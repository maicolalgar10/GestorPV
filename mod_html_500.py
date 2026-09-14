import os

# 1. Ajuste HTML
with open('templates/trabajadores/tarjetas.html', 'r', encoding='utf-8') as f:
    content = f.read()

old_header = '''      <div class="card-header bg-white border-0 py-3 d-flex justify-content-between align-items-center" data-bs-toggle="collapse" data-bs-target="#collapsePagos" style="cursor: pointer; border-radius: 16px 16px 0 0;">
        <h5 class="mb-0 fw-bold text-primary">
          <i class="bi bi-calendar-check me-2"></i> Próximos Pagos Programados
        </h5>
        <div>
          <button type="button" class="btn btn-sm btn-outline-secondary me-2" data-bs-toggle="modal" data-bs-target="#modalHistorialPagosTarjetas" onclick="event.stopPropagation();">
            <i class="bi bi-clock-history"></i> Historial de Pagos
          </button>
          <a href="{{ url_for('dashboard.exportar_pdf_pagos_consolidados') }}" class="btn btn-sm btn-outline-danger me-2" target="_blank" onclick="event.stopPropagation();">
            <i class="bi bi-file-earmark-pdf"></i> Exportar PDF
          </a>
          <button class="btn btn-sm btn-outline-primary rounded-circle"><i class="bi bi-chevron-down"></i></button>
        </div>
      </div>'''

new_header = '''      <div class="card-header bg-white border-0 py-3 d-flex justify-content-between align-items-center" style="border-radius: 16px 16px 0 0;">
        <h5 class="mb-0 fw-bold text-primary">
          <i class="bi bi-calendar-check me-2"></i> Próximos Pagos Programados
        </h5>
        <div>
          <button type="button" class="btn btn-sm btn-outline-secondary me-2" data-bs-toggle="modal" data-bs-target="#modalHistorialPagosTarjetas">
            <i class="bi bi-clock-history"></i> Historial de Pagos
          </button>
          <a href="{{ url_for('dashboard.exportar_pdf_pagos_consolidados') }}" target="_blank" class="btn btn-danger btn-sm fw-bold shadow-sm me-2">
            <i class="bi bi-file-earmark-pdf"></i> Exportar PDF
          </a>
          <button class="btn btn-sm btn-outline-primary rounded-circle" data-bs-toggle="collapse" data-bs-target="#collapsePagos"><i class="bi bi-chevron-down"></i></button>
        </div>
      </div>'''

if old_header in content:
    content = content.replace(old_header, new_header)
else:
    print('No se encontro el bloque old_header en tarjetas.html')

with open('templates/trabajadores/tarjetas.html', 'w', encoding='utf-8') as f:
    f.write(content)

# Opcionalmente quitar onclick="event.stopPropagation();" de proveedores.html si existía en el encabezado
with open('templates/proveedores.html', 'r', encoding='utf-8') as f:
    prov_content = f.read()

# En proveedores.html también haremos que el botón de PDF sea directo (si estaba dentro de un colapso, el usuario dijo "y proveedores.html si aplica")
# Ya le agregamos onclick antes, pero lo reemplazaremos por el formato que dio el usuario:
old_btn = 'href="{{ url_for(\'dashboard.exportar_pdf_pagos_consolidados\') }}" class="btn btn-sm btn-danger" target="_blank" title="Exportar PDF" onclick="event.stopPropagation();"'
new_btn = 'href="{{ url_for(\'dashboard.exportar_pdf_pagos_consolidados\') }}" class="btn btn-danger btn-sm fw-bold shadow-sm" target="_blank" title="Exportar PDF"'
if old_btn in prov_content:
    prov_content = prov_content.replace(old_btn, new_btn)

with open('templates/proveedores.html', 'w', encoding='utf-8') as f:
    f.write(prov_content)


