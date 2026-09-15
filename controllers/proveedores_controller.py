from flask import Blueprint, request, redirect, url_for, flash, render_template, send_file, current_app
import io
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from models import db, ProgramacionPagoProveedor, ProgramacionPagoTarjeta
import os
from reportlab.platypus import Image
from reportlab.lib.units import inch
from reportlab.lib.styles import ParagraphStyle
from decorators import login_required, admin_oficina_required
from datetime import datetime as dt

proveedores_bp = Blueprint("proveedores", __name__, url_prefix="/proveedores")

@proveedores_bp.route("/programar_pago", methods=["POST"])
@login_required
@admin_oficina_required
def programar_pago():
    try:
        proveedor_id = request.form.get('proveedor_id')
        monto = request.form.get('monto')
        fecha_programada = request.form.get('fecha_programada')
        observacion = request.form.get('observacion', '')
        subproyecto_id = request.form.get('subproyecto_id') or None

        if not proveedor_id or not monto or not fecha_programada:
            flash("Por favor complete todos los campos obligatorios (Proveedor, Monto y Fecha).", "warning")
            return redirect(url_for('dashboard.proveedores'))

        nuevo_pago = ProgramacionPagoProveedor(
            proveedor_id=int(proveedor_id),
            monto=float(monto),
            fecha_programada=dt.strptime(fecha_programada, '%Y-%m-%d').date(),
            observacion=observacion,
            estado='Programado',
            subproyecto_id=int(subproyecto_id) if subproyecto_id else None
        )
        
        db.session.add(nuevo_pago)
        db.session.commit()
        flash("Pago programado exitosamente.", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"Error al programar pago: {str(e)}", "danger")

    return redirect(url_for('dashboard.proveedores'))

@proveedores_bp.route("/programacion/cambiar_estado/<int:id>", methods=["POST"])
@login_required
@admin_oficina_required
def cambiar_estado(id):
    pago = ProgramacionPagoProveedor.query.get_or_404(id)
    try:
        nuevo_estado = request.form.get("estado")
        forma_pago = request.form.get("forma_pago")
        if nuevo_estado in ['Programado', 'Realizado', 'Cancelado']:
            pago.estado = nuevo_estado
            if nuevo_estado == 'Realizado' and forma_pago:
                pago.forma_pago = forma_pago
            db.session.commit()
            flash(f"Estado del pago actualizado a {nuevo_estado}.", "success")
        else:
            flash("Estado inválido.", "danger")
    except Exception as e:
        db.session.rollback()
        flash(f"Error al actualizar estado: {e}", "danger")
    return redirect(url_for("dashboard.proveedores"))

@proveedores_bp.route("/programacion_pago/editar/<int:id>", methods=["POST"])
@login_required
@admin_oficina_required
def editar_programacion(id):
    pago = ProgramacionPagoProveedor.query.get_or_404(id)
    try:
        fecha_raw = request.form.get("fecha_programada")
        monto_raw = request.form.get("monto", "0")
        observacion = request.form.get("observacion", "").strip()

        if fecha_raw:
            pago.fecha_programada = dt.strptime(fecha_raw, "%Y-%m-%d").date()
        
        monto_limpio = str(monto_raw).replace('$', '').replace(' ', '')
        if ',' in monto_limpio and '.' in monto_limpio:
            monto_limpio = monto_limpio.replace('.', '').replace(',', '.')
        elif ',' in monto_limpio:
            monto_limpio = monto_limpio.replace(',', '.')
        elif '.' in monto_limpio:
            partes = monto_limpio.split('.')
            if len(partes[-1]) == 3:
                monto_limpio = monto_limpio.replace('.', '')
        monto = float(monto_limpio) if monto_limpio else 0.0
        
        if monto > 0:
            pago.monto = monto
        
        pago.observacion = observacion
        
        db.session.commit()
        flash("Programación de pago actualizada correctamente.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error al editar programación: {e}", "danger")
    return redirect(url_for("dashboard.proveedores"))

@proveedores_bp.route("/programacion/eliminar/<int:id>", methods=["POST"])
@login_required
@admin_oficina_required
def eliminar_programacion(id):
    pago = ProgramacionPagoProveedor.query.get_or_404(id)
    try:
        db.session.delete(pago)
        db.session.commit()
        flash("Programación de pago eliminada.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error al eliminar programación: {e}", "danger")
    return redirect(url_for("dashboard.proveedores"))

