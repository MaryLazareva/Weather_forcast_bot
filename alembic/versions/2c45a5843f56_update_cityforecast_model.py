"""Update CityForecast model

Revision ID: 2c45a5843f56
Revises: 1db730d03105
Create Date: 2025-01-10 17:30:38.259672

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2c45a5843f56'
down_revision: Union[str, None] = '1db730d03105'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('city_forecast', sa.Column('country', sa.String(), nullable=True))
    op.add_column('city_forecast', sa.Column('region', sa.String(), nullable=True))
    op.create_index(op.f('ix_city_forecast_country'), 'city_forecast', ['country'], unique=False)
    op.create_index(op.f('ix_city_forecast_region'), 'city_forecast', ['region'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_city_forecast_region'), table_name='city_forecast')
    op.drop_index(op.f('ix_city_forecast_country'), table_name='city_forecast')
    op.drop_column('city_forecast', 'region')
    op.drop_column('city_forecast', 'country')
    # ### end Alembic commands ###
