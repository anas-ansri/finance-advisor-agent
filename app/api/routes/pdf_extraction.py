# app/api/routes/pdf_extraction.py
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, BackgroundTasks, Form, Request
from fastapi.responses import StreamingResponse
import tempfile
import os
from typing import Optional, List, Dict, Any, AsyncGenerator
from uuid import UUID
import asyncio
import json

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.security import get_current_user
from app.db.database import get_db
from app.models.user import User
from app.models.bank_statement import BankStatement, BankTransaction as BankTransactionModel
from app.models.bank_statement_metadata import BankStatementMetadata
from app.models.account import Account
from app.services.pdf_extraction import BankStatementExtractor
from app.schemas.bank_statement import (
    BankStatement as BankStatementSchema,
    BankStatementWithData,
    BankTransaction as BankTransactionSchema,
    StatementMetadata,
    TransactionCategoryEnum
)
import logging
from fastapi import Query

from app.services.ai import generate_financial_insights

logger = logging.getLogger(__name__)

router = APIRouter()

def convert_to_schema(db_statement: BankStatement) -> BankStatementWithData:
    """Convert database model to Pydantic schema."""
    # Convert transactions
    transactions = []
    for t in db_statement.bank_transactions:
        transaction = BankTransactionSchema(
            date=t.date,
            description=t.description,
            amount=t.amount,
            balance=t.balance,
            transaction_type=t.transaction_type,
            category=t.category.name.value if t.category else None,
            reference_number=t.reference_number,
            is_recurring=t.is_recurring,
            evidence=t.evidence,
            account_id=t.account_id
        )
        transactions.append(transaction)
    
    # Convert metadata
    metadata = StatementMetadata(
        account_number=db_statement.statement_metadata.account_number,
        account_holder=db_statement.statement_metadata.account_holder,
        bank_name=db_statement.statement_metadata.bank_name,
        statement_period=db_statement.statement_metadata.statement_period,
        opening_balance=db_statement.statement_metadata.opening_balance,
        closing_balance=db_statement.statement_metadata.closing_balance
    )
    
    # Create final schema
    return BankStatementWithData(
        id=db_statement.id,
        user_id=db_statement.user_id,
        title=db_statement.title,
        description=db_statement.description,
        is_active=db_statement.is_active,
        created_at=db_statement.created_at,
        updated_at=db_statement.updated_at,
        metadata=metadata,
        transactions=transactions
    )

async def progress_generator(task_id: str) -> AsyncGenerator[str, None]:
    """Generate progress updates for a task."""
    try:
        # Simulate progress updates
        for progress in range(0, 101, 10):
            yield f"data: {json.dumps({'task_id': task_id, 'progress': progress, 'status': 'Processing' if progress < 100 else 'Complete'})}\n\n"
            await asyncio.sleep(1)
    except Exception as e:
        logger.error(f"Progress generator error: {str(e)}")
        yield f"data: {json.dumps({'task_id': task_id, 'error': str(e)})}\n\n"

