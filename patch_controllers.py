import re

controllers = [
    'controllers/proveedores_controller.py',
    'controllers/trabajadores_controller.py'
]

for ctrl in controllers:
    with open(ctrl, 'r', encoding='utf-8') as f:
        c = f.read()

    # Add comentario = request.args.get("comentario", "").strip()
    c = re.sub(
        r'(def exportar_pdf_historial\(\):[\s\n]*fecha_inicio = [^\n]*\n)',
        r'\1    comentario = request.args.get("comentario", "").strip()\n',
        c
    )

    # Add PDF injection
    saldo_final_regex = r"(elements\.append\(Paragraph\(f\"<b>Saldo Final / Restante:</b> \{saldo_final_str\}\", styles\['Normal'\]\)\))"
    injection = r'''\1
    
    if comentario:
        elements.append(Spacer(1, 15))
        elements.append(Paragraph("<b>Observaciones / Notas del Reporte:</b>", styles['Normal']))
        elements.append(Paragraph(comentario, styles['Normal']))'''
    c = re.sub(saldo_final_regex, injection, c)
    
    with open(ctrl, 'w', encoding='utf-8') as f:
        f.write(c)
    print(f"Patched {ctrl}")
