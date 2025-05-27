# app/api/routes/pdf_extraction.py
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, BackgroundTasks, Form
from fastapi.responses import JSONResponse
import tempfile
import os
from typing import Optional, List, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.security import get_current_user
from app.db.database import get_db
from app.models.user import User
from app.models.bank_statement import BankStatement
from app.services.pdf_extraction import BankStatementExtractor
from app.schemas.bank_statement import BankStatement as BankStatementSchema, BankStatementWithData, Tag, TransactionCategoryEnum
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# app/api/routes/pdf_extraction.py (Updated extract_bank_statement function)

@router.post("/extract-bank-statement/", response_model=BankStatementWithData)
async def extract_bank_statement(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Extract data from a bank statement PDF with enhanced processing."""
    
    # Validate file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

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
        extractor = BankStatementExtractor()
        
        print("Starting extraction process...")
        statement_metadata, transactions = extractor.extract_data(temp_file_path)
        
        print(f"Extraction completed:")
        print(f"- Metadata: {statement_metadata}")
        print(f"- Transactions: {len(transactions)}")
        
        # Validate extraction results
        if not transactions:
            logger.warning("No transactions extracted from PDF")
        
        # Save to database
        print("Saving to database...")
        db_statement = await extractor.save_to_database(
            db=db,
            user_id=str(current_user.id),
            metadata=statement_metadata,
            transactions=transactions,
            title=title,
            description=description
        )

        # Schedule cleanup
        background_tasks.add_task(os.unlink, temp_file_path)

        # Fetch complete statement with relationships
        stmt = select(BankStatement).where(
            BankStatement.id == db_statement.id
        ).options(
            selectinload(BankStatement.transactions),
            selectinload(BankStatement.statement_metadata)
        )

        result = await db.execute(stmt)
        complete_statement = result.scalar_one()

        print(f"Successfully processed statement: {complete_statement.title}")
        return complete_statement

    except Exception as e:
        logger.error(f"Error processing PDF: {str(e)}", exc_info=True)
        background_tasks.add_task(os.unlink, temp_file_path)
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")

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
        selectinload(BankStatement.transactions),
        selectinload(BankStatement.statement_metadata)
    )

    result = await db.execute(stmt)
    statement = result.scalar_one_or_none()

    if not statement:
        raise HTTPException(status_code=404, detail="Bank statement not found")

    # Calculate analysis
    transactions = statement.transactions
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
        selectinload(BankStatement.transactions),
        selectinload(BankStatement.statement_metadata)
    )
    
    result = await db.execute(stmt)
    statement = result.scalar_one_or_none()
    
    if not statement:
        raise HTTPException(status_code=404, detail="Bank statement not found")
    
    return statement

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