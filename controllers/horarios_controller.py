from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models import db, Horario, Personal, Proyectos, ProyectoPersonal, Notificaciones, AsignacionDiaria
from datetime import datetime, date
from decorators import login_required, admin_required

horarios_bp = Blueprint("horarios", __name__)



@horarios_bp.route("/asignaciones_diarias", methods=['GET', 'POST'])
@login_required
@admin_required
def gestion_asignaciones_diarias():
    if request.method == 'POST':
        try:
            fecha_str = request.form['fecha']
            proyecto_id = int(request.form['proyecto_id'])
            personal_ids = request.form.getlist('personal_id') # Obtiene una lista de IDs
            hora_entrada_str = request.form.get('hora_entrada', '08:00') # Hora por defecto
            observacion = request.form.get('observacion', '')

            # Validaciones
            if not fecha_str or not proyecto_id or not personal_ids:
                flash("⚠️ Debes completar la fecha, seleccionar un proyecto y al menos un trabajador.", "warning")
                return redirect(url_for('horarios.gestion_asignaciones_diarias'))

            fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
            hora_entrada = datetime.strptime(hora_entrada_str, "%H:%M").time()

            proyecto = Proyectos.query.get_or_404(proyecto_id)

            # Eliminar asignaciones anteriores para esta fecha y proyecto (opcional, para reemplazar)
            # AsignacionDiaria.query.filter_by(fecha=fecha, proyecto_id=proyecto_id).delete()

            # Crear nuevas asignaciones para cada trabajador seleccionado
            for p_id_str in personal_ids:
                p_id_int = int(p_id_str)
                persona = Personal.query.get_or_404(p_id_int)

                nueva_asignacion = AsignacionDiaria(
                    fecha=fecha,
                    proyecto_id=proyecto_id,
                    personal_id=p_id_int,
                    hora_entrada=hora_entrada,
                    observacion=observacion
                )
                db.session.add(nueva_asignacion)

                # 🔔 Enviar notificación al trabajador
                usuario_destino = persona.usuario_data
                if usuario_destino:
                    mensaje_notif = (
                        f"Has sido asignado para trabajar en el proyecto '{proyecto.nombre}' "
                        f"el día {fecha.strftime('%d/%m/%Y')} a las {hora_entrada.strftime('%H:%M')}."
                        f"{' Observación: ' + observacion if observacion else ''}"
                    )
                    notificacion = Notificaciones(
                        id_usuario_destino=usuario_destino.id_usuario,
                        mensaje=mensaje_notif,
                        leido=False
                    )
                    db.session.add(notificacion)

            db.session.commit()
            flash(f"✅ {len(personal_ids)} trabajadores asignados al proyecto '{proyecto.nombre}' para el {fecha.strftime('%d/%m/%Y')}.", "success")

        except Exception as e:
            db.session.rollback()
            print(f"❌ Error al crear asignaciones diarias: {e}")
            flash(f"❌ Error al crear asignaciones: {str(e)}", "danger")

        return redirect(url_for('horarios.gestion_asignaciones_diarias'))

    # GET: Mostrar la vista para agrupar personal
    fecha_seleccionada = request.args.get('fecha', date.today().strftime('%Y-%m-%d'))
    try:
        fecha_obj = datetime.strptime(fecha_seleccionada, "%Y-%m-%d").date()
    except ValueError:
        fecha_obj = date.today()
        fecha_seleccionada = fecha_obj.strftime('%Y-%m-%d')

    # Obtener todas las asignaciones para la fecha seleccionada
    asignaciones_del_dia = (
        db.session.query(AsignacionDiaria, Personal, Proyectos)
        .join(Personal, AsignacionDiaria.personal_id == Personal.id)
        .join(Proyectos, AsignacionDiaria.proyecto_id == Proyectos.id_proyecto)
        .filter(AsignacionDiaria.fecha == fecha_obj)
        .order_by(Proyectos.nombre, Personal.nombre)
        .all()
    )

    # Agrupar por proyecto
    asignaciones_agrupadas = {}
    for asignacion, personal, proyecto in asignaciones_del_dia:
        if proyecto.nombre not in asignaciones_agrupadas:
            asignaciones_agrupadas[proyecto.nombre] = {
                'proyecto': proyecto,
                'trabajadores': []
            }
        asignaciones_agrupadas[proyecto.nombre]['trabajadores'].append({
                "id": personal.id, # ID del personal
                "nombre": personal.nombre,
                "rol": personal.rol,
                "hora_entrada": asignacion.hora_entrada.strftime('%H:%M'), # Hora de la asignación diaria
                "observacion": asignacion.observacion or '', # Observación de la asignación diaria
                "id_asignacion_diaria": asignacion.id # ✅ ESTE ES EL ID REAL QUE DEBES PASAR
            })

    # Obtener listas para el formulario
    proyectos = Proyectos.query.all()
    personal = Personal.query.filter_by(activo=True).all()

    return render_template(
        "gestion_asignaciones_diarias.html",
        asignaciones_agrupadas=asignaciones_agrupadas,
        proyectos=proyectos,
        personal=personal,
        fecha_seleccionada=fecha_seleccionada
    )


