"""Create Google-authenticated users."""

from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("google_sub", sa.String(255), nullable=False, unique=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("role", sa.String(11), nullable=False),
        sa.CheckConstraint("role IN ('student', 'team_member')", name="ck_users_role"),
    )


def downgrade():
    op.drop_table("users")
