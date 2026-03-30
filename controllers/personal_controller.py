from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import db, Personal, Usuarios, Asistencia, ProyectoPersonal
from flask_bcrypt import Bcrypt
from decimal import Decimal
from datetime import date, datetime, timedelta
import traceback  # Para imprimir la traza completa
import random, string
from mail_utils import enviar_correo
from decorators import login_required, admin_required

personal_bp = Blueprint("personal", __name__)
bcrypt = Bcrypt()

CORREO_EMPRESA_CENTRAL = "corseing@gmail.com"

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

            ##NUEVO CAMPO
            rol_personalizado = request.form.get('rol_personalizado', '').strip()

            costo_diario = Decimal(request.form.get('costo_diario', 0))
            activo = True if request.form.get('activo') == 'on' else False
            contacto = request.form.get('contacto', '').strip() # 👈 Identificador de Login

            # Checkbox: ¿crear usuario?
            crear_usuario = True if request.form.get('crear_usuario') == 'on' else False
            email = request.form.get('email', '').strip() # 👈 Email personal/registro en BD

            ROLES_VALIDOS = ['Ingeniero', 'Trabajador', 'Bodeguero', 'Administrativo', 'Otra']

            if rol not in ROLES_VALIDOS:
                flash("Rol no válido", "danger")
                return redirect(url_for("personal.manage_personal"))
            

            if rol == 'Otra' and not rol_personalizado:
                flash("Debe especificar el rol cuando selecciona 'Otra'", "danger")
                return redirect(url_for("personal.manage_personal"))

            if not nombre or costo_diario <= 0:
                flash("Faltan datos obligatorios", "danger")
                return redirect(url_for("personal.manage_personal"))

            if contacto:
                existente = Personal.query.filter_by(contacto=contacto).first()
                if existente:
                    flash(f"Ya existe una persona registrada con el contacto/teléfono {contacto}", "danger")
                    return redirect(url_for("personal.manage_personal"))
                
            # 1️⃣ Crear el Personal
            nuevo_personal = Personal(
                nombre=nombre,
                rol=rol,
                costo_diario=costo_diario,
                activo=activo,
                contacto=contacto if contacto else None,
                rol_personalizado=rol_personalizado if rol == 'Otra' else None

            ) 
            db.session.add(nuevo_personal)
            db.session.flush()

            # 2️⃣ Si se marcó “Crear usuario” y hay correo
            if crear_usuario and email:
                
                # Revisar si el email ya existe en otro usuario (si unique=False, esta revisión es opcional)
                # Si unique=False, podemos omitir esta verificación para evitar conflictos si muchos usan el mismo correo
                
                temp_pass = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
                hashed_pw = bcrypt.generate_password_hash(temp_pass).decode('utf-8')
                rol_usuario = request.form.get('rol_usuario', 'EMPLEADO')

                nuevo_usuario = Usuarios(
                    nombre=nombre,
                    email=email, #  Se guarda el email personal en la BD
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

                print(f"🔑 Contraseña temporal generada para {nombre}.")

                # 🔹 Enviar correo con Mailjet al CORREO CENTRALIZADO
                to_send_email = CORREO_EMPRESA_CENTRAL 
                subject = f"CLAVE TEMPORAL para {nombre} - Login: {contacto or email}" 
                body = f"""
                Hola,

                Se ha creado la cuenta para el empleado {nombre} (Rol: {rol_usuario.upper()}).
                
                Los datos de login son:
                - **Usuario (Teléfono/Email):** {contacto or email}
                - **Contraseña Temporal:** {temp_pass}

                Esta clave fue enviada al correo centralizado ({CORREO_EMPRESA_CENTRAL}) para que el administrador la comunique al empleado.
                El empleado deberá cambiarla al iniciar sesión.
                """
                
                status, response = enviar_correo(
                    to_email=to_send_email, # CAMBIO CLAVE AQUÍ
                    subject=subject,
                    body_text=body
                )

                if status != 200:
                    print(f"Error enviando correo a {to_send_email}: {response}")
                    flash(f"Usuario creado. ERROR: No se pudo enviar el correo centralizado. ({response})", "warning")
                else:
                    print(f"Correo con clave enviado a {to_send_email}")
                    flash(f"Personal {nombre} agregado y usuario creado. Clave enviada al correo centralizado.", "success")

            else:
                db.session.commit()
                flash(f"Personal {nombre} agregado (sin usuario del sistema)", "success")
            
        except Exception as e:
            db.session.rollback()
            import traceback
            print("ERROR REGISTRANDO PERSONAL:\n", traceback.format_exc())
            flash(f"Error al registrar personal: {str(e)}", "danger")

        return redirect(url_for("personal.manage_personal"))
    
    # 1. Obtener el término de búsqueda de la URL
    termino_busqueda = request.args.get('q', '').strip()

    # 2. Aplicar el filtro a la consulta de personal
    if termino_busqueda:
        personal = Personal.query.filter(Personal.nombre.ilike(f'%{termino_busqueda}%')).all()
    else:
        personal = Personal.query.order_by(Personal.nombre).all()

    personal_asistencia = {personal_item.id: Asistencia.query.filter_by(personal_id=personal_item.id).count() for personal_item in personal}

    return render_template("personal.html", personal=personal, asistencias=personal_asistencia)



# ===============================================================
# Editar personal
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
            rol_personalizado = request.form.get('rol_personalizado', '').strip()
            costo_diario = Decimal(request.form.get('costo_diario', 0))
            activo = True if request.form.get('activo') == 'on' else False
            contacto = request.form.get('contacto', '').strip()
            crear_usuario = request.form.get('crear_usuario') == 'on'
            email = request.form.get('email', '').strip()

            # Validaciones básicas
            if not nombre or costo_diario <= 0:
                flash("Faltan datos obligatorios", "danger")
                return redirect(url_for("personal.manage_personal"))

            ROLES_VALIDOS = ['Ingeniero', 'Trabajador', 'Bodeguero', 'Administrativo', 'Otra']

            if rol not in ROLES_VALIDOS:
                flash("Rol no válido", "danger")
                return redirect(url_for("personal.manage_personal"))

            if rol == 'Otra' and not rol_personalizado:
                flash("Debe especificar el rol cuando selecciona 'Otra'", "danger")
                return redirect(url_for("personal.manage_personal"))

            # Contacto único
            if contacto:
                existente = Personal.query.filter(
                    Personal.contacto == contacto,
                    Personal.id != id
                ).first()
                if existente:
                    flash(f"Ya existe una persona registrada con el contacto {contacto}", "danger")
                    return redirect(url_for("personal.manage_personal"))

            # ✅ ACTUALIZAR PERSONAL (siempre)
            persona.nombre = nombre
            persona.rol = rol
            persona.rol_personalizado = rol_personalizado if rol == 'Otra' else None
            persona.costo_diario = costo_diario
            persona.activo = activo
            persona.contacto = contacto if contacto else None

            # Lógica de Usuario
            if crear_usuario and email:
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

                    # ✉️ Enviar correo al CORREO CENTRALIZADO
                    to_send_email = CORREO_EMPRESA_CENTRAL
                    subject = f"CLAVE TEMPORAL para {nombre} - Login: {contacto or email}"
                    body = f"""
                    Hola,

                    Tu usuario fue creado exitosamente.
                    
                    Los datos de login son:
                    - **Usuario (Teléfono/Email):** {contacto or email}
                    - **Contraseña Temporal:** {temp_pass}

                    Esta clave fue enviada al correo centralizado ({CORREO_EMPRESA_CENTRAL}) para que el administrador la comunique al empleado.
                    Por seguridad, deberás cambiarla al iniciar sesión.
                    """

                    status, response = enviar_correo(
                        to_email=to_send_email,
                        subject=subject,
                        body_text=body
                    )

                    if status == 200:
                        flash(f"Usuario creado y correo enviado al administrador central.", "success")
                    else:
                        flash(f"Usuario creado, pero no se pudo enviar el correo centralizado ({status})", "warning")

                else:
                    # ✅ SI YA EXISTE EL USUARIO: ACTUALIZAR SIEMPRE QUE SE MARQUE "CREAR USUARIO"
                    rol_usuario = request.form.get('rol_usuario', 'EMPLEADO')

                    # ✅ DETECTAR SI EL CORREO CAMBIÓ
                    correo_anterior = usuario.email
                    correo_cambio = (correo_anterior != email)

                    # ✅ ACTUALIZAR DATOS DEL USUARIO
                    usuario.email = email
                    usuario.rol = rol_usuario.upper()
                    usuario.nombre = nombre

                    # ✅ SI EL CORREO CAMBIÓ: REGENERAR CONTRASEÑA Y ENVIAR CORREO
                    if correo_cambio:
                        temp_pass = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
                        hashed_pw = bcrypt.generate_password_hash(temp_pass).decode('utf-8')
                        usuario.password = hashed_pw
                        usuario.debe_cambiar_contrasena = True

                        # ✉️ Enviar correo con nueva contraseña
                        to_send_email = CORREO_EMPRESA_CENTRAL
                        subject = f"CLAVE ACTUALIZADA para {nombre} - Login: {contacto or email}"
                        body = f"""
                        Hola,

                        Tu usuario fue actualizado exitosamente.
                        
                        Los datos de login son:
                        - **Usuario (Teléfono/Email):** {contacto or email}
                        - **Contraseña Temporal:** {temp_pass}

                        Esta clave fue enviada al correo centralizado ({CORREO_EMPRESA_CENTRAL}) para que el administrador la comunique al empleado.
                        Por seguridad, deberás cambiarla al iniciar sesión.
                        """

                        status, response = enviar_correo(
                            to_email=to_send_email,
                            subject=subject,
                            body_text=body
                        )

                        if status == 200:
                            flash(f"Usuario actualizado y nueva contraseña enviada al administrador central.", "success")
                        else:
                            flash(f"Usuario actualizado, pero no se pudo enviar el correo centralizado ({status})", "warning")
                    else:
                        flash(f"Usuario actualizado (correo no cambió).", "success")

            elif not crear_usuario and usuario:
                # Eliminar usuario si no se marca "crear_usuario"
                db.session.delete(usuario)
                persona.usuario_id = None
                flash(f"Usuario eliminado del personal.", "success")

            # ✅ GUARDAR LOS CAMBIOS EN LA BASE DE DATOS
            db.session.commit()
            flash(f"Personal {nombre} actualizado correctamente", "success")
            return redirect(url_for("personal.manage_personal"))

        except Exception as e:
            db.session.rollback()
            import traceback
            print("ERROR ACTUALIZANDO PERSONAL:\n", traceback.format_exc())
            flash(f"Error al actualizar personal: {str(e)}", "danger")
            return redirect(url_for("personal.manage_personal"))

    return redirect(url_for("personal.manage_personal"))

@personal_bp.route('/personal/<int:id>/desactivar')
@login_required
@admin_required
def desactivar_personal(id):
    print(f"🟡 Intentando desactivar personal con id={id}")
    persona = Personal.query.get_or_404(id)
    if not persona.activo:
        flash(f"{persona.nombre} ya está desactivado", "warning")
    else:
        try:
            persona.activo = False
            usuario = Usuarios.query.filter_by(personal_id=persona.id).first()
            print(f"🔎 Usuario asociado: {usuario if usuario else 'Ninguno'}")
            if usuario:
                usuario.rol = "EMPLEADO"
            db.session.commit()
            print(f"✅ {persona.nombre} desactivado")
            flash(f"{persona.nombre} desactivado", "warning")
        except Exception as e:
            db.session.rollback()
            print("❌ Error al desactivar personal")
            print(traceback.format_exc())
            flash(f"Error al desactivar: {str(e)}", "danger")
    return redirect(url_for("personal.manage_personal"))


@personal_bp.route('/personal/<int:id>/activar')
@login_required
@admin_required
def activar_personal(id):
    print(f"🟡 Intentando activar personal con id={id}")
    persona = Personal.query.get_or_404(id)
    if persona.activo:
        flash(f"⚠️ {persona.nombre} ya está activo", "info")
    else:
        try:
            persona.activo = True
            usuario = Usuarios.query.filter_by(personal_id=persona.id).first()
            print(f"🔎 Usuario asociado: {usuario if usuario else 'Ninguno'}")
            if usuario:
                usuario.rol = "EMPLEADO"
            db.session.commit()
            print(f"✅ {persona.nombre} activado nuevamente")
            flash(f"✅ {persona.nombre} activado nuevamente", "success")
        except Exception as e:
            db.session.rollback()
            print("❌ Error al activar personal")
            print(traceback.format_exc())
            flash(f"❌ Error al activar: {str(e)}", "danger")
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
        flash(f"🗑️ {persona.nombre} eliminado junto con su usuario y asistencias", "success")
    except Exception as e:
        db.session.rollback()
        print("❌ Error al eliminar personal")
        print(traceback.format_exc())
        flash(f"❌ Error al eliminar personal: {str(e)}", "danger")

    return redirect(url_for("personal.manage_personal"))

