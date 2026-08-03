from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from decorators import login_required, admin_oficina_required
from models import db, Usuarios, Notificaciones
from frases import frase_del_dia
from datetime import datetime as dt
from supabase_client import supabase
import uuid

contratistas_bp = Blueprint("contratistas", __name__)

# ─── GET /contratistas ───────────────────────────
@contratistas_bp.route("/contratistas")
@login_required
@admin_oficina_required
def contratistas():
    from models import ContratistaFactura, Contratista
    usuario = Usuarios.query.get(session.get("user_id"))
    notificaciones = Notificaciones.query.filter_by(
        id_usuario_destino=session["user_id"], leido=False
    ).order_by(Notificaciones.creado_en.desc()).all()
    frase = frase_del_dia()

    # Obtener contratistas ordenados alfabéticamente
    lista_contratistas = Contratista.query.order_by(Contratista.nombre.asc()).all()
    
    # Obtener todas las facturas
    facturas = ContratistaFactura.query.order_by(ContratistaFactura.fecha_factura.desc()).all()

    # Agrupar facturas por contratista (usando nombre_contratista para el enlace)
    facturas_por_contratista = {c.nombre: [] for c in lista_contratistas}
    for f in facturas:
        if f.nombre_contratista in facturas_por_contratista:
            facturas_por_contratista[f.nombre_contratista].append(f)
        else:
            facturas_por_contratista[f.nombre_contratista] = [f]

    # Calcular totales por contratista para el acordeón
    totales_contratistas = {}
    for contratista in lista_contratistas:
        facturas_c = facturas_por_contratista.get(contratista.nombre, [])
        total_facturado = sum(float(f.valor_total) for f in facturas_c)
        total_rete_garantia = sum(float(f.retencion_pesos) for f in facturas_c)
        # Usamos retencion_pesos como rete garantia o algo asimilable si se quiere
        total_pagos = sum(float(f.valor_cancelado) for f in facturas_c)
        saldo_adeudado = sum(float(f.total_adeudado) for f in facturas_c)
        
        totales_contratistas[contratista.nombre] = {
            'total_facturado': total_facturado,
            'total_rete_garantia': total_rete_garantia,
            'total_retenciones_ley': 0.0, # Puede no aplicar a contratista
            'total_pagos': total_pagos,
            'saldo_adeudado': saldo_adeudado,
            'facturas': facturas_c
        }

    return render_template(
        "contratistas.html",
        usuario=usuario,
        notificaciones=notificaciones,
        frase=frase,
        frase_del_dia=frase,
        contratistas=lista_contratistas,
        totales_contratistas=totales_contratistas,
    )


# ─── POST /contratistas/crear_contratista ────────────────────
@contratistas_bp.route("/contratistas/crear_contratista", methods=["POST"])
@login_required
@admin_oficina_required
def crear_contratista():
    from models import Contratista
    try:
        nombre = request.form.get("nombre", "").strip()
        nit = request.form.get("nit", "").strip()
        telefono = request.form.get("telefono", "").strip()
        especialidad = request.form.get("especialidad", "").strip()
        estado = request.form.get("estado", "Activo")

        if not nombre:
            flash("El nombre/razón social es obligatorio.", "warning")
            return redirect(url_for("contratistas.contratistas"))

        existe = Contratista.query.filter(Contratista.nombre.ilike(nombre)).first()
        if existe:
            flash("Ya existe un contratista con ese nombre.", "warning")
            return redirect(url_for("contratistas.contratistas"))

        nuevo = Contratista(
            nombre=nombre, 
            nit=nit, 
            telefono=telefono,
            especialidad=especialidad,
            estado=estado
        )
        db.session.add(nuevo)
        db.session.commit()
        flash("Contratista registrado correctamente.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error al registrar contratista: {e}", "danger")

    return redirect(url_for("contratistas.contratistas"))


# ─── POST /contratistas/editar_contratista/<int:id> ────────────────────
@contratistas_bp.route("/contratistas/editar_contratista/<int:id>", methods=["POST"])
@login_required
@admin_oficina_required
def editar_contratista(id):
    from models import Contratista
    try:
        contratista = Contratista.query.get(id)
        if not contratista:
            flash('Contratista no encontrado.', 'danger')
            return redirect(url_for('contratistas.contratistas'))

        contratista.nombre = request.form.get("nombre", "").strip()
        contratista.nit = request.form.get("nit", "").strip()
        contratista.telefono = request.form.get("telefono", "").strip()
        contratista.especialidad = request.form.get("especialidad", "").strip()
        contratista.estado = request.form.get("estado", "Activo")

        db.session.commit()
        flash('Contratista actualizado exitosamente.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al actualizar contratista: {e}', 'danger')

    return redirect(url_for("contratistas.contratistas"))


