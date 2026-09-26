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

def clean_amount(val) -> float:
    """Limpia una cadena de monto (ej. $ 1.234.567,89) y la convierte a float."""
    if not val:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
        
    val_str = str(val).strip().replace('$', '').replace(' ', '')
    
    if ',' in val_str:
        # Formato colombiano: 1.134.850,00 -> quita puntos, coma a punto
        val_str = val_str.replace('.', '').replace(',', '.')
    else:
        # No hay coma. Puede ser un número puro como 1134850.00 o miles como 1.134.850
        partes = val_str.split('.')
        if len(partes) > 2:
            # Múltiples puntos, son miles
            val_str = val_str.replace('.', '')
        elif len(partes) == 2:
            # Un solo punto. Si tiene exactamente 3 dígitos después, asumimos que son miles (ej. 1.234)
            if len(partes[1]) == 3:
                val_str = val_str.replace('.', '')
            # De lo contrario, es un decimal puro (ej. 1134850.00 o 1134850.5), lo dejamos intacto
            
    try:
        return float(val_str)
    except ValueError:
        return 0.0
