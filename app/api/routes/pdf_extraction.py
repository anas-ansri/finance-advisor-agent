# app/api/routes/pdf_extraction.py
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, BackgroundTasks, Form
from fastapi.responses import JSONResponse
import tempfile
import os
from typing import Optional, List

from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.database import get_db
from app.models.user import User
from app.models.bank_statement import BankStatement
from app.services.pdf_extraction import BankStatementExtractor
from app.schemas.bank_statement import BankStatement as BankStatementSchema, BankStatementWithData, Tag, TransactionCategoryEnum

router = APIRouter()

@router.post("/extract-bank-statement/", response_model=BankStatementSchema)
async def extract_bank_statement(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Extract data from a bank statement PDF and associate it with the current user."""
    # Check if file is a PDF
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    # Create a temporary file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
    temp_file_path = temp_file.name
    
    try:
        # Write the uploaded file to the temporary file
        content = await file.read()
        temp_file.write(content)
        temp_file.close()
        
        # Extract data from the PDF
        extractor = BankStatementExtractor()
        statement_metadata, transactions = extractor.extract_data(temp_file_path)
        
        # Save to database
        db_statement = extractor.save_to_database(
            db=db,
            user_id=current_user.id,
            statement_metadata=statement_metadata,
            transactions=transactions,
            title=title,
            description=description
        )
        
        # Schedule cleanup of temporary file
        background_tasks.add_task(os.unlink, temp_file_path)
        
        return db_statement
    
    except Exception as e:
        # Clean up the temporary file in case of error
        background_tasks.add_task(os.unlink, temp_file_path)
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")


@router.get("/categories/", response_model=List[TransactionCategoryEnum])
def get_transaction_categories():
    """Get all available transaction categories."""
    return list(TransactionCategoryEnum)


@router.get("/bank-statements/", response_model=List[BankStatementSchema])
def get_user_bank_statements(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = 0,
    limit: int = 100,
):
    """Get all bank statements for the current user."""
    statements = db.query(BankStatement).filter(
        BankStatement.user_id == current_user.id,
        BankStatement.is_active == True
    ).offset(skip).limit(limit).all()
    
    return statements


@router.get("/bank-statements/{statement_id}", response_model=BankStatementWithData)
def get_bank_statement_with_data(
    statement_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific bank statement with all its data."""
    statement = db.query(BankStatement).filter(
        BankStatement.id == statement_id,
        BankStatement.user_id == current_user.id,
        BankStatement.is_active == True
    ).first()
    
    if not statement:
        raise HTTPException(status_code=404, detail="Bank statement not found")
    
    return statement


@router.delete("/bank-statements/{statement_id}", response_model=BankStatementSchema)
def delete_bank_statement(
    statement_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a bank statement."""
    statement = db.query(BankStatement).filter(
        BankStatement.id == statement_id,
        BankStatement.user_id == current_user.id,
        BankStatement.is_active == True
    ).first()
    
    if not statement:
        raise HTTPException(status_code=404, detail="Bank statement not found")
    
    statement.is_active = False
    db.commit()
    
    return statement