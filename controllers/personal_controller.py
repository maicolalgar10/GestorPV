from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import db, Personal, Usuarios, Asistencia, ProyectoPersonal
from flask_bcrypt import Bcrypt
from decimal import Decimal
from datetime import date, datetime, timedelta
import traceback  # 👈 Para imprimir la traza completa
import random, string
from mail_utils import enviar_correo
from decorators import login_required, admin_required

personal_bp = Blueprint("personal", __name__)
bcrypt = Bcrypt()


# -------------------------
# Helper: Asistencia semanal
# -------------------------
def asistencia_dict(personal_id, semana_inicio=None):
    dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]
    hoy = date.today()

    if not semana_inicio:
        semana_inicio = hoy - timedelta(days=hoy.weekday())  # lunes

    registros = Asistencia.query.filter(
        Asistencia.personal_id == personal_id,
        Asistencia.fecha.between(semana_inicio, semana_inicio + timedelta(days=4))
    ).all()

    data = {}
    for i, dia in enumerate(dias):
        fecha = semana_inicio + timedelta(days=i)
        asistencia = next((a for a in registros if a.fecha == fecha), None)

        if asistencia:
            estado = "presente" if asistencia.horas_trabajadas > 0 else "ausente"
            data[dia] = {
                "estado": estado,
                "horas": asistencia.horas_trabajadas,
                "motivo": asistencia.motivo
            }
        else:
            data[dia] = {"estado": "sin registro", "horas": 0, "motivo": None}

    return data


