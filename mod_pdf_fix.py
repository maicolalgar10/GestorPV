import os

with open('controllers/dashboard_controller.py', 'r', encoding='utf-8') as f:
    ctrl_content = f.read()

# Vamos a reemplazar la función completa para asegurar que quede bien:
old_start = '''@dashboard_bp.route("/oficina/pagos-programados/exportar-pdf")'''

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
            prov_nombre = p.proveedor.nombre if (hasattr(p, 'proveedor') and p.proveedor) else "Proveedor N/A"
            cuenta_or = getattr(p, 'cuenta_origen', None)
            cuenta_or_texto = clean_text(cuenta_or) if cuenta_or else 'N/A'
            obs = getattr(p, 'observacion', None)
            
            consolidados.append({
                'fecha_programada': p.fecha_programada,
                'tipo': 'Proveedor',
                'entidad': clean_text(prov_nombre),
                'monto': float(p.monto or 0),
                'cuenta_origen': cuenta_or_texto,
                'concepto': clean_text(obs if obs else ''),
                'estado': clean_text(p.estado)
            })
            
        for p in pagos_tar:
            tar_nombre = p.tarjeta.nombre if (hasattr(p, 'tarjeta') and p.tarjeta) else "Tarjeta N/A"
            cuenta_or = getattr(p, 'cuenta_origen', None)
            cuenta_or_texto = clean_text(cuenta_or) if cuenta_or else 'N/A'
            obs = getattr(p, 'concepto', None)
            
            consolidados.append({
                'fecha_programada': p.fecha_programada,
                'tipo': 'Tarjeta',
                'entidad': clean_text(tar_nombre),
                'monto': float(p.monto or 0),
                'cuenta_origen': cuenta_or_texto,
                'concepto': clean_text(obs if obs else ''),
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
        return redirect(url_for("dashboard.dashboard_oficina"))
'''

if old_start in ctrl_content:
    parts = ctrl_content.split(old_start)
    new_content = parts[0] + new_endpoint
    with open('controllers/dashboard_controller.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("dashboard_controller.py modificado correctamente.")
else:
    print("No se encontro la ruta en dashboard_controller.py")
