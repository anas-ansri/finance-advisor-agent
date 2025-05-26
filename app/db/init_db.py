# app/db/init_db.py
from sqlalchemy.orm import Session

from app.models.bank_statement import Category, TransactionCategoryEnum


def init_categories(db: Session) -> None:
    """Initialize transaction categories in the database."""
    # Check if categories already exist
    existing_count = db.query(Category).count()
    if existing_count > 0:
        return
    
    # Create categories
    categories = [
        Category(name=TransactionCategoryEnum.HOUSING, description="Housing expenses including rent, mortgage, property taxes, etc."),
        Category(name=TransactionCategoryEnum.TRANSPORTATION, description="Transportation expenses including car payments, fuel, public transit, etc."),
        Category(name=TransactionCategoryEnum.FOOD_DINING, description="Food and dining expenses including groceries, restaurants, etc."),
        Category(name=TransactionCategoryEnum.ENTERTAINMENT, description="Entertainment expenses including movies, concerts, subscriptions, etc."),
        Category(name=TransactionCategoryEnum.SHOPPING, description="Shopping expenses including clothing, electronics, etc."),
        Category(name=TransactionCategoryEnum.UTILITIES, description="Utility expenses including electricity, water, internet, phone, etc."),
        Category(name=TransactionCategoryEnum.HEALTH_MEDICAL, description="Health and medical expenses including insurance, doctor visits, medications, etc."),
        Category(name=TransactionCategoryEnum.PERSONAL_CARE, description="Personal care expenses including haircuts, gym memberships, etc."),
        Category(name=TransactionCategoryEnum.EDUCATION, description="Education expenses including tuition, books, courses, etc."),
        Category(name=TransactionCategoryEnum.TRAVEL, description="Travel expenses including flights, hotels, etc."),
        Category(name=TransactionCategoryEnum.GIFTS_DONATIONS, description="Gifts and donations including charitable contributions, presents, etc."),
        Category(name=TransactionCategoryEnum.INCOME, description="Income including salary, freelance work, etc."),
        Category(name=TransactionCategoryEnum.INVESTMENTS, description="Investment transactions including stocks, bonds, etc."),
        Category(name=TransactionCategoryEnum.SAVINGS, description="Savings transactions including transfers to savings accounts, etc."),
        Category(name=TransactionCategoryEnum.OTHER, description="Other transactions that don't fit into the above categories")
    ]
    
    db.add_all(categories)
    db.commit()
