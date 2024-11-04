"""add deforestation hotspots

Revision ID: 4e6df3cde2c0
Revises: d102518c5b51
Create Date: 2024-11-04 10:54:07.235106

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = '4e6df3cde2c0'
down_revision = 'd102518c5b51'
branch_labels = None
depends_on = None


def upgrade():
    # Create deforestation_hotspot table
    op.create_table('deforestation_hotspot',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('prediction_id', sa.Integer(), nullable=False),
        sa.Column('geometry', JSONB, nullable=False),  # Store as GeoJSON
        sa.Column('area_ha', sa.Float(), nullable=False),
        sa.Column('perimeter_m', sa.Float(), nullable=False),
        sa.Column('compactness', sa.Float(), nullable=False),
        sa.Column('edge_density', sa.Float(), nullable=False),
        sa.Column('centroid_lon', sa.Float(), nullable=False),
        sa.Column('centroid_lat', sa.Float(), nullable=False),
        sa.Column('verification_status', sa.String(20), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['prediction_id'], ['prediction.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Add indexes for common queries
    op.create_index('idx_deforestation_hotspot_prediction_id', 
                    'deforestation_hotspot', ['prediction_id'])
    op.create_index('idx_deforestation_hotspot_verification_status', 
                    'deforestation_hotspot', ['verification_status'])

def downgrade():
    op.drop_index('idx_deforestation_hotspot_verification_status')
    op.drop_index('idx_deforestation_hotspot_prediction_id')
    op.drop_table('deforestation_hotspot')
    # ### end Alembic commands ###
