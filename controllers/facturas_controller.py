from flask import Blueprint, render_template, request, redirect, flash
from decorators import login_required
from models import db, Factura, Cotizacion, Actas
from decorators import login_required
from werkzeug.utils import secure_filename
from decimal import Decimal
import os
from datetime import datetime

facturas_bp = Blueprint("facturas", __name__, url_prefix="/facturas")

@facturas_bp.route("/crear", methods=["POST"])
@login_required
def crear_factura():
    cotizacion_id = int(request.form.get("cotizacion_id"))
    cotizacion = Cotizacion.query.get_or_404(cotizacion_id)

    if cotizacion.estado != "ACEPTADA":
        flash("Solo se puede facturar una cotización aceptada", "danger")
        return redirect(request.referrer)

    if cotizacion.factura:
        flash("Esta cotización ya tiene una factura asociada", "warning")
        return redirect(request.referrer)

    try:
        total_factura = Decimal(request.form.get("total", 0))
        total_sin_iva = Decimal(request.form.get("total_sin_iva", 0))

        porcentaje_anticipo = Decimal(request.form.get("porcentaje_anticipo", 0))

        if total_factura <= 0:
            flash("El total de la factura debe ser mayor a 0", "danger")
            return redirect(request.referrer)

        if porcentaje_anticipo < 0 or porcentaje_anticipo > 100:
            flash("El porcentaje de anticipo debe estar entre 0 y 100", "danger")
            return redirect(request.referrer)
        
        if total_sin_iva <= 0:
            flash("El total sin IVA debe ser mayor a 0", "danger")
            return redirect(request.referrer)


        # CÁLCULO DEL ANTICIPO
        anticipo_inicial = (total_factura * porcentaje_anticipo) / Decimal("100")

        factura = Factura(
            cotizacion_id=cotizacion.id,
            cliente=cotizacion.cliente,
            proyecto=cotizacion.proyecto,
            total=total_factura,
            total_sin_iva=total_sin_iva,
            anticipo=anticipo_inicial,
            estado="PENDIENTE"
        )

        db.session.add(factura)
        db.session.flush()        # ⬅️ para obtener el ID

        cotizacion.factura = factura
        db.session.commit()

        flash("Factura creada correctamente ✅", "success")

    except Exception as e:
        db.session.rollback()
        print("⚠️ Error:", e)
        flash("Error al crear la factura", "danger")

    return redirect(request.referrer)


@facturas_bp.route("/")
@login_required
def ver_factura():
    facturas = Factura.query.order_by(Factura.id.desc()).all()
    return render_template("facturas.html", facturas=facturas)


@facturas_bp.route("/registrar-cuenta-cobro/<int:factura_id>", methods=["POST"])
@login_required
def registrar_cuenta_cobro(factura_id):
    factura = Factura.query.get_or_404(factura_id)

    try:
        cantidad_raw = request.form.get("cantidad")
        fecha_envio_str = request.form.get("fecha_envio")
        numero = request.form.get("numero_documento")
        archivo = request.files.get("archivo_soporte")

        if not cantidad_raw or not fecha_envio_str or not numero:
            flash("Todos los campos son obligatorios", "danger")
            return redirect(request.referrer)

        nombre_archivo = None
        if archivo and archivo.filename:
            from supabase_client import supabase
            import uuid
            
            ext = archivo.filename.rsplit(".", 1)[-1].lower()
            filename = f"facturas/{uuid.uuid4().hex}_{ext}"
            data = archivo.read()
            
            try:
                supabase.storage.from_("tesoreria").upload(
                    filename, data,
                    {"content-type": archivo.content_type, "upsert": "false"}
                )
                nombre_archivo = supabase.storage.from_("tesoreria").get_public_url(filename)
            except Exception as e:
                flash(f"Error al subir el archivo de soporte a la nube: {e}", "warning")

        nueva_acta = Actas(
            factura_id=factura.id,
            tipo_documento="CUENTA_COBRO",
            cantidad=Decimal(cantidad_raw),
            fecha_envio=datetime.strptime(
                fecha_envio_str, "%Y-%m-%d"
            ).date(),
            numero_documento=numero,
            archivo_soporte=nombre_archivo
        )

        db.session.add(nueva_acta)
        db.session.commit()

        flash("Cuenta de cobro registrada ✅", "success")

    except Exception as e:
        db.session.rollback()
        print("⚠️ Error:", e)
        flash("Error al registrar cuenta de cobro", "danger")

    return redirect(request.referrer)

@facturas_bp.route("/registrar-consignacion/<int:factura_id>", methods=["POST"])
@login_required
def registrar_consignacion(factura_id):
    factura = Factura.query.get_or_404(factura_id)

    try:
        valor_raw = request.form.get("valor_consignado")
        fecha_recepcion_str = request.form.get("fecha_recepcion")
        numero = request.form.get("numero_documento")
        archivo = request.files.get("archivo_soporte")

        if not valor_raw or not fecha_recepcion_str or not numero:
            flash("Todos los campos son obligatorios", "danger")
            return redirect(request.referrer)

        valor_consignado = Decimal(valor_raw)

        total_consignado = sum(
            a.valor_consignado or 0
            for a in factura.actas
            if a.tipo_documento == "FACTURA"
        )

        total_pagado = factura.anticipo + total_consignado + valor_consignado

        if total_pagado > factura.total:
            flash("El pago supera el total de la factura", "danger")
            return redirect(request.referrer)

        nombre_archivo = None
        if archivo and archivo.filename:
            from supabase_client import supabase
            import uuid
            
            ext = archivo.filename.rsplit(".", 1)[-1].lower()
            filename = f"facturas/{uuid.uuid4().hex}_{ext}"
            data = archivo.read()
            
            try:
                supabase.storage.from_("tesoreria").upload(
                    filename, data,
                    {"content-type": archivo.content_type, "upsert": "false"}
                )
                nombre_archivo = supabase.storage.from_("tesoreria").get_public_url(filename)
            except Exception as e:
                flash(f"Error al subir el archivo de soporte a la nube: {e}", "warning")

        nueva_acta = Actas(
            factura_id=factura.id,
            cuenta_cobro_id = request.form.get("cuenta_cobro_id"),
            tipo_documento="FACTURA",
            valor_consignado=valor_consignado,
            fecha_recepcion=datetime.strptime(
                fecha_recepcion_str, "%Y-%m-%d"
            ).date(),
            numero_documento=numero,
            archivo_soporte=nombre_archivo
        )

        db.session.add(nueva_acta)

        if total_pagado >= factura.total:
            factura.estado = "FACTURADO"
        else:
            factura.estado = "EN_PROCESO"

        db.session.commit()

        flash("Consignación registrada correctamente ✅", "success")

    except Exception as e:
        db.session.rollback()
        print("⚠️ Error:", e)
        flash("Error al registrar consignación", "danger")

    return redirect(request.referrer)


