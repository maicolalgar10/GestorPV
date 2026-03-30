from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'e338208de38f'
down_revision = 'ff89d2197d82'
branch_labels = None
depends_on = None


def upgrade():
    #  Crear el ENUM en PostgreSQL
    tipo_documento_enum = postgresql.ENUM(
        'CUENTA_COBRO',
        'FACTURA',
        name='tipo_documento_acta_enum'
    )
    tipo_documento_enum.create(op.get_bind(), checkfirst=True)

    #  Agregar la columna con default
    op.add_column(
        'actas',
        sa.Column(
            'tipo_documento',
            sa.Enum(
                'CUENTA_COBRO',
                'FACTURA',
                name='tipo_documento_acta_enum'
            ),
            nullable=False,
            server_default='CUENTA_COBRO'
        )
    )


def downgrade():
    #  Eliminar la columna
    op.drop_column('actas', 'tipo_documento')

    #  Eliminar el ENUM
    tipo_documento_enum = postgresql.ENUM(
        'CUENTA_COBRO',
        'FACTURA',
        name='tipo_documento_acta_enum'
    )
    tipo_documento_enum.drop(op.get_bind(), checkfirst=True)