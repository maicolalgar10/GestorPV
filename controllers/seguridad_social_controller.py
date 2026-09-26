from helpers import clean_amount
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models import db, PlanillaSeguridadSocial, TipoPlanillaSeguridadSocial, Usuarios, Notificaciones
from decorators import login_required, admin_oficina_required
from datetime import datetime as dt
from supabase_client import supabase
import uuid

seguridad_social_bp = Blueprint("seguridad_social", __name__, url_prefix="/seguridad_social")

@seguridad_social_bp.route("/")
@login_required
@admin_oficina_required
def index():
    usuario = Usuarios.query.get(session.get("user_id"))
    notificaciones = Notificaciones.query.filter_by(
        id_usuario_destino=session["user_id"], leido=False
    ).order_by(Notificaciones.creado_en.desc()).all()
    
    order = request.args.get('order', 'desc')
    sort_by = request.args.get('sort_by', 'fecha_pago')
    
    if sort_by == 'vencimiento':
        order_col = PlanillaSeguridadSocial.fecha_vencimiento
    else:
        order_col = db.func.coalesce(PlanillaSeguridadSocial.fecha_pago, PlanillaSeguridadSocial.fecha_vencimiento)

    if order == 'asc':
        planillas = PlanillaSeguridadSocial.query.order_by(order_col.asc()).all()
    else:
        planillas = PlanillaSeguridadSocial.query.order_by(order_col.desc()).all()
        
    entidades = TipoPlanillaSeguridadSocial.query.order_by(TipoPlanillaSeguridadSocial.nombre.asc()).all()
        
    total_valor = sum(p.valor for p in planillas if p.valor)
    
    return render_template("seguridad_social.html", usuario=usuario, notificaciones=notificaciones, planillas=planillas, entidades=entidades, total_valor=total_valor, current_order=order, current_sort=sort_by)

@seguridad_social_bp.route("/crear_entidad", methods=["POST"])
@login_required
@admin_oficina_required
def crear_entidad():
    nombre = request.form.get("nombre", "").strip()
    if nombre:
        nueva_entidad = TipoPlanillaSeguridadSocial(nombre=nombre)
        try:
            db.session.add(nueva_entidad)
            db.session.commit()
            flash("Entidad registrada correctamente.", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Error al registrar entidad: {e}", "danger")
    return redirect(url_for("seguridad_social.index"))

@seguridad_social_bp.route("/crear", methods=["POST"])
@login_required
@admin_oficina_required
def crear():
    def upload_file(file_field):
        f = request.files.get(file_field)
        if not f or f.filename == "":
            return None
        if supabase is None:
            return None
        try:
            ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'webp'}
            ext = f.filename.rsplit(".", 1)[-1].lower()
            if ext not in ALLOWED_EXTENSIONS:
                flash(f"Extensión .{ext} no permitida. Solo PDF e imágenes.", "danger")
                return None
            filename = f"{uuid.uuid4().hex}.{ext}"
            path = f"seguridad_social/{filename}"
            data = f.read()
            supabase.storage.from_("tesoreria").upload(
                path, data,
                {"content-type": f.content_type, "upsert": "false"}
            )
            return supabase.storage.from_("tesoreria").get_public_url(path)
        except Exception as e:
            return None

    try:
        concepto = request.form.get("concepto", "").strip()
        valor_raw = clean_amount(request.form.get("valor"))
        valor_limpio = str(valor_raw).replace('$', '').replace(' ', '')
        if ',' in valor_limpio and '.' in valor_limpio:
            valor_limpio = valor_limpio.replace('.', '').replace(',', '.')
        elif ',' in valor_limpio:
            valor_limpio = valor_limpio.replace(',', '.')
        elif '.' in valor_limpio:
            partes = valor_limpio.split('.')
            if len(partes[-1]) == 3:
                valor_limpio = valor_limpio.replace('.', '')
        
        valor = float(valor_limpio) if valor_limpio else 0.0
        
        estado_pago = request.form.get("estado_pago", "").strip()
        tipo_planilla_id = request.form.get("tipo_planilla_id")

        fecha_pago_raw = request.form.get("fecha_pago", "").strip()
        fecha_pago = dt.strptime(fecha_pago_raw, "%Y-%m-%d").date() if fecha_pago_raw else None
        
        fecha_vencimiento_raw = request.form.get("fecha_vencimiento", "").strip()
        fecha_vencimiento = dt.strptime(fecha_vencimiento_raw, "%Y-%m-%d").date() if fecha_vencimiento_raw else None
        
        soporte_declaracion_url = upload_file("soporte_declaracion")
        soporte_pago_url = upload_file("soporte_pago")

        nueva_planilla = PlanillaSeguridadSocial(
            concepto=concepto,
            valor=valor,
            estado_pago=estado_pago,
            fecha_pago=fecha_pago,
            fecha_vencimiento=fecha_vencimiento,
            tipo_planilla_id=tipo_planilla_id,
            soporte_declaracion_url=soporte_declaracion_url,
            soporte_pago_url=soporte_pago_url
        )
        
        db.session.add(nueva_planilla)
        db.session.commit()
        flash("Planilla de Seguridad Social registrada correctamente.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error al registrar: {e}", "danger")
        
    return redirect(url_for("seguridad_social.index"))