# ================================
# 🗑️ ELIMINAR ASIGNACIÓN DIARIA INDIVIDUAL (si es necesario)
# ================================
@horarios_bp.route("/asignacion_diaria/eliminar/<int:id>", methods=["POST"])
@login_required
@admin_required
def eliminar_asignacion_diaria(id):
    asignacion = AsignacionDiaria.query.get_or_404(id)
    try:
        proyecto_nombre = asignacion.proyecto.nombre
        personal_nombre = asignacion.personal.nombre
        fecha = asignacion.fecha

        db.session.delete(asignacion)
        db.session.commit()
        flash(f"🗑️ Asignación de {personal_nombre} al proyecto {proyecto_nombre} para el {fecha.strftime('%d/%m/%Y')} eliminada.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Error al eliminar la asignación: {str(e)}", "danger")

    # Volver a la vista de gestión del día actual o del día de la asignación eliminada
    return redirect(url_for("horarios.gestion_asignaciones_diarias", fecha=asignacion.fecha.strftime('%Y-%m-%d')))


# ================================
# 📝 EXPORTAR MENSAJE PARA WHATSAPP
# ================================
@horarios_bp.route("/asignaciones_diarias/exportar_whatsapp")
@login_required
@admin_required
def exportar_whatsapp():
    fecha_str = request.args.get('fecha', date.today().strftime('%Y-%m-%d'))
    try:
        fecha_obj = datetime.strptime(fecha_str, "%Y-%m-%d").date()
    except ValueError:
        fecha_obj = date.today()
        fecha_str = fecha_obj.strftime('%Y-%m-%d')

    # Obtener todas las asignaciones para la fecha seleccionada
    asignaciones_del_dia = (
        db.session.query(AsignacionDiaria, Personal, Proyectos)
        .join(Personal, AsignacionDiaria.personal_id == Personal.id)
        .join(Proyectos, AsignacionDiaria.proyecto_id == Proyectos.id_proyecto)
        .filter(AsignacionDiaria.fecha == fecha_obj)
        .order_by(Proyectos.nombre, Personal.nombre)
        .all()
    )

    # Agrupar por proyecto para el mensaje
    mensaje_whatsapp = f"*PROGRAMACIÓN DEL DÍA {fecha_obj.strftime('%d/%m/%Y')}*\n\n"
    proyectos_dict = {}
    for asignacion, personal, proyecto in asignaciones_del_dia:
        if proyecto.nombre not in proyectos_dict:
            proyectos_dict[proyecto.nombre] = {
                'proyecto': proyecto,
                'trabajadores': []
            }
        proyectos_dict[proyecto.nombre]['trabajadores'].append({
            'nombre': personal.nombre,
            'hora_entrada': asignacion.hora_entrada.strftime('%H:%M'),
            'observacion': asignacion.observacion
        })

    for nombre_proyecto, data in proyectos_dict.items():
        mensaje_whatsapp += f"*{nombre_proyecto}*\n"
        for trabajador in data['trabajadores']:
            mensaje_whatsapp += f"- {trabajador['nombre']} ({trabajador['hora_entrada']})"
            if trabajador['observacion']:
                mensaje_whatsapp += f" - Obs: {trabajador['observacion']}"
            mensaje_whatsapp += "\n"
        mensaje_whatsapp += "\n" # Espacio entre proyectos

    # Devolver el mensaje como texto plano para copiar
    return mensaje_whatsapp, 200, {'Content-Type': 'text/plain; charset=utf-8'}





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

    if "user_id" not in session:
        return {"ok": False, "error": "No autenticado"}, 401

    Notificaciones.query.filter_by(
        id_usuario_destino=session["user_id"],
        leido=False
    ).update({"leido": True})

    db.session.commit()
    return {"ok": True}

