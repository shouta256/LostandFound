"""Add optional item photos and URL timestamps."""

from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('items', sa.Column('photo_updated_at', sa.DateTime(timezone=True), nullable=True))
    op.create_table('item_photos',
        sa.Column('item_id', sa.Uuid(), nullable=False),
        sa.Column('content_type', sa.String(length=10), nullable=False),
        sa.Column('data', sa.LargeBinary(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "content_type IN ('image/jpeg', 'image/png', 'image/webp')",
            name='ck_item_photos_content_type',
        ),
        sa.ForeignKeyConstraint(['item_id'], ['items.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('item_id'),
    )


def downgrade():
    op.drop_table('item_photos')
    op.drop_column('items', 'photo_updated_at')
