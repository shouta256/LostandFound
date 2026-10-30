"""Create ownership claims and optional campus pickups."""

from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('claims',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('item_id', sa.Uuid(), nullable=False),
        sa.Column('claimant_id', sa.Uuid(), nullable=False),
        sa.Column('ownership_information', sa.Text(), nullable=False),
        sa.Column('status', sa.Text(), server_default='pending', nullable=False),
        sa.Column('reviewed_by', sa.Uuid(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint(
            "(status = 'pending' AND reviewed_by IS NULL AND reviewed_at IS NULL) OR (status IN "
            "('approved', 'rejected') AND reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL)",
            name='ck_claims_review_information',
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'approved', 'rejected')",
            name='ck_claims_status',
        ),
        sa.CheckConstraint(
            'length(trim(ownership_information)) >= 1 AND length(ownership_information) <= 2000',
            name='ck_claims_ownership_length',
        ),
        sa.CheckConstraint(
            'reviewed_by IS NULL OR reviewed_by != claimant_id',
            name='ck_claims_no_self_review',
        ),
        sa.ForeignKeyConstraint(['claimant_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['item_id'], ['items.id'], ),
        sa.ForeignKeyConstraint(['reviewed_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(
        'uq_claims_approved_item', 'claims', ['item_id'],
        unique=True,
        postgresql_where=sa.text("status = 'approved'"),
        sqlite_where=sa.text("status = 'approved'"),
    )
    op.create_index(
        'uq_claims_pending_user_item', 'claims', ['item_id', 'claimant_id'],
        unique=True,
        postgresql_where=sa.text("status = 'pending'"),
        sqlite_where=sa.text("status = 'pending'"),
    )
    op.create_table('pickups',
        sa.Column('claim_id', sa.Uuid(), nullable=False),
        sa.Column('location', sa.Text(), nullable=False),
        sa.Column('status', sa.Text(), server_default='not_ready', nullable=False),
        sa.Column('ready_at', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "(status = 'ready' AND ready_at IS NOT NULL) OR (status = 'not_ready' AND ready_at IS "
            'NULL)',
            name='ck_pickups_readiness_time',
        ),
        sa.CheckConstraint("status IN ('not_ready', 'ready')", name='ck_pickups_status'),
        sa.CheckConstraint(
            'length(trim(location)) >= 1 AND length(location) <= 200',
            name='ck_pickups_location_length',
        ),
        sa.ForeignKeyConstraint(['claim_id'], ['claims.id'], ),
        sa.PrimaryKeyConstraint('claim_id')
    )


def downgrade():
    op.drop_table('pickups')
    op.drop_index('uq_claims_pending_user_item', table_name="claims")
    op.drop_index('uq_claims_approved_item', table_name="claims")
    op.drop_table('claims')