@proveedores_bp.route("/programacion/pdf", methods=["GET"])
@login_required
@admin_oficina_required
def generar_pdf_programacion():
    try:
        from models import ProveedorFactura, ProgramacionPagoProveedor
        
        facturas = ProveedorFactura.query.all()
        # Calcular dinámicamente el valor_cancelado basado en las subfacturas si existen
        for f in facturas:
            if hasattr(f, 'subfacturas') and f.subfacturas:
                f.valor_cancelado = sum(float(sf.valor or 0) for sf in f.subfacturas)

        deuda_por_proveedor = {}
        for factura in facturas:
            nombre = factura.nombre_proveedor
            deuda_por_proveedor[nombre] = deuda_por_proveedor.get(nombre, 0) + float(factura.total_adeudado or 0)

        pagos_programados = ProgramacionPagoProveedor.query.filter(ProgramacionPagoProveedor.estado != 'Realizado').order_by(ProgramacionPagoProveedor.fecha_programada.asc()).all()

        total_programado = 0.0
        for pago in pagos_programados:
            prov_nombre = pago.proveedor.nombre if pago.proveedor else "Desconocido"
            pago.deuda_actual = float(deuda_por_proveedor.get(prov_nombre, 0.0))
            monto_val = float(pago.monto or 0.0)
            pago.saldo_restante = pago.deuda_actual - monto_val
            total_programado += monto_val

        return render_template(
            "pdf_pagos_programados.html",
            pagos_programados=pagos_programados,
            total_programado=total_programado,
            fecha_reporte=dt.now()
        )
    except Exception as e:
        print(f"Error generando PDF de pagos programados: {e}")
        flash(f"Error al generar el reporte PDF: {str(e)}", "danger")
        return redirect(url_for("dashboard.proveedores"))

@proveedores_bp.route("/historial_pagos", methods=["GET"])
@login_required
@admin_oficina_required
def historial_pagos():
    fecha_inicio = request.args.get("fecha_inicio")
    fecha_fin = request.args.get("fecha_fin")
    
    query = ProgramacionPagoProveedor.query.filter(ProgramacionPagoProveedor.estado.ilike('Realizado'))
    
    if fecha_inicio:
        try:
            f_inicio = dt.strptime(fecha_inicio, "%Y-%m-%d").date()
            query = query.filter(ProgramacionPagoProveedor.fecha_programada >= f_inicio)
        except ValueError:
            pass
            
    if fecha_fin:
        try:
            f_fin = dt.strptime(fecha_fin, "%Y-%m-%d").date()
            query = query.filter(ProgramacionPagoProveedor.fecha_programada <= f_fin)
        except ValueError:
            pass
            
    pagos_realizados = query.order_by(ProgramacionPagoProveedor.fecha_programada.desc()).all()
    
    total_pagado = sum(float(pago.monto or 0.0) for pago in pagos_realizados)
    
    return render_template(
        "historial_pagos_proveedores.html",
        pagos=pagos_realizados,
        total_pagado=total_pagado
    )

