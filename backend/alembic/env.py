import os
from alembic import context
from sqlalchemy import create_engine, pool
from app.db.session import Base
from app.db import models
from app.core.config import settings

config = context.config
target_metadata = Base.metadata
url = os.environ.get("MIGRATION_DATABASE_URL", settings().database_url)
if context.is_offline_mode():
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = create_engine(url, poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
