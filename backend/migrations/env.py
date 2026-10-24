from alembic import context

from app.database import Base, engine
from app.models import Item, User  # noqa: F401 -- register table metadata


def run_migrations(connection):
    context.configure(connection=connection, target_metadata=Base.metadata)
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    context.configure(url=engine.url, target_metadata=Base.metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
elif context.config.attributes.get("connection") is not None:
    # Tests can run real migrations inside an isolated PostgreSQL schema.
    run_migrations(context.config.attributes["connection"])
else:
    with engine.connect() as connection:
        run_migrations(connection)
