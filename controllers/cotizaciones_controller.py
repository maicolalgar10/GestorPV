from datetime import datetime
import os
from flask import Blueprint, request, redirect, url_for, flash
from decorators import login_required
from models import db, Cotizacion, Factura, Usuarios, Notificaciones
from werkzeug.utils import secure_filename

cotizaciones_bp = Blueprint("cotizaciones", __name__)

UPLOAD_FOLDER = "static/uploads/cotizaciones"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ================================
# Crear cotización
# ================================
@cotizaciones_bp.route("/cotizaciones", methods=["POST"])
@login_required
def crear_cotizacion():
    try:
        cliente = request.form.get("cliente")
        proyecto = request.form.get("proyecto")
        numero_cotizacion = request.form.get("numero_cotizacion")
        imagen = request.files.get("imagen_cotizacion")

        if not cliente or not proyecto or not numero_cotizacion:
            flash("Cliente, proyecto y número de cotización son obligatorios", "warning")
            return redirect(url_for("dashboard.dashboard_oficina"))

        ruta_imagen = None
        if imagen and imagen.filename:
            filename = secure_filename(imagen.filename)
            ruta_imagen = os.path.join(UPLOAD_FOLDER, filename)
            imagen.save(ruta_imagen)
            ruta_imagen = filename

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
def cambiar_estado_cotizacion(id, estado):
    cotizacion = Cotizacion.query.get_or_404(id)

    if estado not in ["ACEPTADA", "RECHAZADA"]:
        flash("Estado no válido", "danger")
        return redirect(url_for("dashboard.dashboard_oficina"))

    # 🔒 Bloquear si ya fue facturada
    existe_factura = Factura.query.filter_by(cotizacion_id=cotizacion.id).first()
    if existe_factura:
        flash("Esta cotización ya fue facturada", "warning")
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
def eliminar_cotizacion(id):
    cotizacion = Cotizacion.query.get_or_404(id)

    try:
        # 🔒 Buscar factura asociada por cotizacion_id
        factura = Factura.query.filter_by(cotizacion_id=cotizacion.id).first()
        if factura:
            db.session.delete(factura)

        # 🖼️ borrar imagen si existe
        if cotizacion.imagen_cotizacion:
            path_imagen = os.path.join(UPLOAD_FOLDER, cotizacion.imagen_cotizacion)
            if os.path.exists(path_imagen):
                os.remove(path_imagen)

        # 📄 borrar cotización
        db.session.delete(cotizacion)
        db.session.commit()

        flash("Cotización y factura eliminadas correctamente ✅", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"Error al eliminar cotización: {str(e)}", "danger")

    return redirect(url_for("dashboard.dashboard_oficina"))


