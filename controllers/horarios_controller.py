from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import db, Horario, Personal, Proyectos, ProyectoPersonal, Notificaciones
from datetime import datetime, date

horarios_bp = Blueprint("horarios", __name__)

# ================================
# 📋 LISTAR HORARIOS
# ================================
@horarios_bp.route("/horarios")
def listar_horarios():
    horarios = Horario.query.order_by(Horario.fecha.desc()).all()
    return render_template("horario.html", horarios=horarios)


# ================================
# 🕒 CREAR NUEVO HORARIO (por trabajador)
# ================================
@horarios_bp.route("/horarios/nuevo/<int:id>", methods=["GET", "POST"])
def nuevo_horario(id):
    # Obtener el trabajador específico
    personal = Personal.query.get_or_404(id)

    # Solo mostrar los proyectos donde está asignado el trabajador
    proyectos = (
        db.session.query(Proyectos)
        .join(ProyectoPersonal)
        .filter(ProyectoPersonal.personal_id == id)
        .all()
    )

    fecha_actual = date.today().strftime("%Y-%m-%d")

    if request.method == "POST":
        try:
            proyecto_id = request.form.get("proyecto_id")
            hora_entrada = request.form.get("hora_entrada")
            observacion = request.form.get("observacion", "")

            # Validación de campos obligatorios
            if not proyecto_id or not hora_entrada:
                flash("⚠️ Debes completar todos los campos obligatorios", "warning")
                return redirect(url_for("horarios.nuevo_horario", id=id))

            # Crear el nuevo horario
            nuevo = Horario(
                personal_id=personal.id,
                proyecto_id=int(proyecto_id),
                fecha=date.today(),
                hora_entrada=datetime.strptime(hora_entrada, "%H:%M").time(),
                observacion=observacion,
            )

            db.session.add(nuevo)
            db.session.flush()  # 👈 Para obtener el ID antes del commit

            # ===========================
            # 🔔 Crear notificación al trabajador
            # ===========================
            usuario_destino = personal.usuario_data  # Relación con Usuarios

            if usuario_destino:
                proyecto = Proyectos.query.get(int(proyecto_id))
                mensaje_notif = (
                    f"Se te ha asignado un nuevo horario para el proyecto "
                    f"'{proyecto.nombre}' el {nuevo.fecha.strftime('%d/%m/%Y')} "
                    f"a las {nuevo.hora_entrada.strftime('%H:%M')}."
                )

                notificacion = Notificaciones(
                    id_usuario_destino=usuario_destino.id_usuario,
                    mensaje=mensaje_notif,
                    id_horario=nuevo.id
                )
                db.session.add(notificacion)

            db.session.commit()
            flash("✅ Horario registrado correctamente y notificación enviada", "success")

            # 🔁 Redirigir al listado de personal (no al detalle)
            return redirect(url_for("personal.manage_personal"))

        except Exception as e:
            db.session.rollback()
            flash(f"❌ Error al registrar el horario: {str(e)}", "danger")

    # Renderizar formulario
    return render_template(
        "horario.html",
        personal=personal,
        proyectos=proyectos,
        fecha_actual=fecha_actual
    )


# ================================
# 🗑️ ELIMINAR HORARIO
# ================================
@horarios_bp.route("/horarios/eliminar/<int:id>", methods=["POST"])
def eliminar_horario(id):
    horario = Horario.query.get_or_404(id)
    try:
        db.session.delete(horario)
        db.session.commit()
        flash("🗑️ Horario eliminado correctamente", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Error al eliminar horario: {str(e)}", "danger")

    return redirect(url_for("horarios.listar_horarios"))


@horarios_bp.route("/detalle/<int:id>")
def detalle_horario(id):
    horario = Horario.query.get_or_404(id)
    return render_template("detalle_horario.html", horario=horario)


# ================================
# 🔔 MARCAR NOTIFICACIONES COMO LEÍDAS (desde el dropdown)
# ================================
@horarios_bp.route("/notificaciones/marcar_leidas", methods=["POST"])
def marcar_leidas():
    from flask import session

    if "user_id" not in session:
        return {"ok": False, "error": "No autenticado"}, 401

    Notificaciones.query.filter_by(
        id_usuario_destino=session["user_id"],
        leido=False
    ).update({"leido": True})

    db.session.commit()
    return {"ok": True}