@router.get("/progress/{task_id}")
async def get_progress(task_id: str):
    """Get progress updates for a task using Server-Sent Events."""
    return StreamingResponse(
        progress_generator(task_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@router.post("/extract-bank-statement/", response_model=BankStatementWithData)
async def extract_bank_statement(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    account_id: Optional[UUID] = Form(None),
    task_id: str = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Extract data from a bank statement PDF with enhanced processing."""
    
    # Validate file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    # Validate account_id if provided
    if account_id:
        # Check if account exists and belongs to user
        stmt = select(Account).where(
            Account.id == account_id,
            Account.user_id == current_user.id
        )
        result = await db.execute(stmt)
        account = result.scalar_one_or_none()
        if not account:
            raise HTTPException(status_code=404, detail="Account not found or does not belong to user")

    # Create temporary file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
    temp_file_path = temp_file.name

    try:
        # Write uploaded file to temporary file
        content = await file.read()
        print(f"Processing file: {file.filename}, size: {len(content)} bytes")
        
        temp_file.write(content)
        temp_file.close()

        # Extract data from PDF
        extractor = BankStatementExtractor(api_key=current_user.openai_api_key)
        
        print("Starting extraction process...")
        statement_metadata, transactions = extractor.extract_data(temp_file_path)
        
        print(f"Extraction completed:")
        print(f"- Metadata: {statement_metadata}")
        print(f"- Transactions: {len(transactions)}")
        
        # Validate extraction results
        if not transactions:
            logger.warning("No transactions extracted from PDF")
            raise HTTPException(status_code=400, detail="No transactions could be extracted from the PDF")
        
        # Save to database
        print("Saving to database...")
        db_statement = await extractor.save_to_database(
            db=db,
            user_id=str(current_user.id),
            metadata=statement_metadata,
            transactions=transactions,
            title=title,
            description=description,
            account_id=account_id
        )

        # Schedule cleanup
        background_tasks.add_task(os.unlink, temp_file_path)

        # Fetch complete statement with relationships
        stmt = select(BankStatement).where(
            BankStatement.id == db_statement.id
        ).options(
            selectinload(BankStatement.bank_transactions).selectinload(BankTransactionModel.category),
            selectinload(BankStatement.statement_metadata)
        )

        result = await db.execute(stmt)
        complete_statement = result.scalar_one()

        print(f"Successfully processed statement: {complete_statement.title}")
        
        # Trigger AI insight generation as a background task
        background_tasks.add_task(generate_financial_insights, db, current_user.id)

        return convert_to_schema(complete_statement)

    except Exception as e:
        logger.error(f"Error processing PDF: {str(e)}", exc_info=True)
        background_tasks.add_task(os.unlink, temp_file_path)
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")
    
@router.get("/bank-statements/financial-score", response_model=Dict[str, Any])
async def get_financial_score(
    income_range: float = Query(100000, gt=0, description="Expected maximum income for scoring"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = (
        select(BankStatement)
        .where(
            BankStatement.user_id == current_user.id,
            BankStatement.is_active == True
        )
        .order_by(BankStatement.created_at.desc())
        .options(
            selectinload(BankStatement.bank_transactions).selectinload(BankTransactionModel.category),
            selectinload(BankStatement.statement_metadata)
        )
    )
    result = await db.execute(stmt)
    statement = result.scalars().first()
    if not statement:
        raise HTTPException(status_code=404, detail="No bank statements found")
    statement_id = str(statement.id)
    if not statement.bank_transactions:
        raise HTTPException(status_code=404, detail="No transactions found in the latest bank statement")

    transactions = statement.bank_transactions
    if not transactions:
        return {"statement_id": statement_id, "financial_score": 0, "details": "No transactions found"}

    total_income = sum(t.amount for t in transactions if t.amount > 0)
    total_expenses = sum(abs(t.amount) for t in transactions if t.amount < 0)

    income_score = min(40, (total_income / income_range) * 40)

    avg_expense = total_expenses / len(transactions) if transactions else 0
    expense_score = 30 - min(30, (avg_expense / 10000) * 30)

    savings = total_income - total_expenses
    savings_score = 30 if savings > 0 else max(0, 30 + (savings / total_income) * 30)

    financial_score = round(income_score + expense_score + savings_score)
    financial_score = min(100, max(0, financial_score))

    return {
        "statement_id": statement_id,
        "financial_score": financial_score,
        "breakdown": {
            "income_score": round(income_score, 2),
            "expense_score": round(expense_score, 2),
            "savings_score": round(savings_score, 2)
        }
    }


@router.get("/bank-statements/overall-financial-score", response_model=Dict[str, Any])
async def get_overall_financial_score(
    income_range: float = Query(100000, gt=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = (
        select(BankStatement)
        .where(
            BankStatement.user_id == current_user.id,
            BankStatement.is_active == True
        )
        .options(
            selectinload(BankStatement.bank_transactions).selectinload(BankTransactionModel.category)
        )
    )
    result = await db.execute(stmt)
    statements = result.scalars().all()
    all_transactions = [t for s in statements for t in s.bank_transactions]
    if not all_transactions:
        return {"financial_score": 0, "details": "No transactions found"}
    total_income = sum(t.amount for t in all_transactions if t.amount > 0)
    total_expenses = sum(abs(t.amount) for t in all_transactions if t.amount < 0)
    income_score = min(40, (total_income / income_range) * 40)
    avg_expense = total_expenses / len(all_transactions)
    expense_score = 30 - min(30, (avg_expense / 10000) * 30)
    savings = total_income - total_expenses
    savings_score = 30 if savings > 0 else max(0, 30 + (savings / total_income) * 30)
    financial_score = round(income_score + expense_score + savings_score)
    financial_score = min(100, max(0, financial_score))
    return {
        "financial_score": financial_score,
        "breakdown": {
            "income_score": round(income_score, 2),
            "expense_score": round(expense_score, 2),
            "savings_score": round(savings_score, 2)
        }
    }


@router.get("/bank-statements/transactions/categories/summary", response_model=Dict[str, Any])
async def get_categorized_summary_all(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = (
        select(BankTransactionModel)
        .where(BankTransactionModel.user_id == current_user.id)
        .options(selectinload(BankTransactionModel.category))
    )
    result = await db.execute(stmt)
    transactions = result.scalars().all()
    category_breakdown = {}
    for t in transactions:
        cat = t.category.name.value if t.category else "OTHER"
        if cat not in category_breakdown:
            category_breakdown[cat] = {"count": 0, "total": 0}
        category_breakdown[cat]["count"] += 1
        category_breakdown[cat]["total"] += abs(t.amount)
    return category_breakdown


@router.get("/bank-statements/transactions/categories/summary/recent", response_model=Dict[str, Any])
async def get_categorized_summary_recent(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = (
        select(BankStatement)
        .where(
            BankStatement.user_id == current_user.id,
            BankStatement.is_active == True
        )
        .order_by(BankStatement.created_at.desc())
        .options(selectinload(BankStatement.bank_transactions).selectinload(BankTransactionModel.category))
    )
    result = await db.execute(stmt)
    statement = result.scalars().first()
    if not statement:
        raise HTTPException(status_code=404, detail="No bank statements found")
    transactions = statement.bank_transactions
    category_breakdown = {}
    for t in transactions:
        cat = t.category.name.value if t.category else "OTHER"
        if cat not in category_breakdown:
            category_breakdown[cat] = {"count": 0, "total": 0}
        category_breakdown[cat]["count"] += 1
        category_breakdown[cat]["total"] += abs(t.amount)
    return category_breakdown

@router.get("/bank-statements/{statement_id}/transactions/categories/summary", response_model=Dict[str, Any])
async def get_categorized_summary_by_statement(
    statement_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = (
        select(BankTransactionModel)
        .where(
            BankTransactionModel.statement_id == statement_id,
            BankTransactionModel.user_id == current_user.id
        )
        .options(selectinload(BankTransactionModel.category))
    )
    result = await db.execute(stmt)
    transactions = result.scalars().all()
    category_breakdown = {}
    for t in transactions:
        cat = t.category.name.value if t.category else "OTHER"
        if cat not in category_breakdown:
            category_breakdown[cat] = {"count": 0, "total": 0}
        category_breakdown[cat]["count"] += 1
        category_breakdown[cat]["total"] += abs(t.amount)
    return category_breakdown

# Add new endpoint for transaction analysis
@router.get("/bank-statements/{statement_id}/analysis", response_model=Dict[str, Any])
async def get_statement_analysis(
    statement_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get detailed analysis of a bank statement."""
    
    stmt = select(BankStatement).where(
        BankStatement.id == statement_id,
        BankStatement.user_id == current_user.id,
        BankStatement.is_active == True
    ).options(
        selectinload(BankStatement.bank_transactions).selectinload(BankTransactionModel.category),
        selectinload(BankStatement.statement_metadata)
    )

    result = await db.execute(stmt)
    statement = result.scalar_one_or_none()

    if not statement:
        raise HTTPException(status_code=404, detail="Bank statement not found")

    # Calculate analysis
    transactions = statement.bank_transactions
    total_credits = sum(t.amount for t in transactions if t.amount > 0)
    total_debits = sum(abs(t.amount) for t in transactions if t.amount < 0)
    
    # Category breakdown
    category_breakdown = {}
    for transaction in transactions:
        if transaction.category:
            cat_name = transaction.category.name.value
            if cat_name not in category_breakdown:
                category_breakdown[cat_name] = {"count": 0, "total": 0}
            category_breakdown[cat_name]["count"] += 1
            category_breakdown[cat_name]["total"] += abs(transaction.amount)

    return {
        "statement_id": statement_id,
        "total_transactions": len(transactions),
        "total_credits": total_credits,
        "total_debits": total_debits,
        "net_change": total_credits - total_debits,
        "category_breakdown": category_breakdown,
        "date_range": {
            "start": min(t.date for t in transactions) if transactions else None,
            "end": max(t.date for t in transactions) if transactions else None
        }
    }

@router.get("/categories/", response_model=List[TransactionCategoryEnum])
def get_transaction_categories():
    """Get all available transaction categories."""
    return list(TransactionCategoryEnum)

@router.get("/bank-statements/", response_model=List[BankStatementSchema])
async def get_user_bank_statements(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = 0,
    limit: int = 100,
):
    """Get all bank statements for the current user."""
    stmt = select(BankStatement).where(
        BankStatement.user_id == current_user.id,
        BankStatement.is_active == True
    ).offset(skip).limit(limit)
    
    result = await db.execute(stmt)
    statements = result.scalars().all()
    
    return statements

@router.get("/bank-statements/{statement_id}", response_model=BankStatementWithData)
async def get_bank_statement_with_data(
    statement_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific bank statement with all its data."""
    stmt = select(BankStatement).where(
        BankStatement.id == statement_id,
        BankStatement.user_id == current_user.id,
        BankStatement.is_active == True
    ).options(
        selectinload(BankStatement.bank_transactions).selectinload(BankTransactionModel.category),
        selectinload(BankStatement.statement_metadata)
    )
    
    result = await db.execute(stmt)
    statement = result.scalar_one_or_none()
    
    if not statement:
        raise HTTPException(status_code=404, detail="Bank statement not found")
    
    return convert_to_schema(statement)

@router.delete("/bank-statements/{statement_id}", response_model=BankStatementSchema)
async def delete_bank_statement(
    statement_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a bank statement."""
    stmt = select(BankStatement).where(
        BankStatement.id == statement_id,
        BankStatement.user_id == current_user.id,
        BankStatement.is_active == True
    )
    
    result = await db.execute(stmt)
    statement = result.scalar_one_or_none()
    
    if not statement:
        raise HTTPException(status_code=404, detail="Bank statement not found")
    
    statement.is_active = False
    await db.commit()
    
    return statement


@router.get("/accounts/balances", response_model=Dict[str, float])
async def get_all_account_balances(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get the most recent closing balance of all accounts associated with the current user.
    """
    stmt = (
        select(BankStatementMetadata)
        .join(BankStatementMetadata.statement)
        .where(
            BankStatement.user_id == current_user.id,
            BankStatement.is_active == True
        )
        .order_by(BankStatement.created_at.desc())
    )

    result = await db.execute(stmt)
    metadata_list = result.scalars().all()

    account_balances = {}
    seen_accounts = set()

    for metadata in metadata_list:
        acc_num = metadata.account_number
        if acc_num not in seen_accounts:
            seen_accounts.add(acc_num)
            account_balances[acc_num] = metadata.closing_balance

    return account_balances
