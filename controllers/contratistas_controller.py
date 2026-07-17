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

    facturas = ContratistaFactura.query.order_by(ContratistaFactura.fecha_factura.desc()).all()
    lista_contratistas = Contratista.query.order_by(Contratista.nombre.asc()).all()

    deuda_por_contratista = {}
    for factura in facturas:
        nombre = factura.nombre_contratista
        deuda_por_contratista[nombre] = deuda_por_contratista.get(nombre, 0) + float(factura.total_adeudado)

    # Totales globales (usan los @property del modelo)
    total_valor_neto      = sum(float(f.valor_neto or 0) for f in facturas)
    total_iva             = sum(f.iva for f in facturas)
    total_valor_total     = sum(f.valor_total for f in facturas)
    total_retencion       = sum(f.retencion_pesos for f in facturas)
    total_cancelado       = sum(float(f.valor_cancelado or 0) for f in facturas)
    total_adeudado_global = sum(deuda_por_contratista.values())

    return render_template(
        "contratistas.html",
        usuario=usuario,
        notificaciones=notificaciones,
        frase=frase,
        frase_del_dia=frase,
        facturas=facturas,
        total_valor_neto=total_valor_neto,
        total_iva=total_iva,
        total_valor_total=total_valor_total,
        total_retencion=total_retencion,
        total_cancelado=total_cancelado,
        total_adeudado_global=total_adeudado_global,
        contratistas=lista_contratistas,
        deuda_por_contratista=deuda_por_contratista,
    )

# ─── GET /contratistas/<nombre_contratista> ────────
@contratistas_bp.route("/contratistas/<string:nombre_contratista>")
@login_required
@admin_oficina_required
def facturas_contratista(nombre_contratista):
    from models import ContratistaFactura
    usuario = Usuarios.query.get(session.get("user_id"))
    notificaciones = Notificaciones.query.filter_by(
        id_usuario_destino=session["user_id"], leido=False
    ).order_by(Notificaciones.creado_en.desc()).all()
    frase = frase_del_dia()

    facturas = ContratistaFactura.query.filter_by(nombre_contratista=nombre_contratista).order_by(ContratistaFactura.fecha_factura.desc()).all()
    
    deuda_total = sum(f.total_adeudado for f in facturas)

    return render_template(
        "facturas_contratista.html",
        usuario=usuario,
        notificaciones=notificaciones,
        frase=frase,
        frase_del_dia=frase,
        facturas=facturas,
        nombre_contratista=nombre_contratista,
        deuda_total=deuda_total
    )

# ─── POST /contratistas/crear ────────────────────
@contratistas_bp.route("/contratistas/crear", methods=["POST"])
@login_required
@admin_oficina_required
def crear_contratista():
    from models import Contratista
    try:
        nombre = request.form.get("nombre", "").strip()
        nit = request.form.get("nit", "").strip()
        telefono = request.form.get("telefono", "").strip()

        if not nombre:
            flash("El nombre del contratista es obligatorio.", "warning")
            return redirect(url_for("contratistas.contratistas"))

        existe = Contratista.query.filter(Contratista.nombre.ilike(nombre)).first()
        if existe:
            flash("Ya existe un contratista con ese nombre.", "warning")
            return redirect(url_for("contratistas.contratistas"))

        nuevo = Contratista(nombre=nombre, nit=nit, telefono=telefono)
        db.session.add(nuevo)
        db.session.commit()
        flash("Contratista registrado correctamente.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error al registrar contratista: {e}", "danger")

    return redirect(url_for("contratistas.contratistas"))

# ─── POST /contratistas/nueva ────────────────────
@contratistas_bp.route("/contratistas/nueva", methods=["POST"])
@login_required
@admin_oficina_required
def nueva_factura_contratista():
    from models import ContratistaFactura

    def upload_file(file_field):
        f = request.files.get(file_field)
        if not f or f.filename == "":
            return None
        if supabase is None:
            flash("Supabase no configurado. Archivo no subido.", "warning")
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
            flash(f"Error subiendo archivo: {e}", "warning")
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
            orden_compra_url       = upload_file("orden_compra"),
            comprobante_compra_url = upload_file("comprobante_compra"),
            banco_pago_url         = upload_file("banco_pago"),
        )
        db.session.add(factura)
        db.session.commit()
        flash("Factura de contratista registrada correctamente.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error al registrar la factura: {e}", "danger")

    return redirect(url_for("contratistas.contratistas"))

# ─── POST /contratistas/<id>/editar ──────────────
@contratistas_bp.route("/contratistas/<int:id>/editar", methods=["POST"])
@login_required
@admin_oficina_required
def editar_factura_contratista(id):
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
            flash(f"Error subiendo archivo: {e}", "warning")
            return current_url

    try:
        def parse_float_safe(value, default=0.0):
            try:
                if value is None or str(value).strip() == "": return default
                return float(value)
            except (ValueError, TypeError):
                return default

        fecha_pago_raw = request.form.get("fecha_pago", "").strip()
        factura.nombre_contratista       = request.form["nombre_contratista"].strip()
        factura.fecha_factura          = dt.strptime(request.form["fecha_factura"], "%Y-%m-%d").date()
        factura.plazo_dias             = int(request.form.get("plazo_dias") or 0)
        factura.fecha_vencimiento      = dt.strptime(request.form["fecha_vencimiento"], "%Y-%m-%d").date()
        factura.valor_neto             = parse_float_safe(request.form.get("valor_neto"))
        factura.porcentaje_iva         = parse_float_safe(request.form.get("porcentaje_iva"), 19.0)
        factura.valor_cancelado        = parse_float_safe(request.form.get("valor_cancelado"))
        factura.retencion              = parse_float_safe(request.form.get("retencion"))
        factura.fecha_pago             = dt.strptime(fecha_pago_raw, "%Y-%m-%d").date() if fecha_pago_raw else None
        
        if request.form.get("eliminar_orden") == "true":
            factura.orden_compra_url = None
        else:
            factura.orden_compra_url = upload_or_keep("orden_compra", factura.orden_compra_url)
            
        if request.form.get("eliminar_comprobante") == "true":
            factura.comprobante_compra_url = None
        else:
            factura.comprobante_compra_url = upload_or_keep("comprobante_compra", factura.comprobante_compra_url)
            
        if request.form.get("eliminar_soporte") == "true":
            factura.banco_pago_url = None
        else:
            factura.banco_pago_url = upload_or_keep("banco_pago", factura.banco_pago_url)

        db.session.commit()
        flash("Factura actualizada correctamente.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error al actualizar: {e}", "danger")

    return redirect(url_for("contratistas.contratistas"))

# ─── POST /contratistas/<id>/eliminar ────────────
@contratistas_bp.route("/contratistas/<int:id>/eliminar", methods=["POST"])
@login_required
@admin_oficina_required
def eliminar_factura_contratista(id):
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
