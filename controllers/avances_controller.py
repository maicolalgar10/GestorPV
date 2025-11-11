from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models import db, Actividades, Avances, Proyectos, ProyectoPersonal, Evidencias
from datetime import datetime
import os, base64
from werkzeug.utils import secure_filename
from frases import obtener_frase
# Carpeta donde se guardarán las imágenes
UPLOAD_FOLDER = "static/uploads/evidencias"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

avances_bp = Blueprint("avances", __name__)


# ===============================================================
# ➕ REGISTRAR AVANCE DE UNA ACTIVIDAD (trabajador)
# ===============================================================
@avances_bp.route("/registrar/<int:id_actividad>", methods=["POST"])
def registrar_avance(id_actividad):
    flash(obtener_frase("avance"), "success")
    id_usuario = session.get("user_id")
    if not id_usuario:
        flash("⚠️ Debes iniciar sesión para enviar avances.", "warning")
        return redirect(url_for("auth.login"))

    try:
        unidades = int(request.form["unidades_avanzadas"])
        fecha = datetime.strptime(request.form["fecha"], "%Y-%m-%d").date()
        mensaje = request.form.get("mensaje", "")

        # Crear el avance
        nuevo_avance = Avances(
            id_actividad=id_actividad,
            id_usuario=id_usuario,
            fecha=fecha,
            unidades_avanzadas=unidades,
            mensaje=mensaje,
        )
        db.session.add(nuevo_avance)
        db.session.commit()

        # ✅ Guardar evidencias (archivos o fotos tomadas)
        files = request.files.getlist("evidencias")

        # 1️⃣ Archivos subidos desde galería
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                ruta_relativa = os.path.join("uploads", "evidencias", filename)
                ruta_completa = os.path.join("static", ruta_relativa)
                os.makedirs(os.path.dirname(ruta_completa), exist_ok=True)
                file.save(ruta_completa)

                evidencia = Evidencias(
                    id_avance=nuevo_avance.id_avance,
                    ruta_archivo=ruta_relativa,
                    tipo="imagen"
                )
                db.session.add(evidencia)

        # 2️⃣ Imagen tomada con cámara (base64)
        imagen_capturada = request.form.get("captura_base64")
        if imagen_capturada:
            img_data = base64.b64decode(imagen_capturada.split(",")[1])
            filename = f"captura_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            ruta_relativa = os.path.join("uploads", "evidencias", filename)
            ruta_completa = os.path.join("static", ruta_relativa)
            os.makedirs(os.path.dirname(ruta_completa), exist_ok=True)
            with open(ruta_completa, "wb") as f:
                f.write(img_data)

            evidencia = Evidencias(
                id_avance=nuevo_avance.id_avance,
                ruta_archivo=ruta_relativa,
                tipo="imagen"
            )
            db.session.add(evidencia)

        # ✅ RECALCULAR EL PROGRESO DE LA ACTIVIDAD
        actividad = Actividades.query.get(id_actividad)
        total = actividad.unidades_totales or 0
        avanzado = (
            db.session.query(db.func.sum(Avances.unidades_avanzadas))
            .filter_by(id_actividad=id_actividad)
            .scalar()
        ) or 0
        
        # Guardar el progreso calculado en la sesión (para usarlo en el dashboard)
        session[f'avance_{id_actividad}'] = {
            'avanzado': avanzado,
            'porcentaje': int((avanzado / total) * 100) if total > 0 else 0
        }

        db.session.commit()
        flash("✅ Avance y evidencias registradas correctamente.", "success")

    except Exception as e:
        db.session.rollback()
        print("❌ Error al registrar avance:", e)
        flash("❌ Error al registrar avance o subir evidencias.", "danger")

    return redirect(url_for("dashboard.dashboard_trabajador"))
# ===============================================================
# 📋 INFORME DE AVANCE DE UN PROYECTO
# ===============================================================
@avances_bp.route("/informe/<int:id_proyecto>")
def ver_informe_avance(id_proyecto):
    id_usuario = session.get("user_id")
    if not id_usuario:
        flash("⚠️ Debes iniciar sesión para ver el informe.", "warning")
        return redirect(url_for("auth.login"))

    proyecto = Proyectos.query.get_or_404(id_proyecto)

    avances = (
        db.session.query(Avances, Actividades)
        .join(Actividades, Actividades.id_actividad == Avances.id_actividad)
        .filter(Actividades.id_proyecto == id_proyecto)
        .order_by(Avances.fecha.desc())
        .all()
    )

    return render_template(
        "/informe_avance.html",
        proyecto=proyecto,
        avances=avances
    )
