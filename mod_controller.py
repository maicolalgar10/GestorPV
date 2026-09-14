import os

with open('controllers/trabajadores_controller.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Imports
if 'from fpdf import FPDF' not in content:
    content = content.replace('from flask import ', 'import io\nfrom fpdf import FPDF\nfrom flask import send_file, ')

# 2. Modificar tarjetas()
old_tarjetas = '''    pagos_programados = ProgramacionPagoTarjeta.query.order_by(ProgramacionPagoTarjeta.fecha_programada.asc()).all()
    return render_template("trabajadores/tarjetas.html", usuario=usuario, tarjetas=tarjetas_lista, pagos_programados=pagos_programados)'''
new_tarjetas = '''    pagos_programados = ProgramacionPagoTarjeta.query.filter(ProgramacionPagoTarjeta.estado != 'REALIZADO').order_by(ProgramacionPagoTarjeta.fecha_programada.asc()).all()
    historial_pagos = ProgramacionPagoTarjeta.query.filter_by(estado='REALIZADO').order_by(ProgramacionPagoTarjeta.fecha_programada.desc()).all()
    return render_template("trabajadores/tarjetas.html", usuario=usuario, tarjetas=tarjetas_lista, pagos_programados=pagos_programados, historial_pagos=historial_pagos)'''
content = content.replace(old_tarjetas, new_tarjetas)

# 3. Add Endpoints
new_endpoints = '''
@trabajadores_bp.route("/oficina/trabajadores/tarjetas/marcar-pagado/<int:id>", methods=["POST"])
@login_required
@admin_oficina_required
def marcar_pagado_tarjeta(id):
    try:
        pago = ProgramacionPagoTarjeta.query.get_or_404(id)
        pago.estado = 'REALIZADO'
        db.session.commit()
        flash("Pago marcado como REALIZADO correctamente", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error al marcar el pago: {str(e)}", "danger")
    return redirect(url_for("trabajadores.tarjetas"))

@trabajadores_bp.route("/oficina/trabajadores/tarjetas/exportar-pdf")
@login_required
@admin_oficina_required
def exportar_pdf_tarjetas():
    pagos = ProgramacionPagoTarjeta.query.order_by(ProgramacionPagoTarjeta.fecha_programada.asc()).all()
    
    pdf = FPDF(orientation='L', format="A4")
    pdf.add_page()
    pdf.set_margins(15, 15, 15)
    pdf.set_font("Helvetica", style="B", size=16)
    pdf.cell(0, 10, "REPORTE DE PROGRAMACION DE PAGOS - TARJETAS", align="C")
    pdf.ln(15)
    
    pdf.set_font("Helvetica", style="B", size=10)
    pdf.set_fill_color(220, 220, 220)
    pdf.cell(30, 10, "FECHA", border=1, fill=True, align="C")
    pdf.cell(50, 10, "TARJETA", border=1, fill=True, align="C")
    pdf.cell(35, 10, "MONTO", border=1, fill=True, align="C")
    pdf.cell(50, 10, "CUENTA ORIGEN", border=1, fill=True, align="C")
    pdf.cell(70, 10, "CONCEPTO", border=1, fill=True, align="C")
    pdf.cell(30, 10, "ESTADO", border=1, fill=True, align="C")
    pdf.ln(10)
    
    pdf.set_font("Helvetica", size=9)
    for p in pagos:
        tarjeta_nombre = p.tarjeta.nombre if p.tarjeta and p.tarjeta.nombre else 'Desconocida'
        # Truncar textos largos
        t_n = (tarjeta_nombre[:20] + '..') if len(tarjeta_nombre) > 20 else tarjeta_nombre
        c_o = (p.cuenta_origen[:20] + '..') if p.cuenta_origen and len(p.cuenta_origen) > 20 else str(p.cuenta_origen)
        con = (p.concepto[:35] + '..') if p.concepto and len(p.concepto) > 35 else str(p.concepto)
        
        pdf.cell(30, 8, p.fecha_programada.strftime('%d/%m/%Y'), border=1, align="C")
        pdf.cell(50, 8, t_n, border=1)
        pdf.cell(35, 8, f"$ {p.monto:,.2f}", border=1, align="R")
        pdf.cell(50, 8, c_o, border=1)
        pdf.cell(70, 8, con, border=1)
        pdf.cell(30, 8, str(p.estado), border=1, align="C")
        pdf.ln(8)
        
    pdf.ln(10)
    pdf.set_font("Helvetica", style="I", size=8)
    pdf.cell(0, 5, "Documento generado automaticamente.", align="L")
    
    byte_string = pdf.output()
    return send_file(
        io.BytesIO(byte_string),
        download_name="Reporte_Pagos_Tarjetas.pdf",
        mimetype="application/pdf"
    )
'''

if 'marcar-pagado' not in content:
    content += new_endpoints

with open('controllers/trabajadores_controller.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('trabajadores_controller.py actualizado con exito.')