# -------------------------
# Rutas
# -------------------------
@personal_bp.route('/personal', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_personal():
    if request.method == 'POST':
        try:
            nombre = request.form.get('nombre', '').strip()
            rol = request.form.get('rol')
            costo_diario = Decimal(request.form.get('costo_diario', 0))
            activo = True if request.form.get('activo') == 'on' else False
            contacto = request.form.get('contacto', '').strip()

            # Checkbox: ¿crear usuario?
            crear_usuario = True if request.form.get('crear_usuario') == 'on' else False
            email = request.form.get('email', '').strip()

            if rol not in ['Ingeniero', 'Trabajador', 'Supervisor']:
                flash("❌ Rol no válido", "personal-danger")
                return redirect(url_for("personal.manage_personal"))

            if not nombre or costo_diario <= 0:
                flash("❌ Faltan datos obligatorios", "personal-danger")
                return redirect(url_for("personal.manage_personal"))

            if contacto:
                existente = Personal.query.filter_by(contacto=contacto).first()
                if existente:
                    flash(f"❌ Ya existe una persona registrada con el contacto {contacto}", "personal-danger")
                    return redirect(url_for("personal.manage_personal"))
                
            # 1️⃣ Crear el Personal
            nuevo_personal = Personal(
                nombre=nombre,
                rol=rol,
                costo_diario=costo_diario,
                activo=activo,
                contacto=contacto if contacto else None
            )    
            db.session.add(nuevo_personal)
            db.session.flush()

            # 2️⃣ Si se marcó “Crear usuario” y hay correo
            if crear_usuario and email:
                if Usuarios.query.filter_by(email=email).first():
                    flash(f"❌ Ya existe un usuario con el correo {email}", "personal-danger")
                    return redirect(url_for("personal.manage_personal"))
                
                temp_pass = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
                hashed_pw = bcrypt.generate_password_hash(temp_pass).decode('utf-8')
                rol_usuario = request.form.get('rol_usuario', 'EMPLEADO')

                nuevo_usuario = Usuarios(
                    nombre=nombre,
                    email=email,
                    password=hashed_pw,
                    rol=rol_usuario.upper(),
                    foto_perfil="default.png",
                    personal_data=nuevo_personal,
                    debe_cambiar_contrasena=True
                )

                db.session.flush()
                nuevo_personal.usuario_id = nuevo_usuario.id_usuario
                db.session.add(nuevo_usuario)
                db.session.commit()

                print(f"🔑 Contraseña temporal para {nuevo_usuario.email}: {temp_pass}")

                # 🔹 Enviar correo con Mailjet
                subject = "Tu cuenta en el sistema"
                body = f"""
                Hola {nombre},

                Tu usuario fue creado exitosamente en el sistema.
                Tu contraseña temporal es: {temp_pass}

                Por seguridad, deberás cambiarla al iniciar sesión.
                """

                status, response = enviar_correo(
                    to_email=email,
                    subject=subject,
                    body_text=body
                )

                if status != 200:
                    print(f"❌ Error enviando correo a {email}: {response}")
                else:
                    print(f"✅ Correo enviado a {email}")

                flash(f"✅ Personal {nombre} agregado y usuario creado (email: {email})", "personal-success")

            else:
                db.session.commit()
                flash(f"✅ Personal {nombre} agregado (sin usuario del sistema)", "personal-success")
            

            

        except Exception as e:
            db.session.rollback()
            import traceback
            print("ERROR REGISTRANDO PERSONAL:\n", traceback.format_exc())
            flash(f"❌ Error al registrar personal: {str(e)}", "personal-danger")

        return redirect(url_for("personal.manage_personal"))
    
    # 1. Obtener el término de búsqueda de la URL
    termino_busqueda = request.args.get('q', '').strip()

    # 2. Aplicar el filtro a la consulta de personal
    if termino_busqueda:
        personal = Personal.query.filter(Personal.nombre.ilike(f'%{termino_busqueda}%')).all()
    else:
        personal = Personal.query.order_by(Personal.nombre).all()

    personal_asistencia = {p.id:asistencia_dict(p.id) for p in personal}

    return render_template("personal.html", personal=personal, asistencias=personal_asistencia)


@personal_bp.route('/personal/<int:id>/desactivar')
@login_required
@admin_required
def desactivar_personal(id):
    print(f"🟡 Intentando desactivar personal con id={id}")
    persona = Personal.query.get_or_404(id)
    if not persona.activo:
        flash(f"⚠️ {persona.nombre} ya está desactivado", "personal-warning")
    else:
        try:
            persona.activo = False
            usuario = Usuarios.query.filter_by(personal_id=persona.id).first()
            print(f"🔎 Usuario asociado: {usuario if usuario else 'Ninguno'}")
            if usuario:
                usuario.rol = "EMPLEADO"
            db.session.commit()
            print(f"✅ {persona.nombre} desactivado")
            flash(f"🚫 {persona.nombre} desactivado", "personal-warning")
        except Exception as e:
            db.session.rollback()
            print("❌ Error al desactivar personal")
            print(traceback.format_exc())
            flash(f"❌ Error al desactivar: {str(e)}", "personal-danger")
    return redirect(url_for("personal.manage_personal"))


@personal_bp.route('/personal/<int:id>/activar')
@login_required
@admin_required
def activar_personal(id):
    print(f"🟡 Intentando activar personal con id={id}")
    persona = Personal.query.get_or_404(id)
    if persona.activo:
        flash(f"⚠️ {persona.nombre} ya está activo", "personal-info")
    else:
        try:
            persona.activo = True
            usuario = Usuarios.query.filter_by(personal_id=persona.id).first()
            print(f"🔎 Usuario asociado: {usuario if usuario else 'Ninguno'}")
            if usuario:
                usuario.rol = "EMPLEADO"
            db.session.commit()
            print(f"✅ {persona.nombre} activado nuevamente")
            flash(f"✅ {persona.nombre} activado nuevamente", "personal-success")
        except Exception as e:
            db.session.rollback()
            print("❌ Error al activar personal")
            print(traceback.format_exc())
            flash(f"❌ Error al activar: {str(e)}", "personal-danger")
    return redirect(url_for("personal.manage_personal"))


@personal_bp.route('/personal/delete/<int:id>', methods=['POST'])
@login_required
@admin_required
def delete_personal(id):
    print(f"\n🟡 Intentando eliminar personal con id={id}...")
    persona = Personal.query.get_or_404(id)
    print(f"✅ Encontrado personal: {persona.nombre}, activo={persona.activo}")

    try:
        usuario = Usuarios.query.filter_by(personal_id=persona.id).first()
        print(f"🔎 Usuario asociado: {usuario if usuario else 'Ninguno'}")

        asistencias = Asistencia.query.filter_by(personal_id=persona.id).all()
        print(f"📊 Asistencias encontradas: {len(asistencias)}")

        for a in asistencias:
            print(f"   🗑️ Eliminando asistencia del {a.fecha}")
            db.session.delete(a)

        if usuario:
            print(f"   🗑️ Eliminando usuario {usuario.nombre}")
            db.session.delete(usuario)

        print(f"   🗑️ Eliminando personal {persona.nombre}")
        db.session.delete(persona)

        db.session.commit()
        print("✅ Commit realizado correctamente.")
        flash(f"🗑️ {persona.nombre} eliminado junto con su usuario y asistencias", "personal-success")
    except Exception as e:
        db.session.rollback()
        print("❌ Error al eliminar personal")
        print(traceback.format_exc())
        flash(f"❌ Error al eliminar personal: {str(e)}", "personal-danger")

    return redirect(url_for("personal.manage_personal"))


# -------------------------
# Rutas de Asistencia
# -------------------------

# 📘 Ver asistencia semanal
@personal_bp.route('/personal/<int:id>/asistencia', methods=['GET'])
@login_required
@admin_required
def ver_asistencia(id):
    print(f"🟡 Consultando asistencia para personal id={id}")
    persona = Personal.query.get_or_404(id)

    hoy = date.today()
    inicio_semana = hoy - timedelta(days=hoy.weekday())
    dias = [inicio_semana + timedelta(days=i) for i in range(5)]

    registros = Asistencia.query.filter(
        Asistencia.personal_id == id,
        Asistencia.fecha.between(inicio_semana, inicio_semana + timedelta(days=4))
    ).all()

    print(f"📊 Registros de asistencia encontrados: {len(registros)}")

    asistencia_map = {a.fecha: a for a in registros}

    return render_template(
        "asistencia.html",
        persona=persona,
        dias=dias,
        asistencia_map=asistencia_map
    )


# 🆕 NUEVA RUTA: Registro de asistencia (formulario manual)
@personal_bp.route('/personal/<int:id>/registrar_asistencia', methods=['GET', 'POST'])
@login_required
@admin_required
def registrar_asistencia(id):
    print(f"🟢 [DEBUG] Entrando a registrar asistencia del ID={id}")
    trabajador = Personal.query.get_or_404(id)

    # 🔹 Proyectos donde el trabajador está asignado
    proyectos_asignados = [
        asignacion.proyecto for asignacion in ProyectoPersonal.query.filter_by(personal_id=id).all()
    ]

    print(f"🟢 [DEBUG] Proyectos encontrados para {trabajador.nombre}: {[p.nombre for p in proyectos_asignados]}")

    fecha_str = date.today().strftime("%Y-%m-%d")

    # ✅ Si el método es POST, guardamos directamente la asistencia
    if request.method == 'POST':
        try:
            fecha = request.form.get("fecha")
            manana = request.form.get("manana")
            tarde = request.form.get("tarde")
            horas_manana = request.form.get("horas_manana") or 0
            horas_tarde = request.form.get("horas_tarde") or 0
            motivo = request.form.get("motivo")
            proyecto_id = request.form.get("proyecto_id")

            print(f"📥 POST recibido: fecha={fecha}, proyecto={proyecto_id}")

            if not proyecto_id:
                flash("⚠️ Debes seleccionar un proyecto", "personal-warning")
                return redirect(url_for('personal.registrar_asistencia', id=id))

            asistencia = Asistencia(
                personal_id=id,
                proyecto_id=int(proyecto_id),
                fecha=datetime.strptime(fecha, "%Y-%m-%d").date(),
                trabajo_manana=bool(manana),
                trabajo_tarde=bool(tarde),
                horas_trabajadas=int(horas_manana) + int(horas_tarde),
                motivo=motivo
            )
            db.session.add(asistencia)
            db.session.commit()

            flash("✅ Asistencia registrada correctamente", "personal-success")
            print("✅ Asistencia guardada correctamente")

            # ✅ Recargar el formulario vacío tras guardar
            return redirect(url_for('personal.registrar_asistencia', id=id))

        except Exception as e:
            db.session.rollback()
            print("❌ Error al guardar asistencia")
            print(traceback.format_exc())
            flash(f"❌ Error al guardar asistencia: {str(e)}", "personal-danger")

    # ✅ En GET, simplemente renderiza el formulario
    return render_template(
        "asistencia.html",
        trabajador=trabajador,
        proyectos=proyectos_asignados,
        fecha_str=fecha_str,
        asistencia_registrada={}  # ✅ Se envía diccionario vacío para evitar errores Jinja
    )


# 🧾 Guardar asistencia (POST)
@personal_bp.route('/asistencia/<int:id>', methods=['POST'])
@login_required
@admin_required
def save_asistencia(id):
    print(f"🟡 Guardando asistencia para personal id={id}")
    try:
        fecha = request.form.get("fecha")
        manana = request.form.get("manana")
        tarde = request.form.get("tarde")
        horas_manana = request.form.get("horas_manana") or 0
        horas_tarde = request.form.get("horas_tarde") or 0
        motivo = request.form.get("motivo")
        proyecto_id = request.form.get("proyecto_id") or 1

        print(f"📥 Datos recibidos: fecha={fecha}, mañana={manana}, tarde={tarde}, horas_m={horas_manana}, horas_t={horas_tarde}, motivo={motivo}, proyecto_id={proyecto_id}")

        asistencia = Asistencia(
            personal_id=id,
            proyecto_id=int(proyecto_id),
            fecha=datetime.strptime(fecha, "%Y-%m-%d").date(),
            trabajo_manana=True if manana else False,
            trabajo_tarde=True if tarde else False,
            horas_trabajadas=int(horas_manana) + int(horas_tarde),
            motivo=motivo
        )

        db.session.add(asistencia)
        db.session.commit()
        print("✅ Asistencia guardada correctamente")
        flash("✅ Asistencia guardada correctamente", "personal-success")
    except Exception as e:
        db.session.rollback()
        print("❌ Error al guardar asistencia")
        print(traceback.format_exc())
        flash(f"❌ Error al guardar: {str(e)}", "personal-danger")

    return redirect(url_for('personal.manage_personal'))

#####################################################################

# 📋 Detalle del trabajador (con asistencia semanal)
@personal_bp.route('/personal/<int:id>/detalles')
@login_required
@admin_required
def detalles_personal(id):
    persona = Personal.query.get_or_404(id)

    # Calcular inicio de semana (lunes)
    hoy = date.today()
    inicio_semana = hoy - timedelta(days=hoy.weekday())

    # Obtener asistencias de lunes a viernes
    registros = Asistencia.query.filter(
        Asistencia.personal_id == id,
        Asistencia.fecha.between(inicio_semana, inicio_semana + timedelta(days=4))
    ).all()

    # Mapear días con estado
    dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]
    asistencia_detalle = []

    for i, dia_nombre in enumerate(dias_semana):
        fecha = inicio_semana + timedelta(days=i)
        registro = next((a for a in registros if a.fecha == fecha), None)

        if registro:
            estado = "presente" if registro.horas_trabajadas > 0 else "ausente"
            asistencia_detalle.append({
                "dia": dia_nombre,
                "estado": estado,
                "horas": registro.horas_trabajadas,
                "motivo": registro.motivo,
                "proyecto": registro.proyecto.nombre if registro.proyecto else None
            })
        else:
            asistencia_detalle.append({
                "dia": dia_nombre,
                "estado": "sin registro",
                "horas": 0,
                "motivo": None,
                "proyecto": None
            })

    # Datos estadísticos
    proyectos_activos = ProyectoPersonal.query.filter_by(personal_id=id).count()
    dias_presentes = sum(1 for a in asistencia_detalle if a["estado"] == "presente")
    horas_total = sum(a["horas"] for a in asistencia_detalle)

    return render_template(
        "personal_detalles.html",
        persona=persona,
        asistencia_detalle=asistencia_detalle,
        proyectos_activos=proyectos_activos,
        dias_presentes=dias_presentes,
        horas_total=horas_total
    )

