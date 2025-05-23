# app/services/pdf_extraction.py
import os
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

from langchain_core.prompts import ChatPromptTemplate
from langchain.chat_models import ChatOpenAI
from langchain_text_splitters import TokenTextSplitter
from langchain_community.document_loaders import PyPDFLoader

from sqlalchemy.orm import Session

from app.schemas.bank_statement import BankStatementWithData, StatementMetadata, BankTransaction, TransactionCategoryEnum
from app.models.bank_statement import BankStatement, Transaction, StatementMetadata as StatementMetadataModel, Category, TransactionCategoryEnum as DBTransactionCategoryEnum

logger = logging.getLogger(__name__)

class BankStatementExtractor:
    """Service for extracting data from bank statement PDFs."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the extractor with OpenAI API key."""
        if api_key:
            os.environ["OPENAI_API_KEY"] = api_key
        elif not os.environ.get("OPENAI_API_KEY"):
            raise ValueError("OpenAI API key must be provided or set as environment variable")
        
        # Initialize LLM
        self.llm = ChatOpenAI(model_name="gpt-4o", temperature=0)
        
        # Create text splitter for chunking
        self.text_splitter = TokenTextSplitter(
            chunk_size=2000,
            chunk_overlap=200,
        )
        
        # Define extraction prompts
        self.transaction_prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "You are an expert at extracting bank transaction data from bank statements. "
                "Extract all transactions with their details. Be precise with dates, amounts, and descriptions. "
                "For each transaction, extract the date, description, amount, and any other relevant details. "
                "If the amount is a withdrawal or debit, make sure it's represented as a negative number. "
                "For each transaction, categorize it into one of the following categories: "
                "Housing, Transportation, Food & Dining, Entertainment, Shopping, Utilities, "
                "Health & Medical, Personal Care, Education, Travel, Gifts & Donations, "
                "Income, Investments, Savings, Other. "
                "If no transactions can be found in the text, return an empty list."
            ),
            ("human", "{text}"),
        ])
        
        self.metadata_prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "You are an expert at extracting metadata from bank statements. "
                "Extract information like account number, account holder name, bank name, "
                "statement period, opening balance, and closing balance. "
                "Be precise and extract only factual information that appears in the text. "
                "If certain information is not present, leave those fields empty."
            ),
            ("human", "{text}"),
        ])
        
        # Create extractors
        self.transaction_extractor = self.transaction_prompt | self.llm.with_structured_output(
            schema={"transactions": List[BankTransaction]},
            include_raw=False,
        )
        
        self.metadata_extractor = self.metadata_prompt | self.llm.with_structured_output(
            schema=StatementMetadata,
            include_raw=False,
        )
    
    def load_pdf(self, file_path: str) -> str:
        """Load PDF content from file path."""
        logger.info(f"Loading PDF from {file_path}")
        try:
            loader = PyPDFLoader(file_path)
            pages = loader.load()
            full_text = "\n".join([page.page_content for page in pages])
            return full_text
        except Exception as e:
            logger.error(f"Error loading PDF: {str(e)}")
            raise
    
    def extract_data(self, file_path: str) -> tuple[StatementMetadata, List[BankTransaction]]:
        """Extract all data from a bank statement PDF."""
        # Load PDF content
        full_text = self.load_pdf(file_path)
        
        # Extract metadata from the first few pages (usually contains statement info)
        first_chunk = full_text[:min(len(full_text), 4000)]
        metadata = self.metadata_extractor.invoke({"text": first_chunk})
        
        # Split text into chunks for transaction extraction
        chunks = self.text_splitter.split_text(full_text)
        logger.info(f"Split PDF into {len(chunks)} chunks for processing")
        
        # Extract transactions from each chunk in parallel
        transaction_results = self.transaction_extractor.batch(
            [{"text": chunk} for chunk in chunks],
            {"max_concurrency": 5},
        )
        
        # Combine all transactions
        all_transactions = []
        for result in transaction_results:
            if hasattr(result, 'transactions'):
                all_transactions.extend(result.transactions)
        
        # Remove potential duplicates (based on date, amount, and description)
        unique_transactions = self._remove_duplicate_transactions(all_transactions)
        
        # Sort transactions by date
        sorted_transactions = sorted(unique_transactions, key=lambda x: x.date)
        
        return metadata, sorted_transactions
    
    def _remove_duplicate_transactions(self, transactions: List[BankTransaction]) -> List[BankTransaction]:
        """Remove duplicate transactions based on date, amount, and description."""
        unique_transactions = {}
        
        for transaction in transactions:
            # Create a key based on date, amount, and first 30 chars of description
            key = (
                transaction.date.strftime('%Y-%m-%d'),
                transaction.amount,
                transaction.description[:30]
            )
            
            # Only keep one instance of each transaction
            if key not in unique_transactions:
                unique_transactions[key] = transaction
        
        return list(unique_transactions.values())
    
    def _get_or_create_category(self, db: Session, category_name: str) -> Category:
        """Get or create a category by name."""
        try:
            # Try to convert the string to enum
            category_enum = TransactionCategoryEnum(category_name)
            db_enum = DBTransactionCategoryEnum[category_enum.name]
            
            # Look up the category
            category = db.query(Category).filter(Category.name == db_enum).first()
            
            if not category:
                # Create the category if it doesn't exist
                category = Category(name=db_enum)
                db.add(category)
                db.flush()
            
            return category
        except (ValueError, KeyError):
            # If the category doesn't match our enum, use OTHER
            category = db.query(Category).filter(Category.name == DBTransactionCategoryEnum.OTHER).first()
            
            if not category:
                category = Category(name=DBTransactionCategoryEnum.OTHER)
                db.add(category)
                db.flush()
            
            return category
    
    def save_to_database(self, 
                     db: Session, 
                     user_id: int, 
                     metadata: StatementMetadata,
                     transactions: List[BankTransaction],
                     title: str, 
                        description: Optional[str] = None) -> BankStatement:
        """Save extracted data to database."""
        # Create bank statement record
        db_statement = BankStatement(
            title=title,
            description=description or "Extracted bank statement data",
            user_id=user_id,
            is_active=True
        )
        
        db.add(db_statement)
        db.flush()  # Flush to get the ID
        
        # Create metadata record
        db_metadata = StatementMetadataModel(
            statement_id=db_statement.id,
            account_number=metadata.account_number,
            account_holder=metadata.account_holder,
            bank_name=metadata.bank_name,
            statement_period=metadata.statement_period,
            opening_balance=metadata.opening_balance,
            closing_balance=metadata.closing_balance
        )
        db.add(db_metadata)
        
        # Create transaction records
        for transaction in transactions:
            # Get or create category
            category = None
            if transaction.category:
                category = self._get_or_create_category(db, transaction.category)
            
            db_transaction = Transaction(
                statement_id=db_statement.id,
                date=transaction.date,
                description=transaction.description,
                amount=transaction.amount,
                balance=transaction.balance,
                transaction_type=transaction.transaction_type,
                category_id=category.id if category else None,
                reference_number=transaction.reference_number,
                is_recurring=transaction.is_recurring if hasattr(transaction, 'is_recurring') else False,
                evidence=transaction.evidence
            )
            db.add(db_transaction)
        
        db.commit()
        db.refresh(db_statement)
        
        return db_statement