# 2. Ajuste Controlador 500
with open('controllers/dashboard_controller.py', 'r', encoding='utf-8') as f:
    ctrl_content = f.read()

import re

# Modificaremos la ruta de exportación
old_export = '''@dashboard_bp.route("/oficina/pagos-programados/exportar-pdf")
@login_required
@admin_oficina_required
def exportar_pdf_pagos_consolidados():'''

# Remplazar todo el cuerpo de exportar_pdf_pagos_consolidados
# Primero encontraremos todo desde "@dashboard_bp.route...exportar_pdf_pagos_consolidados():" hasta el final del archivo
# (ya que este fue el ultimo bloque que añadimos)

# Limpiar acentos y eñes
def clean_text(text):
    if not text:
        return ""
    import unicodedata
    return unicodedata.normalize('NFKD', str(text)).encode('ASCII', 'ignore').decode('utf-8')

new_endpoint = '''@dashboard_bp.route("/oficina/pagos-programados/exportar-pdf")
@login_required
@admin_oficina_required
def exportar_pdf_pagos_consolidados():
    try:
        from models import ProgramacionPagoProveedor, ProgramacionPagoTarjeta
        
        pagos_prov = ProgramacionPagoProveedor.query.filter(ProgramacionPagoProveedor.estado != 'Realizado').all()
        pagos_tar = ProgramacionPagoTarjeta.query.filter(ProgramacionPagoTarjeta.estado != 'REALIZADO').all()
        
        consolidados = []
        
        import unicodedata
        def clean_text(text):
            if not text: return ""
            return unicodedata.normalize('NFKD', str(text)).encode('ASCII', 'ignore').decode('utf-8')

        for p in pagos_prov:
            prov_nombre = clean_text(p.proveedor.nombre if (hasattr(p, 'proveedor') and p.proveedor) else "S/N")
            consolidados.append({
                'fecha_programada': p.fecha_programada,
                'tipo': 'Proveedor',
                'entidad': prov_nombre,
                'monto': float(p.monto or 0),
                'cuenta_origen': clean_text(p.cuenta_origen if p.cuenta_origen else 'N/A'),
                'concepto': clean_text(p.observacion if hasattr(p, 'observacion') and p.observacion else ''),
                'estado': clean_text(p.estado)
            })
            
        for p in pagos_tar:
            tar_nombre = clean_text(p.tarjeta.nombre if (hasattr(p, 'tarjeta') and p.tarjeta) else "S/N")
            consolidados.append({
                'fecha_programada': p.fecha_programada,
                'tipo': 'Tarjeta',
                'entidad': tar_nombre,
                'monto': float(p.monto or 0),
                'cuenta_origen': clean_text(p.cuenta_origen if p.cuenta_origen else 'N/A'),
                'concepto': clean_text(p.concepto if hasattr(p, 'concepto') and p.concepto else ''),
                'estado': clean_text(p.estado)
            })
            
        consolidados.sort(key=lambda x: x['fecha_programada'])
        
        total_pendiente = sum(c['monto'] for c in consolidados)
        
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
            monto_str = f"$ {p['monto']:,.2f}"
            fecha_str = p['fecha_programada'].strftime('%d/%m/%Y') if hasattr(p['fecha_programada'], 'strftime') else str(p['fecha_programada'])
            
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
    except Exception as e:
        import traceback
        print(f"Error generando PDF: {str(e)}")
        print(traceback.format_exc())
        flash(f"Error generando PDF: {str(e)}", "danger")
        return redirect(url_for("dashboard.oficina"))
'''

# Hacemos split con la firma de la funcion para re-escribir todo el final del archivo
if old_export in ctrl_content:
    parts = ctrl_content.split(old_export)
    new_content = parts[0] + new_endpoint
    with open('controllers/dashboard_controller.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("dashboard_controller.py modificado correctamente.")
else:
    print("No se encontro exportar_pdf_pagos_consolidados en dashboard_controller.py")
