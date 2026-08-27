from flask import Blueprint, request, redirect, url_for, flash, render_template
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

        pagos_programados = ProgramacionPagoProveedor.query.order_by(ProgramacionPagoProveedor.fecha_programada.asc()).all()

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

@proveedores_bp.route("/programacion/historial", methods=["GET"])
@login_required
@admin_oficina_required
def historial_pagos():
    fecha_busqueda = request.args.get("fecha")
    
    query = ProgramacionPagoProveedor.query.filter_by(estado='Realizado')
    
    if fecha_busqueda:
        try:
            fecha_obj = dt.strptime(fecha_busqueda, "%Y-%m-%d").date()
            query = query.filter(ProgramacionPagoProveedor.fecha_programada == fecha_obj)
        except ValueError:
            flash("Formato de fecha inválido.", "warning")
            
    pagos_realizados = query.order_by(ProgramacionPagoProveedor.fecha_programada.desc()).all()
    
    total_pagado = sum(float(pago.monto or 0.0) for pago in pagos_realizados)
    
    return render_template(
        "historial_pagos_proveedores.html",
        pagos=pagos_realizados,
        total_pagado=total_pagado,
        fecha_busqueda=fecha_busqueda
    )