@seguridad_social_bp.route("/editar/<int:id>", methods=["POST"])
@login_required
@admin_oficina_required
def editar(id):
    planilla = PlanillaSeguridadSocial.query.get_or_404(id)
    
    def upload_or_keep(file_field, current_url):
        f = request.files.get(file_field)
        if not f or f.filename == "":
            return current_url
        if supabase is None:
            return current_url
        try:
            ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'webp'}
            ext = f.filename.rsplit(".", 1)[-1].lower()
            if ext not in ALLOWED_EXTENSIONS:
                flash(f"Extensión .{ext} no permitida. Solo PDF e imágenes.", "danger")
                return current_url
            filename = f"{uuid.uuid4().hex}.{ext}"
            path = f"seguridad_social/{filename}"
            data = f.read()
            supabase.storage.from_("tesoreria").upload(
                path, data,
                {"content-type": f.content_type, "upsert": "false"}
            )
            return supabase.storage.from_("tesoreria").get_public_url(path)
        except Exception as e:
            return current_url

    try:
        planilla.concepto = request.form.get("concepto", "").strip()
        
        valor_raw = clean_amount(request.form.get("valor"))
        valor_limpio = str(valor_raw).replace('$', '').replace(' ', '')
        if ',' in valor_limpio and '.' in valor_limpio:
            valor_limpio = valor_limpio.replace('.', '').replace(',', '.')
        elif ',' in valor_limpio:
            valor_limpio = valor_limpio.replace(',', '.')
        elif '.' in valor_limpio:
            partes = valor_limpio.split('.')
            if len(partes[-1]) == 3:
                valor_limpio = valor_limpio.replace('.', '')
        planilla.valor = float(valor_limpio) if valor_limpio else 0.0
        
        planilla.estado_pago = request.form.get("estado_pago", "").strip()
        planilla.tipo_planilla_id = request.form.get("tipo_planilla_id")

        fecha_pago_raw = request.form.get("fecha_pago", "").strip()
        planilla.fecha_pago = dt.strptime(fecha_pago_raw, "%Y-%m-%d").date() if fecha_pago_raw else None
        
        fecha_vencimiento_raw = request.form.get("fecha_vencimiento", "").strip()
        planilla.fecha_vencimiento = dt.strptime(fecha_vencimiento_raw, "%Y-%m-%d").date() if fecha_vencimiento_raw else None
        
        if request.form.get("eliminar_soporte_declaracion") == "true":
            planilla.soporte_declaracion_url = None
        else:
            planilla.soporte_declaracion_url = upload_or_keep("soporte_declaracion", planilla.soporte_declaracion_url)
            
        if request.form.get("eliminar_soporte_pago") == "true":
            planilla.soporte_pago_url = None
        else:
            planilla.soporte_pago_url = upload_or_keep("soporte_pago", planilla.soporte_pago_url)

        db.session.commit()
        flash("Registro editado correctamente.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error al editar: {e}", "danger")
        
    return redirect(url_for("seguridad_social.index"))

@seguridad_social_bp.route("/eliminar/<int:id>", methods=["POST"])
@login_required
@admin_oficina_required
def eliminar(id):
    planilla = PlanillaSeguridadSocial.query.get_or_404(id)
    try:
        db.session.delete(planilla)
        db.session.commit()
        flash("Registro eliminado correctamente.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error al eliminar: {e}", "danger")
    return redirect(url_for("seguridad_social.index"))

@seguridad_social_bp.route("/eliminar_entidad/<int:id>", methods=["POST"])
@login_required
@admin_oficina_required
def eliminar_entidad(id):
    entidad = TipoPlanillaSeguridadSocial.query.get_or_404(id)
    
    # Check if there are planillas associated with this entity
    if entidad.planillas:
        flash("No se puede eliminar la entidad porque tiene planillas asociadas. Elimine las planillas primero o asigne otra entidad.", "warning")
        return redirect(url_for("seguridad_social.index"))
        
    try:
        db.session.delete(entidad)
        db.session.commit()
        flash("Entidad eliminada correctamente.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error al eliminar entidad: {e}", "danger")
        
    return redirect(url_for("seguridad_social.index"))

