# app/db/init_db.py
from sqlalchemy.orm import Session

from app.models.bank_category import BankCategory, TransactionCategoryEnum


def init_categories(db: Session) -> None:
    """Initialize transaction categories in the database."""
    # Check if categories already exist
    existing_count = db.query(BankCategory).count()
    if existing_count > 0:
        return
    
    # Create categories
    categories = [
        BankCategory(name=TransactionCategoryEnum.HOUSING, description="Housing expenses including rent, mortgage, property taxes, etc."),
        BankCategory(name=TransactionCategoryEnum.TRANSPORTATION, description="Transportation expenses including car payments, fuel, public transit, etc."),
        BankCategory(name=TransactionCategoryEnum.FOOD_DINING, description="Food and dining expenses including groceries, restaurants, etc."),
        BankCategory(name=TransactionCategoryEnum.ENTERTAINMENT, description="Entertainment expenses including movies, concerts, subscriptions, etc."),
        BankCategory(name=TransactionCategoryEnum.SHOPPING, description="Shopping expenses including clothing, electronics, etc."),
        BankCategory(name=TransactionCategoryEnum.UTILITIES, description="Utility expenses including electricity, water, internet, phone, etc."),
        BankCategory(name=TransactionCategoryEnum.HEALTH_MEDICAL, description="Health and medical expenses including insurance, doctor visits, medications, etc."),
        BankCategory(name=TransactionCategoryEnum.PERSONAL_CARE, description="Personal care expenses including haircuts, gym memberships, etc."),
        BankCategory(name=TransactionCategoryEnum.EDUCATION, description="Education expenses including tuition, books, courses, etc."),
        BankCategory(name=TransactionCategoryEnum.TRAVEL, description="Travel expenses including flights, hotels, etc."),
        BankCategory(name=TransactionCategoryEnum.GIFTS_DONATIONS, description="Gifts and donations including charitable contributions, presents, etc."),
        BankCategory(name=TransactionCategoryEnum.INCOME, description="Income including salary, freelance work, etc."),
        BankCategory(name=TransactionCategoryEnum.INVESTMENTS, description="Investment transactions including stocks, bonds, etc."),
        BankCategory(name=TransactionCategoryEnum.SAVINGS, description="Savings transactions including transfers to savings accounts, etc."),
        BankCategory(name=TransactionCategoryEnum.NOT_CATEGORIZED, description="Transactions that do not fit into any specific category."),
    ]
    
    db.add_all(categories)
    db.commit()
