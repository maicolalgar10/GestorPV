import os

with open('controllers/dashboard_controller.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Imports
if 'from fpdf import FPDF' not in content:
    content = content.replace('from flask import ', 'import io\nfrom fpdf import FPDF\nfrom flask import send_file, ')

# 2. Endpoints
new_endpoints = '''
@dashboard_bp.route("/oficina/pagos-programados/exportar-pdf")
@login_required
@admin_oficina_required
def exportar_pdf_pagos_consolidados():
    from models import ProgramacionPagoProveedor, ProgramacionPagoTarjeta
    
    # 1. Consultar Proveedores
    pagos_prov = ProgramacionPagoProveedor.query.filter(ProgramacionPagoProveedor.estado != 'Realizado').all()
    # 2. Consultar Tarjetas
    pagos_tar = ProgramacionPagoTarjeta.query.filter(ProgramacionPagoTarjeta.estado != 'REALIZADO').all()
    
    # Unificar en una lista de diccionarios
    consolidados = []
    
    for p in pagos_prov:
        prov_nombre = p.proveedor.nombre if p.proveedor else "Desconocido"
        consolidados.append({
            'fecha_programada': p.fecha_programada,
            'tipo': 'Proveedor',
            'entidad': prov_nombre,
            'monto': p.monto,
            'cuenta_origen': p.cuenta_origen if p.cuenta_origen else 'N/A',
            'concepto': p.observacion if p.observacion else '',
            'estado': p.estado
        })
        
    for p in pagos_tar:
        tar_nombre = p.tarjeta.nombre if p.tarjeta else "Desconocida"
        consolidados.append({
            'fecha_programada': p.fecha_programada,
            'tipo': 'Tarjeta',
            'entidad': tar_nombre,
            'monto': p.monto,
            'cuenta_origen': p.cuenta_origen if p.cuenta_origen else 'N/A',
            'concepto': p.concepto if p.concepto else '',
            'estado': p.estado
        })
        
    # Ordenar por fecha
    consolidados.sort(key=lambda x: x['fecha_programada'])
    
    total_pendiente = sum(float(c['monto']) for c in consolidados)
    
    # Generar PDF
    pdf = FPDF(orientation='L', format="A4")
    pdf.add_page()
    pdf.set_margins(10, 15, 10)
    pdf.set_font("Helvetica", style="B", size=16)
    pdf.cell(0, 10, "REPORTE UNIFICADO DE PROXIMOS PAGOS PROGRAMADOS", align="C")
    pdf.ln(12)
    
    pdf.set_font("Helvetica", style="B", size=12)
    pdf.cell(0, 10, f"Total Pendiente: $ {total_pendiente:,.2f}", align="R")
    pdf.ln(12)
    
    pdf.set_font("Helvetica", style="B", size=9)
    pdf.set_fill_color(220, 220, 220)
    pdf.cell(25, 10, "FECHA", border=1, fill=True, align="C")
    pdf.cell(20, 10, "TIPO", border=1, fill=True, align="C")
    pdf.cell(50, 10, "ENTIDAD", border=1, fill=True, align="C")
    pdf.cell(30, 10, "MONTO", border=1, fill=True, align="C")
    pdf.cell(40, 10, "CUENTA ORIGEN", border=1, fill=True, align="C")
    pdf.cell(85, 10, "CONCEPTO", border=1, fill=True, align="C")
    pdf.cell(27, 10, "ESTADO", border=1, fill=True, align="C")
    pdf.ln(10)
    
    pdf.set_font("Helvetica", size=8)
    for p in consolidados:
        ent = (p['entidad'][:25] + '..') if len(p['entidad']) > 25 else p['entidad']
        cta = (str(p['cuenta_origen'])[:18] + '..') if len(str(p['cuenta_origen'])) > 18 else str(p['cuenta_origen'])
        con = (str(p['concepto'])[:50] + '..') if len(str(p['concepto'])) > 50 else str(p['concepto'])
        monto_str = f"$ {float(p['monto']):,.2f}"
        fecha_str = p['fecha_programada'].strftime('%d/%m/%Y')
        
        pdf.cell(25, 8, fecha_str, border=1, align="C")
        pdf.cell(20, 8, p['tipo'], border=1, align="C")
        pdf.cell(50, 8, ent, border=1)
        pdf.cell(30, 8, monto_str, border=1, align="R")
        pdf.cell(40, 8, cta, border=1)
        pdf.cell(85, 8, con, border=1)
        pdf.cell(27, 8, str(p['estado']), border=1, align="C")
        pdf.ln(8)
        
    pdf.ln(10)
    pdf.set_font("Helvetica", style="I", size=8)
    pdf.cell(0, 5, "Documento generado automaticamente por el Sistema.", align="L")
    
    byte_string = pdf.output()
    return send_file(
        io.BytesIO(byte_string),
        download_name="Reporte_Unificado_Pagos.pdf",
        mimetype="application/pdf"
    )
'''

if 'exportar_pdf_pagos_consolidados' not in content:
    content += new_endpoints

with open('controllers/dashboard_controller.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('dashboard_controller.py actualizado con exito.')
