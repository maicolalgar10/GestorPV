import re

with open('controllers/contratistas_controller.py', 'r', encoding='utf-8') as f:
    content = f.read()

# For crear_factura
crear_repl = '''            porcentaje_iva         = parse_pct(request.form.get("porcentaje_iva")),
            valor_cancelado        = limpiar_monto(request.form.get("valor_cancelado")),
            retencion              = parse_pct(request.form.get("retencion")),
            porcentaje_retegarantia= parse_pct(request.form.get("retegarantia")),'''

content = re.sub(
    r'porcentaje_iva\s*=\s*parse_pct\(request\.form\.get\("porcentaje_iva"\)\),\s*valor_cancelado\s*=\s*limpiar_monto\(request\.form\.get\("valor_cancelado"\)\),\s*retencion\s*=\s*parse_pct\(request\.form\.get\("retencion"\)\),',
    crear_repl,
    content,
    count=1
)

# For editar_factura
editar_repl = '''        factura.porcentaje_iva = parse_pct(request.form.get("porcentaje_iva"))
        factura.valor_cancelado = limpiar_monto(request.form.get("valor_cancelado"))
        factura.retencion = parse_pct(request.form.get("retencion"))
        factura.porcentaje_retegarantia = parse_pct(request.form.get("retegarantia"))'''

content = re.sub(
    r'factura\.porcentaje_iva = parse_pct\(request\.form\.get\("porcentaje_iva"\)\)\s*factura\.valor_cancelado = limpiar_monto\(request\.form\.get\("valor_cancelado"\)\)\s*factura\.retencion = parse_pct\(request\.form\.get\("retencion"\)\)',
    editar_repl,
    content,
    count=1
)

with open('controllers/contratistas_controller.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Updated controllers/contratistas_controller.py')
