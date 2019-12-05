"""Data model changes to support background workers

    * add completed column to submission table
    * create external_id

Revision ID: e49fc438496f
Revises: 91dea8eac72c
Create Date: 2019-10-22 10:19:45.381193

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import expression, func

# revision identifiers, used by Alembic.
revision = 'e49fc438496f'
down_revision = '91dea8eac72c'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('submission',
        sa.Column('completed', sa.Boolean(), nullable=False, server_default=expression.false())
    )

    op.create_table(
        'external_id',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('submission_id', sa.Integer, nullable=False),
        sa.Column('external_id', sa.Text, nullable=False),
        sa.Column('external_system', sa.String(255), nullable=False),
        sa.Column('date_created', sa.DateTime(timezone=True), server_default=func.now())
    )

    op.create_foreign_key(
        'fk_submission_id',
        'external_id',
        'submission',
        ['submission_id'],
        ['id']

    )


def downgrade():
    op.drop_column('submission', 'completed')
    op.drop_table('external_id')
