# pylint: skip-file
"""csv batch support

Revision ID: 886f03e523c6
Revises: e49fc438496f
Create Date: 2020-03-03 10:04:39.549737

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '886f03e523c6'
down_revision = 'e49fc438496f'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column('submission', 'completed')
    op.add_column('submission',
        sa.Column('csv_date_processed', sa.DateTime(timezone=True), nullable=True)
    )

def downgrade():
    op.drop_column('submission', 'csv_date_processed')
    op.add_column('submission',
        sa.Column('completed', sa.Boolean(), nullable=False, server_default=expression.false())
    )
