import os
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_text_splitters import TokenTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.schemas.bank_statement import BankStatementWithData, StatementMetadata, BankTransaction, TransactionCategoryEnum
from app.models.bank_statement import (
    BankStatement,
    BankTransaction as BankTransactionModel,
    BankStatementMetadata,
    BankCategory,
    TransactionCategoryEnum as DBTransactionCategoryEnum
)

logger = logging.getLogger(__name__)

from pydantic import BaseModel
from typing import List
from app.schemas.bank_statement import BankTransaction, StatementMetadata

class TransactionList(BaseModel):
    """Wrapper for transaction extraction results."""
    transactions: List[BankTransaction]

class MetadataWrapper(BaseModel):
    """Wrapper for metadata extraction results."""
    metadata: StatementMetadata

class BankStatementExtractor:
    """Enhanced service for extracting data from bank statement PDFs."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the extractor with OpenAI API key."""
        if api_key:
            os.environ["OPENAI_API_KEY"] = api_key
        elif not os.environ.get("OPENAI_API_KEY"):
            raise ValueError("OpenAI API key must be provided or set as environment variable")

        # Initialize LLM with higher temperature for better extraction
        self.llm = ChatOpenAI(model_name="gpt-4o-mini", temperature=0.1)

        # Create text splitter for chunking
        self.text_splitter = TokenTextSplitter(
            chunk_size=3000,
            chunk_overlap=300,
        )

        # Enhanced metadata extraction prompt
        self.metadata_prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "You are an expert at extracting metadata from bank statements. "
                "Extract the following information precisely:\n"
                "- Account Number: Look for account numbers, typically 8-12 digits\n"
                "- Account Holder: The customer name on the statement\n"
                "- Bank Name: The financial institution name\n"
                "- Statement Period: The date range covered (e.g., 'October 10 - November 9')\n"
                "- Opening Balance: The starting balance for the period\n"
                "- Closing Balance: The ending balance for the period\n\n"
                "Look for phrases like 'Beginning balance', 'Ending balance', 'Statement of Account', "
                "'Account #', customer addresses, and date ranges. "
                "Extract exact values as they appear in the document. "
                "If information is not clearly present, return null for that field."
            ),
            ("human", "{text}"),
        ])

        # Enhanced transaction extraction prompt
        self.transaction_prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "You are an expert at extracting bank transaction data from bank statements. "
                "Extract ALL transactions with complete details. For each transaction:\n\n"
                "1. DATE: Convert to YYYY-MM-DD format. If year is missing, infer from context\n"
                "2. DESCRIPTION: Full transaction description as shown\n"
                "3. AMOUNT: Negative for debits/withdrawals, positive for credits/deposits\n"
                "4. BALANCE: Account balance after transaction (if shown)\n"
                "5. TRANSACTION_TYPE: 'debit', 'credit', 'fee', 'interest', etc.\n"
                "6. REFERENCE_NUMBER: Check numbers, transaction IDs, etc.\n"
                "7. CATEGORY: Categorize each transaction into one of these categories:\n"
                "   - INCOME: Salary, deposits, credits, interest\n"
                "   - HOUSING: Rent, mortgage, utilities\n"
                "   - TRANSPORTATION: Gas, car payments, public transport\n"
                "   - FOOD_DINING: Groceries, restaurants, food purchases\n"
                "   - SHOPPING: Retail purchases, general shopping\n"
                "   - ENTERTAINMENT: Movies, games, subscriptions\n"
                "   - UTILITIES: Phone, internet, electricity, water\n"
                "   - HEALTH_MEDICAL: Medical bills, pharmacy, healthcare\n"
                "   - PERSONAL_CARE: Beauty, grooming, personal items\n"
                "   - EDUCATION: School fees, books, courses\n"
                "   - TRAVEL: Hotels, flights, travel expenses\n"
                "   - GIFTS_DONATIONS: Gifts, charitable donations\n"
                "   - INVESTMENTS: Investment accounts, securities\n"
                "   - SAVINGS: Savings transfers, deposits\n"
                "   - OTHER: Anything that doesn't fit above categories\n\n"
                "8. EVIDENCE: The exact text line from which this transaction was extracted\n\n"
                "Look for transaction tables, check lists, and detailed transaction sections. "
                "Include ALL transactions found in the text."
            ),
            ("human", "{text}"),
        ])

        # Create structured output extractors
        self.transaction_extractor = self.transaction_prompt | self.llm.with_structured_output(
            schema=TransactionList,
            method="function_calling",
            include_raw=False,
        )

        self.metadata_extractor = self.metadata_prompt | self.llm.with_structured_output(
            schema=StatementMetadata,
            method="function_calling",
            include_raw=False,
        )

    def load_pdf(self, file_path: str) -> str:
        """Load PDF content from file path with enhanced text extraction."""
        logger.info(f"Loading PDF from {file_path}")
        try:
            loader = PyPDFLoader(file_path)
            pages = loader.load()
            
            # Join pages with clear separators
            full_text = "\n\n--- PAGE BREAK ---\n\n".join([page.page_content for page in pages])
            
            logger.info(f"Extracted {len(full_text)} characters from PDF")
            return full_text
        except Exception as e:
            logger.error(f"Error loading PDF: {str(e)}")
            raise

    def extract_data(self, file_path: str) -> tuple[StatementMetadata, List[BankTransaction]]:
        """Extract all data from a bank statement PDF with improved processing."""
        
        # Load PDF content
        print("Loading PDF content...")
        full_text = self.load_pdf(file_path)
        
        # Extract metadata from the entire document (focusing on first 6000 chars)
        metadata_text = full_text[:6000]
        print("Extracting metadata...")
        metadata = self.metadata_extractor.invoke({"text": metadata_text})
        print(f"Extracted metadata: {metadata}")

        # Split text into overlapping chunks for transaction extraction
        chunks = self.text_splitter.split_text(full_text)
        logger.info(f"Split PDF into {len(chunks)} chunks for processing")

        # Extract transactions from each chunk with batch processing
        print("Extracting transactions...")
        transaction_results = self.transaction_extractor.batch(
            [{"text": chunk} for chunk in chunks],
            {"max_concurrency": 3},  # Reduced concurrency for stability
        )

        # Combine all transactions
        all_transactions = []
        for i, result in enumerate(transaction_results):
            if hasattr(result, 'transactions'):
                chunk_transactions = result.transactions
                print(f"Chunk {i+1}: Found {len(chunk_transactions)} transactions")
                all_transactions.extend(chunk_transactions)

        print(f"Total transactions found: {len(all_transactions)}")

        # Remove duplicates and sort
        unique_transactions = self._remove_duplicate_transactions(all_transactions)
        sorted_transactions = sorted(unique_transactions, key=lambda x: x.date)

        print(f"Final unique transactions: {len(sorted_transactions)}")
        
        return metadata, sorted_transactions

    def _remove_duplicate_transactions(self, transactions: List[BankTransaction]) -> List[BankTransaction]:
        """Remove duplicate transactions with improved logic."""
        unique_transactions = {}
        
        for transaction in transactions:
            # Create a more comprehensive key for deduplication
            key = (
                transaction.date.strftime('%Y-%m-%d'),
                abs(transaction.amount),  # Use absolute value to handle sign differences
                transaction.description[:50].strip().upper(),  # Normalize description
            )
            
            # Keep the transaction with more complete information
            if key not in unique_transactions:
                unique_transactions[key] = transaction
            else:
                # Keep the one with more complete data
                existing = unique_transactions[key]
                if (transaction.balance is not None and existing.balance is None) or \
                   (transaction.reference_number and not existing.reference_number):
                    unique_transactions[key] = transaction

        return list(unique_transactions.values())

    async def _get_or_create_category(self, db: Session, category_name: str) -> BankCategory:
        """Get or create a category by name with improved matching."""
        try:
            # Normalize the category name
            category_name = category_name.upper().replace(' ', '_').replace('&', '_')
            
            # Try to convert the string to enum
            if hasattr(TransactionCategoryEnum, category_name):
                category_enum = getattr(TransactionCategoryEnum, category_name)
                db_enum = DBTransactionCategoryEnum[category_enum.name]
            else:
                # Try direct mapping
                category_enum = TransactionCategoryEnum(category_name)
                db_enum = DBTransactionCategoryEnum[category_enum.name]

            # Look up the category
            result = await db.execute(
                select(BankCategory).filter(BankCategory.name == db_enum)
            )
            category = result.scalar_one_or_none()
            
            if not category:
                # Create the category if it doesn't exist
                category = BankCategory(name=db_enum)
                db.add(category)
                await db.flush()

            return category

        except (ValueError, KeyError, AttributeError):
            # If the category doesn't match our enum, use OTHER
            result = await db.execute(
                select(BankCategory).filter(BankCategory.name == DBTransactionCategoryEnum.OTHER)
            )
            category = result.scalar_one_or_none()
            
            if not category:
                category = BankCategory(name=DBTransactionCategoryEnum.OTHER)
                db.add(category)
                await db.flush()

            return category

    async def save_to_database(self,
                             db: Session,
                             user_id: str,
                             metadata: StatementMetadata,
                             transactions: List[BankTransaction],
                             title: str,
                             description: Optional[str] = None,
                             account_id: Optional[UUID] = None) -> BankStatement:
        """Save extracted data to database with enhanced error handling."""
        
        try:
            # Create bank statement record
            db_statement = BankStatement(
                title=title,
                description=description or "Extracted bank statement data",
                user_id=user_id,
                is_active=True
            )
            db.add(db_statement)
            await db.flush()

            # Create metadata record
            db_metadata = BankStatementMetadata(
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
                    category = await self._get_or_create_category(db, transaction.category)

                db_transaction = BankTransactionModel(
                    statement_id=db_statement.id,
                    account_id=account_id,
                    date=transaction.date,
                    description=transaction.description,
                    amount=transaction.amount,
                    balance=transaction.balance,
                    transaction_type=transaction.transaction_type,
                    category_id=category.id if category else None,
                    reference_number=transaction.reference_number,
                    is_recurring=getattr(transaction, 'is_recurring', False),
                    evidence=transaction.evidence
                )
                db.add(db_transaction)

            await db.commit()
            await db.refresh(db_statement)
            
            print(f"Successfully saved statement with {len(transactions)} transactions")
            return db_statement

        except Exception as e:
            await db.rollback()
            logger.error(f"Error saving to database: {str(e)}")
            raise
