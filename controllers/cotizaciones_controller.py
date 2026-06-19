from datetime import datetime
import os
from flask import Blueprint, request, redirect, url_for, flash
from decorators import login_required, admin_oficina_required
from models import db, Cotizacion, Contrato, Usuarios, Notificaciones
from werkzeug.utils import secure_filename
from supabase_client import supabase
import uuid

cotizaciones_bp = Blueprint("cotizaciones", __name__)


# ================================
# Crear cotización
# ================================
@cotizaciones_bp.route("/cotizaciones", methods=["POST"])
@login_required
@admin_oficina_required
def crear_cotizacion():
    try:
        cliente = request.form.get("cliente")
        proyecto = request.form.get("proyecto")
        numero_cotizacion = request.form.get("numero_cotizacion")
        archivos = request.files.getlist("archivos_cotizacion")

        if not cliente or not proyecto or not numero_cotizacion:
            flash("Cliente, proyecto y número de cotización son obligatorios", "warning")
            return redirect(url_for("dashboard.dashboard_oficina"))

        urls_subidas = []
        if supabase:
            for imagen in archivos:
                if imagen and imagen.filename:
                    original_filename = secure_filename(imagen.filename)
                    ext = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else 'jpg'
                    # Usar solo UUID y la extensión (estilo paranoico)
                    unique_filename = f"cotizacion_{uuid.uuid4().hex}.{ext}"
                    
                    try:
                        # Leer el archivo como bytes
                        file_bytes = imagen.read()
                        # Subir al bucket 'uploads' dentro de la carpeta 'cotizaciones'
                        supabase.storage.from_("uploads").upload(f"cotizaciones/{unique_filename}", file_bytes, {"content-type": imagen.content_type})
                        
                        # Obtener la URL pública
                        public_url = supabase.storage.from_("uploads").get_public_url(f"cotizaciones/{unique_filename}")
                        urls_subidas.append(public_url)
                    except Exception as e:
                        print("Error al subir archivo a Supabase:", e)
        else:
            if any(img.filename for img in archivos):
                flash("Supabase no está configurado. No se subieron las imágenes.", "warning")

        ruta_imagen = ",".join(urls_subidas) if urls_subidas else None

        cotizacion = Cotizacion(
            cliente=cliente,
            proyecto=proyecto,
            numero_cotizacion=numero_cotizacion,
            imagen_cotizacion=ruta_imagen,
            estado="PENDIENTE"
        )

        db.session.add(cotizacion)
        db.session.commit()

        flash("Cotización creada correctamente ✅", "success")
        return redirect(url_for("dashboard.dashboard_oficina"))

    except Exception as e:
        db.session.rollback()
        flash(f"Error al crear la cotización: {str(e)}", "danger")
        return redirect(url_for("dashboard.dashboard_oficina"))


@cotizaciones_bp.route("/cotizaciones/<int:id>/estado/<string:estado>", methods=["POST"])
@login_required
@admin_oficina_required
def cambiar_estado_cotizacion(id, estado):
    cotizacion = Cotizacion.query.get_or_404(id)

    if estado not in ["ACEPTADA", "RECHAZADA"]:
        flash("Estado no válido", "danger")
        return redirect(url_for("dashboard.dashboard_oficina"))

    # 🔒 Bloquear si ya fue facturada
    existe_contrato = Contrato.query.filter_by(cotizacion_id=cotizacion.id).first()
    if existe_contrato:
        flash("Esta cotización ya tiene un contrato asociado", "warning")
        return redirect(url_for("dashboard.dashboard_oficina"))

    cotizacion.estado = estado
    
    # ============================
    # 🔔 NOTIFICACIÓN AL ADMIN
    # ============================
    if estado == "ACEPTADA":
        admins = Usuarios.query.filter_by(rol="ADMIN").all()

        for admin in admins:
            notificacion = Notificaciones(
                id_usuario_destino=admin.id_usuario,
                mensaje=f"La cotización #{cotizacion.numero_cotizacion} fue ACEPTADA y está lista para facturar.",
                leido=False,
                creado_en=datetime.utcnow()
            )
            db.session.add(notificacion)
    
    db.session.commit()

    flash(f"Cotización {estado.lower()} correctamente ✅", "success")
    return redirect(url_for("dashboard.dashboard_oficina"))


@cotizaciones_bp.route("/cotizaciones/<int:id>/eliminar", methods=["POST"])
@login_required
@admin_oficina_required
def eliminar_cotizacion(id):
    cotizacion = Cotizacion.query.get_or_404(id)

    try:
        # 🔒 Buscar contrato asociado por cotizacion_id
        contrato = Contrato.query.filter_by(cotizacion_id=cotizacion.id).first()
        if contrato:
            db.session.delete(contrato)

        # 🖼️ borrar imagenes si existen
        if cotizacion.imagen_cotizacion and supabase:
            urls = cotizacion.imagen_cotizacion.split(",")
            for url in urls:
                if "supabase.co" in url:
                    try:
                        # El path usualmente está después de '/public/uploads/'
                        path_part = url.split("/public/uploads/")[-1]
                        supabase.storage.from_("uploads").remove([path_part])
                    except Exception as e:
                        print("Error al borrar imagen en Supabase:", e)

        # 📄 borrar cotización
        db.session.delete(cotizacion)
        db.session.commit()

        flash("Cotización y contrato eliminados correctamente ✅", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"Error al eliminar cotización: {str(e)}", "danger")

    return redirect(url_for("dashboard.dashboard_oficina"))


