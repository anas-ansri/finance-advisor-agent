import asyncio
from logging.config import fileConfig
import os
import sys

# Add the project root directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncEngine
from app.db.database import Base
from app.core.config import settings

# Import all models
from app.models.user import User
from app.models.expense import Expense
from app.models.bank_category import BankCategory
from app.models.bank_statement import BankStatement
from app.models.account import Account
from app.models.bank_statement_metadata import BankStatementMetadata
from app.models.bank_tags import BankTag
from app.models.bank_transaction_tag import BankTransactionTag
from app.models.bank_transaction import BankTransaction
from app.models.conversation import Conversation
from app.models.financial_goal import FinancialGoal
from app.models.ai_preference import AIPreference
from app.models.ai_insight import AIInsight
from app.models.ai_model import AIModel
from sqlalchemy import text
from sqlalchemy import create_engine


# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

# Override the SQLAlchemy URL with the one from settings
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = AsyncEngine(
        engine_from_config(
            config.get_section(config.config_ini_section),
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
            future=True,
        )
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())