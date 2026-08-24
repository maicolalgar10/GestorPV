from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models import db, DianFactura, Usuarios, Notificaciones
from decorators import login_required, admin_oficina_required
from datetime import datetime as dt
from supabase_client import supabase
import uuid

dian_bp = Blueprint("dian", __name__, url_prefix="/dian")

@dian_bp.route("/")
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
        order_col = DianFactura.fecha_vencimiento
    else:
        order_col = db.func.coalesce(DianFactura.fecha_pago, DianFactura.fecha_vencimiento)

    if order == 'asc':
        facturas = DianFactura.query.order_by(order_col.asc()).all()
    else:
        facturas = DianFactura.query.order_by(order_col.desc()).all()
        
    total_valor = sum(f.valor for f in facturas if f.valor)
    
    return render_template("dian.html", usuario=usuario, notificaciones=notificaciones, facturas=facturas, total_valor=total_valor, current_order=order, current_sort=sort_by)

@dian_bp.route("/crear", methods=["POST"])
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
            path = f"dian/{filename}"
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
        valor_raw = request.form.get("valor", "0")
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
        
        pago = request.form.get("pago", "").strip()
        tipo_impuesto = request.form.get("tipo_impuesto", "").strip()

        fecha_pago_raw = request.form.get("fecha_pago", "").strip()
        fecha_pago = dt.strptime(fecha_pago_raw, "%Y-%m-%d").date() if fecha_pago_raw else None
        
        fecha_vencimiento_raw = request.form.get("fecha_vencimiento", "").strip()
        fecha_vencimiento = dt.strptime(fecha_vencimiento_raw, "%Y-%m-%d").date() if fecha_vencimiento_raw else None
        
        archivo_url = upload_file("archivo")
        recibo_pago_url = upload_file("recibo_pago")

        nueva_factura = DianFactura(
            concepto=concepto,
            valor=valor,
            pago=pago,
            fecha_pago=fecha_pago,
            fecha_vencimiento=fecha_vencimiento,
            tipo_impuesto=tipo_impuesto,
            archivo_url=archivo_url,
            recibo_pago_url=recibo_pago_url
        )
        
        db.session.add(nueva_factura)
        db.session.commit()
        flash("Factura/Impuesto DIAN registrado correctamente.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error al registrar: {e}", "danger")
        
    return redirect(url_for("dian.index"))

@dian_bp.route("/editar/<int:id>", methods=["POST"])
@login_required
@admin_oficina_required
def editar(id):
    factura = DianFactura.query.get_or_404(id)
    
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
            path = f"dian/{filename}"
            data = f.read()
            supabase.storage.from_("tesoreria").upload(
                path, data,
                {"content-type": f.content_type, "upsert": "false"}
            )
            return supabase.storage.from_("tesoreria").get_public_url(path)
        except Exception as e:
            return current_url

    try:
        factura.concepto = request.form.get("concepto", "").strip()
        
        valor_raw = request.form.get("valor", "0")
        valor_limpio = str(valor_raw).replace('$', '').replace(' ', '')
        if ',' in valor_limpio and '.' in valor_limpio:
            valor_limpio = valor_limpio.replace('.', '').replace(',', '.')
        elif ',' in valor_limpio:
            valor_limpio = valor_limpio.replace(',', '.')
        elif '.' in valor_limpio:
            partes = valor_limpio.split('.')
            if len(partes[-1]) == 3:
                valor_limpio = valor_limpio.replace('.', '')
        factura.valor = float(valor_limpio) if valor_limpio else 0.0
        
        factura.pago = request.form.get("pago", "").strip()
        factura.tipo_impuesto = request.form.get("tipo_impuesto", "").strip()

        fecha_pago_raw = request.form.get("fecha_pago", "").strip()
        factura.fecha_pago = dt.strptime(fecha_pago_raw, "%Y-%m-%d").date() if fecha_pago_raw else None
        
        fecha_vencimiento_raw = request.form.get("fecha_vencimiento", "").strip()
        factura.fecha_vencimiento = dt.strptime(fecha_vencimiento_raw, "%Y-%m-%d").date() if fecha_vencimiento_raw else None
        
        if request.form.get("eliminar_archivo") == "true":
            factura.archivo_url = None
        else:
            factura.archivo_url = upload_or_keep("archivo", factura.archivo_url)
            
        if request.form.get("eliminar_recibo_pago") == "true":
            factura.recibo_pago_url = None
        else:
            factura.recibo_pago_url = upload_or_keep("recibo_pago", factura.recibo_pago_url)

        db.session.commit()
        flash("Registro editado correctamente.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error al editar: {e}", "danger")
        
    return redirect(url_for("dian.index"))

@dian_bp.route("/eliminar/<int:id>", methods=["POST"])
@login_required
@admin_oficina_required
def eliminar(id):
    factura = DianFactura.query.get_or_404(id)
    try:
        db.session.delete(factura)
        db.session.commit()
        flash("Registro eliminado correctamente.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error al eliminar: {e}", "danger")
    return redirect(url_for("dian.index"))
