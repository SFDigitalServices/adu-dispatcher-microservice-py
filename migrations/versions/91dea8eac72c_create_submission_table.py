# pylint: skip-file
"""create submission table

Revision ID: 91dea8eac72c
Revises: 
Create Date: 2019-09-25 14:28:51.619375

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import func


# revision identifiers, used by Alembic.
revision = '91dea8eac72c'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'submission',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('data', sa.Text, nullable=False),
        sa.Column('date_created', sa.DateTime(timezone=True), server_default=func.now())
    )


def downgrade():
    op.drop_table('submission')
