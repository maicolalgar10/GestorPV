import os
from datetime import datetime as dt, date as d, time as t

# ======================
# Fechas
# ======================

def parse_fecha_ymd(ymd: str) -> dt:
    """Convierte 'YYYY-MM-DD' a datetime a medianoche (00:00:00)."""
    return dt.combine(dt.strptime(ymd, "%Y-%m-%d").date(), t.min)

def hoy_ymd() -> str:
    """Devuelve la fecha de hoy en formato YYYY-MM-DD."""
    return d.today().isoformat()

def _ymd_to_midnight(ymd: str) -> dt:
    """Convierte 'YYYY-MM-DD' a datetime con hora 00:00:00."""
    return dt.combine(dt.strptime(ymd, "%Y-%m-%d").date(), t.min)


# ======================
# Archivos
# ======================

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

def allowed_file(filename: str) -> bool:
    """Verifica si la extensión del archivo es permitida."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