# ===============================================================
# ✏️ Editar personal
# ===============================================================
@personal_bp.route('/personal/editar/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def editar_personal(id):
    persona = Personal.query.get_or_404(id)
    usuario = Usuarios.query.filter_by(personal_id=id).first()

    if request.method == 'POST':
        try:
            nombre = request.form.get('nombre', '').strip()
            rol = request.form.get('rol')
            costo_diario = Decimal(request.form.get('costo_diario', 0))
            activo = True if request.form.get('activo') == 'on' else False
            contacto = request.form.get('contacto', '').strip()

            crear_usuario = request.form.get('crear_usuario') == 'on'
            email = request.form.get('email', '').strip()

            # Validaciones básicas
            if not nombre or costo_diario <= 0:
                flash("❌ Faltan datos obligatorios", "personal-danger")
                return redirect(url_for("personal.manage_personal"))

            if rol not in ['Ingeniero', 'Trabajador', 'Supervisor']:
                flash("❌ Rol no válido", "personal-danger")
                return redirect(url_for("personal.manage_personal"))

            # Contacto único
            if contacto:
                existente = Personal.query.filter(
                    Personal.contacto == contacto,
                    Personal.id != id
                ).first()
                if existente:
                    flash(f"❌ Ya existe una persona registrada con el contacto {contacto}", "personal-danger")
                    return redirect(url_for("personal.manage_personal"))

            persona.nombre = nombre
            persona.rol = rol
            persona.costo_diario = costo_diario
            persona.activo = activo
            persona.contacto = contacto if contacto else None

            if crear_usuario and email:
                # 🔄 Asegurar que SQLAlchemy vea los datos actuales

                # ⚠️ Verificar si ya existe un usuario con ese email en toda la DB
                usuario_existente = Usuarios.query.filter(Usuarios.email == email).first()

                if usuario_existente and usuario_existente.personal_id != persona.id:

                    flash(f"❌ Ya existe un usuario con el correo {email}", "personal-danger")
                    return redirect(url_for("personal.manage_personal"))

                if not usuario:
                    # Crear nuevo usuario
                    temp_pass = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
                    hashed_pw = bcrypt.generate_password_hash(temp_pass).decode('utf-8')
                    rol_usuario = request.form.get('rol_usuario', 'EMPLEADO')

                    nuevo_usuario = Usuarios(
                        nombre=nombre,
                        email=email,
                        password=hashed_pw,
                        rol=rol_usuario.upper(),
                        foto_perfil="default.png",
                        personal_data=persona,
                        debe_cambiar_contrasena=True
                    )
                    db.session.add(nuevo_usuario)
                    db.session.flush()
                    persona.usuario_id = nuevo_usuario.id_usuario

                    # ✉️ Enviar correo
                    from mail_utils import enviar_correo
                    subject = "Tu cuenta en el sistema"
                    body = f"""
                    Hola {nombre},

                    Tu usuario fue creado exitosamente.
                    Tu contraseña temporal es: {temp_pass}

                    Por seguridad, deberás cambiarla al iniciar sesión.
                    """
                    status, response = enviar_correo(
                        to_email=email,
                        subject=subject,
                        body_text=body
                    )

                    if status == 200:
                        flash(f"✅ Usuario creado y correo enviado a {email}", "personal-success")
                    else:
                        flash(f"⚠️ Usuario creado, pero no se pudo enviar el correo ({status})", "warning")

                else:
                    # Si ya existe el usuario, actualiza datos
                    usuario.email = email
                    usuario.rol = request.form.get('rol_usuario', 'EMPLEADO').upper()
            elif not crear_usuario and usuario:
                db.session.delete(usuario)
                persona.usuario_id = None

            db.session.commit()
            flash(f"✅ Personal {nombre} actualizado correctamente", "personal-success")
            return redirect(url_for("personal.manage_personal"))

        except Exception as e:
            db.session.rollback()
            import traceback
            print("ERROR ACTUALIZANDO PERSONAL:\n", traceback.format_exc())
            flash(f"❌ Error al actualizar personal: {str(e)}", "personal-danger")
            return redirect(url_for("personal.manage_personal"))

    return redirect(url_for("personal.manage_personal"))
