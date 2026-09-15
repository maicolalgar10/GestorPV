from flask import Blueprint, request, redirect, url_for, flash, render_template, send_file
import io
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from models import db, ProgramacionPagoProveedor
from decorators import login_required, admin_oficina_required
from datetime import datetime as dt

proveedores_bp = Blueprint("proveedores", __name__, url_prefix="/proveedores")

@proveedores_bp.route("/programar_pago", methods=["POST"])
@login_required
@admin_oficina_required
def programar_pago():
    try:
        proveedor_id = request.form.get("proveedor_id")
        fecha_raw = request.form.get("fecha_programada")
        monto_raw = request.form.get("monto", "0")
        observacion = request.form.get("observacion", "").strip()

        fecha_programada = dt.strptime(fecha_raw, "%Y-%m-%d").date() if fecha_raw else None
        
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

        if not proveedor_id or not fecha_programada or monto <= 0:
            flash("Datos inválidos para programar el pago.", "danger")
            return redirect(url_for("dashboard.proveedores"))

        nuevo_pago = ProgramacionPagoProveedor(
            proveedor_id=proveedor_id,
            fecha_programada=fecha_programada,
            monto=monto,
            observacion=observacion,
            estado='Programado'
        )
        db.session.add(nuevo_pago)
        db.session.commit()
        flash("Pago programado correctamente.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error al programar pago: {e}", "danger")

    return redirect(url_for("dashboard.proveedores"))

@proveedores_bp.route("/programacion/cambiar_estado/<int:id>", methods=["POST"])
@login_required
@admin_oficina_required
def cambiar_estado(id):
    pago = ProgramacionPagoProveedor.query.get_or_404(id)
    try:
        nuevo_estado = request.form.get("estado")
        if nuevo_estado in ['Programado', 'Realizado', 'Cancelado']:
            pago.estado = nuevo_estado
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

    pagos = query.order_by(ProgramacionPagoProveedor.fecha_programada.desc()).all()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter), rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    elements = []
    styles = getSampleStyleSheet()

    # Título
    title = Paragraph("Historial de Pagos a Proveedores", styles['Title'])
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

    # Tabla
    data = [['Fecha', 'Proveedor', 'Monto Pagado', 'Observación', 'Estado']]
    
    total = 0
    for p in pagos:
        prov_nombre = p.proveedor.nombre if (hasattr(p, 'proveedor') and p.proveedor) else 'N/A'
        fecha_str = p.fecha_programada.strftime('%d/%m/%Y') if p.fecha_programada else ''
        monto = float(p.monto or 0)
        total += monto
        monto_str = f"${monto:,.0f}".replace(",", ".")
        data.append([fecha_str, prov_nombre, monto_str, p.observacion or '', 'Realizado'])

    table = Table(data, colWidths=[80, 200, 100, 250, 70])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#10b981")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    
    elements.append(table)
    elements.append(Spacer(1, 20))
    
    total_str = f"${total:,.0f}".replace(",", ".")
    elements.append(Paragraph(f"<b>Total Pagado:</b> {total_str}", styles['Normal']))

    doc.build(elements)
    buffer.seek(0)
    
    return send_file(
        buffer,
        as_attachment=True,
        download_name="Historial_Pagos_Proveedores.pdf",
        mimetype="application/pdf"
    )