# ─── POST /contratistas/crear_factura ────────────────────
@contratistas_bp.route("/contratistas/crear_factura", methods=["POST"])
@login_required
@admin_oficina_required
def crear_factura():
    from models import ContratistaFactura

    def upload_file(file_field):
        f = request.files.get(file_field)
        if not f or f.filename == "":
            return None
        if supabase is None:
            return None
        try:
            ext = f.filename.rsplit(".", 1)[-1].lower()
            filename = f"{uuid.uuid4().hex}.{ext}"
            path = f"contratistas/{filename}"
            data = f.read()
            supabase.storage.from_("tesoreria").upload(
                path, data,
                {"content-type": f.content_type, "upsert": "false"}
            )
            return supabase.storage.from_("tesoreria").get_public_url(path)
        except Exception as e:
            print(f"Error subiendo archivo: {e}")
            return None

    try:
        fecha_factura     = dt.strptime(request.form["fecha_factura"], "%Y-%m-%d").date()
        fecha_vencimiento = dt.strptime(request.form["fecha_vencimiento"], "%Y-%m-%d").date()
        fecha_pago_raw    = request.form.get("fecha_pago", "").strip()
        fecha_pago        = dt.strptime(fecha_pago_raw, "%Y-%m-%d").date() if fecha_pago_raw else None

        def parse_float_safe(value, default=0.0):
            try:
                if value is None or str(value).strip() == "": return default
                return float(value)
            except (ValueError, TypeError):
                return default

        factura = ContratistaFactura(
            nombre_contratista       = request.form["nombre_contratista"].strip(),
            fecha_factura          = fecha_factura,
            plazo_dias             = int(request.form.get("plazo_dias") or 0),
            fecha_vencimiento      = fecha_vencimiento,
            valor_neto             = parse_float_safe(request.form.get("valor_neto")),
            porcentaje_iva         = parse_float_safe(request.form.get("porcentaje_iva"), 19.0),
            valor_cancelado        = parse_float_safe(request.form.get("valor_cancelado")),
            retencion              = parse_float_safe(request.form.get("retencion")),
            fecha_pago             = fecha_pago,
            orden_compra_url       = upload_file("orden_compra_pdf"),
            comprobante_compra_url = upload_file("factura_pdf"),
            banco_pago_url         = upload_file("comprobante_pago"),
        )
        db.session.add(factura)
        db.session.commit()
        flash("Factura/Reporte registrada correctamente.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error al registrar la factura: {e}", "danger")

    return redirect(url_for("contratistas.contratistas"))


# ─── POST /contratistas/editar_factura/<int:id> ──────────────
@contratistas_bp.route("/contratistas/editar_factura/<int:id>", methods=["POST"])
@login_required
@admin_oficina_required
def editar_factura(id):
    from models import ContratistaFactura

    factura = ContratistaFactura.query.get_or_404(id)

    def upload_or_keep(file_field, current_url):
        f = request.files.get(file_field)
        if not f or f.filename == "":
            return current_url
        if supabase is None:
            return current_url
        try:
            ext = f.filename.rsplit(".", 1)[-1].lower()
            filename = f"{uuid.uuid4().hex}.{ext}"
            path = f"contratistas/{filename}"
            data = f.read()
            supabase.storage.from_("tesoreria").upload(
                path, data,
                {"content-type": f.content_type, "upsert": "false"}
            )
            return supabase.storage.from_("tesoreria").get_public_url(path)
        except Exception as e:
            print(f"Error subiendo archivo: {e}")
            return current_url

    try:
        def parse_float_safe(value, default=0.0):
            try:
                if value is None or str(value).strip() == "": return default
                return float(value)
            except (ValueError, TypeError):
                return default

        fecha_pago_raw = request.form.get("fecha_pago", "").strip()
        if "nombre_contratista" in request.form:
            factura.nombre_contratista       = request.form["nombre_contratista"].strip()
            
        factura.fecha_factura          = dt.strptime(request.form["fecha_factura"], "%Y-%m-%d").date()
        factura.plazo_dias             = int(request.form.get("plazo_dias") or 0)
        
        # Fecha vencimiento podría venir vacía si hay un script, pero si es requerida:
        if request.form.get("fecha_vencimiento"):
            factura.fecha_vencimiento      = dt.strptime(request.form["fecha_vencimiento"], "%Y-%m-%d").date()
            
        factura.valor_neto             = parse_float_safe(request.form.get("valor_neto"))
        factura.porcentaje_iva         = parse_float_safe(request.form.get("porcentaje_iva"), 19.0)
        factura.valor_cancelado        = parse_float_safe(request.form.get("valor_cancelado"))
        factura.retencion              = parse_float_safe(request.form.get("retencion"))
        factura.fecha_pago             = dt.strptime(fecha_pago_raw, "%Y-%m-%d").date() if fecha_pago_raw else None
        
        factura.orden_compra_url = upload_or_keep("orden_compra_pdf", factura.orden_compra_url)
        factura.comprobante_compra_url = upload_or_keep("factura_pdf", factura.comprobante_compra_url)
        factura.banco_pago_url = upload_or_keep("comprobante_pago", factura.banco_pago_url)

        db.session.commit()
        flash("Factura actualizada correctamente.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error al actualizar: {e}", "danger")

    return redirect(url_for("contratistas.contratistas"))


# ─── POST /contratistas/<id>/eliminar ────────────
@contratistas_bp.route("/contratistas/eliminar_factura/<int:id>", methods=["POST"])
@login_required
@admin_oficina_required
def eliminar_factura(id):
    from models import ContratistaFactura
    factura = ContratistaFactura.query.get_or_404(id)
    try:
        db.session.delete(factura)
        db.session.commit()
        flash("Factura eliminada correctamente.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error al eliminar: {e}", "danger")
    return redirect(url_for("contratistas.contratistas"))