@proveedores_bp.route("/oficina/proveedores/historial/exportar-pdf")
@login_required
@admin_oficina_required
def exportar_pdf_historial():
    fecha_inicio = request.args.get("fecha_inicio")
    fecha_fin = request.args.get("fecha_fin")
    saldo_inicial_str = request.args.get("saldo_inicial", "0")
    
    try:
        saldo_inicial = float(saldo_inicial_str)
    except ValueError:
        saldo_inicial = 0.0

    # Query Proveedores
    query_prov = ProgramacionPagoProveedor.query.filter(ProgramacionPagoProveedor.estado.ilike('Realizado'))
    # Query Tarjetas
    query_tarj = ProgramacionPagoTarjeta.query.filter(ProgramacionPagoTarjeta.estado.ilike('REALIZADO'))

    if fecha_inicio:
        try:
            f_inicio = dt.strptime(fecha_inicio, "%Y-%m-%d").date()
            query_prov = query_prov.filter(ProgramacionPagoProveedor.fecha_programada >= f_inicio)
            query_tarj = query_tarj.filter(ProgramacionPagoTarjeta.fecha_programada >= f_inicio)
        except ValueError:
            pass

    if fecha_fin:
        try:
            f_fin = dt.strptime(fecha_fin, "%Y-%m-%d").date()
            query_prov = query_prov.filter(ProgramacionPagoProveedor.fecha_programada <= f_fin)
            query_tarj = query_tarj.filter(ProgramacionPagoTarjeta.fecha_programada <= f_fin)
        except ValueError:
            pass

    pagos_prov = query_prov.all()
    pagos_tarj = query_tarj.all()
    
    unificados = []
    
    for p in pagos_prov:
        prov_nombre = p.proveedor.nombre if (hasattr(p, 'proveedor') and p.proveedor) else 'N/A'
        unificados.append({
            'fecha': p.fecha_programada,
            'tipo': 'Proveedor',
            'entidad': prov_nombre,
            'monto': float(p.monto or 0),
            'forma_pago': p.forma_pago or 'N/A',
            'concepto': p.observacion or '',
            'estado': 'Realizado'
        })
        
    for t in pagos_tarj:
        tarj_nombre = t.tarjeta.nombre if (hasattr(t, 'tarjeta') and t.tarjeta) else 'N/A'
        unificados.append({
            'fecha': t.fecha_programada,
            'tipo': 'Tarjeta',
            'entidad': tarj_nombre,
            'monto': float(t.monto or 0),
            'forma_pago': t.forma_pago or t.cuenta_origen or 'N/A',
            'concepto': t.concepto or '',
            'estado': 'Realizado'
        })
        
    # Sort by fecha desc
    unificados.sort(key=lambda x: x['fecha'], reverse=True)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter), rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    elements = []
    styles = getSampleStyleSheet()

    # Logo
    logo_path = os.path.join(current_app.root_path, 'static', 'uploads', 'logos', 'corseing_logo.png')
    
    if os.path.exists(logo_path):
        try:
            img = Image(logo_path, width=2.0*inch, height=0.75*inch)
            img.hAlign = 'LEFT'
            elements.append(img)
            elements.append(Spacer(1, 10))
        except Exception:
            pass
            
    # Título y fecha de generacion
    fecha_gen = dt.now().strftime("%d/%m/%Y %H:%M")
    elements.append(Paragraph(f"Fecha de Generación: {fecha_gen}", styles['Normal']))
    elements.append(Spacer(1, 12))
    
    title = Paragraph("REPORTE UNIFICADO DE PAGOS REALIZADOS", styles['Title'])
    elements.append(title)
    
    subtitle_text = "Filtro: "
    if fecha_inicio and fecha_fin:
        subtitle_text += f"{fecha_inicio} al {fecha_fin}"
    elif fecha_inicio:
        subtitle_text += f"Desde {fecha_inicio}"
    elif fecha_fin:
        subtitle_text += f"Hasta {fecha_fin}"
    else:
        subtitle_text += "Todos los registros"
        
    elements.append(Paragraph(subtitle_text, styles['Normal']))
    elements.append(Spacer(1, 12))

    # Cell Style
    cell_style = ParagraphStyle(
        'GridCell',
        fontName='Helvetica',
        fontSize=8,
        leading=10,
        alignment=0 # Left
    )
    
    header_style = ParagraphStyle(
        'HeaderCell',
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=11,
        alignment=1, # Center
        textColor=colors.whitesmoke
    )

    # Tabla
    data = [[
        Paragraph('FECHA', header_style),
        Paragraph('TIPO', header_style),
        Paragraph('ENTIDAD', header_style),
        Paragraph('MONTO', header_style),
        Paragraph('FORMA PAGO / ORIGEN', header_style),
        Paragraph('CONCEPTO', header_style),
        Paragraph('ESTADO', header_style)
    ]]
    
    total = 0
    for u in unificados:
        fecha_str = u['fecha'].strftime('%d/%m/%Y') if u['fecha'] else ''
        monto_str = f"${u['monto']:,.0f}".replace(",", ".")
        total += u['monto']
        
        data.append([
            Paragraph(fecha_str, cell_style),
            Paragraph(str(u['tipo']), cell_style),
            Paragraph(str(u['entidad']), cell_style),
            Paragraph(monto_str, cell_style),
            Paragraph(str(u['forma_pago']), cell_style),
            Paragraph(str(u['concepto']), cell_style),
            Paragraph(str(u['estado']), cell_style)
        ])

    colWidths = [1.0*inch, 0.9*inch, 2.2*inch, 1.2*inch, 1.3*inch, 1.5*inch, 0.9*inch]
    table = Table(data, colWidths=colWidths)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#10b981")),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    
    elements.append(table)
    elements.append(Spacer(1, 20))
    
    saldo_inicial_str_fmt = f"${saldo_inicial:,.0f}".replace(",", ".")
    total_str = f"${total:,.0f}".replace(",", ".")
    saldo_final = saldo_inicial - total
    saldo_final_str = f"${saldo_final:,.0f}".replace(",", ".")
    
    # Pie de pagina
    elements.append(Paragraph(f"<b>Saldo Inicial:</b> {saldo_inicial_str_fmt}", styles['Normal']))
    elements.append(Paragraph(f"<b>Total Pagado:</b> {total_str}", styles['Normal']))
    elements.append(Paragraph(f"<b>Saldo Final / Restante:</b> {saldo_final_str}", styles['Normal']))
    
    elements.append(Spacer(1, 40))
    
    # Firmas
    firmas_data = [
        ["_______________________", "_______________________", "_______________________"],
        ["ELABORÓ", "REVISÓ", "APROBÓ"]
    ]
    tabla_firmas = Table(firmas_data, colWidths=[2.5*inch, 2.5*inch, 2.5*inch])
    tabla_firmas.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,1), (-1,1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,1), (-1,1), 9),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))
    elements.append(tabla_firmas)

    doc.build(elements)
    buffer.seek(0)
    
    return send_file(
        buffer,
        as_attachment=True,
        download_name="Reporte_Unificado_Pagos.pdf",
        mimetype="application/pdf"
    )
