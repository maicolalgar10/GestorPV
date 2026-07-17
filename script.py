import os
import re

# 1. Models
models_path = 'models.py'
with open(models_path, 'r', encoding='utf-8') as f:
    models_content = f.read()

# We'll append the new models at the end
if 'class Contratista(db.Model):' not in models_content:
    new_models = '''
# ===========================================
# Contratistas
# ===========================================
class Contratista(db.Model):
    __tablename__ = "contratistas"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(200), nullable=False, unique=True, index=True)
    nit = db.Column(db.String(50), nullable=True)
    telefono = db.Column(db.String(50), nullable=True)
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)

class ContratistaFactura(db.Model):
    __tablename__ = "contratista_facturas"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # ─── Identificación ─────────────────────────────────────────────
    nombre_contratista = db.Column(db.String(200), nullable=False, index=True)

    # ─── Documentos (URLs de Supabase Storage) ──────────────────────
    orden_compra_url      = db.Column(db.String(500), nullable=True)
    comprobante_compra_url = db.Column(db.String(500), nullable=True)
    banco_pago_url        = db.Column(db.String(500), nullable=True)

    # ─── Fechas ──────────────────────────────────────────────────────
    fecha_factura     = db.Column(db.Date, nullable=False)
    plazo_dias        = db.Column(db.Integer, nullable=False, default=0)
    fecha_vencimiento = db.Column(db.Date, nullable=False)
    fecha_pago        = db.Column(db.Date, nullable=True)

    # ─── Valores monetarios ──────────────────────────────────────────
    valor_neto      = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    valor_cancelado = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    retencion       = db.Column(db.Numeric(14, 2), nullable=False, default=0)

    # ─── Auditoría ───────────────────────────────────────────────────
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)
    porcentaje_iva = db.Column(db.Numeric(14, 2), nullable=False, default=19.0)

    # ─── Campos calculados (@property) ───────────────────────────────
    @property
    def iva(self):
        try:
            pct = float(self.porcentaje_iva) if self.porcentaje_iva is not None else 19.0
            return round(float(self.valor_neto or 0) * (pct / 100.0), 2)
        except (ValueError, TypeError):
            return 0.0

    @property
    def valor_total(self):
        try:
            return round(float(self.valor_neto or 0) + self.iva, 2)
        except (ValueError, TypeError):
            return 0.0

    @property
    def retencion_pesos(self):
        try:
            return float(self.valor_neto or 0) * (float(self.retencion or 0) / 100.0)
        except (ValueError, TypeError):
            return 0.0

    @property
    def total_adeudado(self):
        try:
            return round(self.valor_total - self.retencion_pesos - float(self.valor_cancelado or 0), 2)
        except (ValueError, TypeError):
            return 0.0

    @property
    def dias_mora(self):
        if self.fecha_pago is not None:
            return 0
        if self.fecha_vencimiento:
            delta = (datetime.utcnow().date() - self.fecha_vencimiento).days
            return max(0, delta)
        return 0

    @property
    def estado_factura(self):
        if self.fecha_pago is not None:
            return "Pagada"
        if self.dias_mora > 0:
            return "Vencida"
        return "Pendiente"

    @property
    def estado_cuenta(self):
        if self.total_adeudado <= 0:
            return "AL DÍA"
        elif self.dias_mora > 0:
            return "MORA"
        return "POR PAGAR"
'''
    with open(models_path, 'a', encoding='utf-8') as f:
        f.write(new_models)
