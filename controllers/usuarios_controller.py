from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models import db, Usuarios, Personal
from flask_bcrypt import Bcrypt
from flask import current_app
from werkzeug.utils import secure_filename
import os
import secrets
from mail_utils import enviar_correo
from decorators import login_required, admin_required
from datetime import datetime


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in current_app.config["ALLOWED_EXTENSIONS"]
    )

usuarios_bp = Blueprint("usuarios", __name__)
bcrypt = Bcrypt()


# -----------------------------
# LOGIN (Usuarios Blueprint)
# -----------------------------
@usuarios_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard.dashboard'))

    if request.method == 'POST':
        # Obtener el valor de identificación del formulario.
        # El formulario ahora enviará el valor en el campo 'contacto'
        user_identifier = request.form.get('contacto', '').strip() 
        password = request.form['password']
        
        # Inicializamos las variables de búsqueda
        user = None
        personal_data = None
        
        # =======================================================
        # LÓGICA DE BÚSQUEDA FLEXIBLE (Teléfono o Correo)
        # =======================================================
        
        # 1. INTENTAR BUSCAR POR TELÉFONO (Contacto de Personal)
        if user_identifier:
            personal_data = Personal.query.filter_by(contacto=user_identifier).first()
            if personal_data:
                # Si encontramos el Personal, buscamos el Usuario asociado
                user = Usuarios.query.filter_by(personal_id=personal_data.id).first()
        
        # 2. SI NO SE ENCONTRÓ NINGÚN USUARIO, INTENTAR BUSCAR POR CORREO ELECTRÓNICO
        if not user:
             # Usamos el identificador directamente como email
             user = Usuarios.query.filter_by(email=user_identifier).first()
             
             # Si se encontró por email, también necesitamos el personal asociado
             if user:
                 personal_data = Personal.query.filter_by(id=user.personal_id).first()

        
        # =======================================================
        #  VALIDACIÓN DESPUÉS DE LA BÚSQUEDA
        # =======================================================

        # 3. VERIFICAR EXISTENCIA DEL USUARIO
        if not user:
            flash("Usuario o contraseña incorrecta.", "danger")
            return render_template("login.html") 

        # 4. BLOQUEO: Verificar si el personal está inactivo (Solo aplica si hay datos de personal)
        # Nota: El administrador (ROL=ADMIN) puede no tener personal_data, por eso esta verificación debe ser condicional.
        if personal_data and not personal_data.activo:
            flash("Tu cuenta ha sido desactivada. Contacta con el administrador.", "danger")
            return render_template("login.html")

        # 5. VERIFICAR CONTRASEÑA
        if bcrypt.check_password_hash(user.password, password):
            # Si la contraseña es correcta, verificar si debe cambiar la contraseña
            if user.debe_cambiar_contrasena:
                # NO CREAR SESIÓN AÚN - dejar que cambie la contraseña
                flash("Debes cambiar tu contraseña antes de continuar.", "warning")
                return redirect(url_for('usuarios.cambiar_password_primera', id=user.id_usuario)) 

            # Login normal (SOLO si NO debe cambiar contraseña)
            session['user_id'] = user.id_usuario
            session['nombre'] = user.nombre
            session['rol'] = user.rol
            session['foto_perfil'] = user.foto_perfil or '/static/uploads/perfiles/default.png'
            
            flash("Login exitoso", "success")
            return redirect(url_for('dashboard.dashboard'))
        else:
            # Contraseña incorrecta
            flash("Usuario o contraseña incorrecta.", "danger")
            return render_template("login.html") 

    return render_template("login.html")


# -----------------------------
# REGISTRO
# -----------------------------
@usuarios_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        nombre = request.form['nombre'].strip()
        email = request.form['email'].strip()
        password = request.form['password']  # ADMIN, BODEGA, EMPLEADO, OFICINA

        existing = Usuarios.query.filter_by(email=email).first()
        if existing:
            flash("Email ya registrado", "danger")
            return redirect(url_for('usuarios.register'))

        hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
        nuevo = Usuarios(
            nombre=nombre,
            email=email,
            password=hashed_pw,
            rol="EMPLEADO"
        )
        db.session.add(nuevo)
        db.session.commit()
        flash("Usuario registrado correctamente", "success")
        return redirect(url_for('usuarios.login'))

    return render_template("olvide_contrasena.html")


# -----------------------------
# LOGOUT
# -----------------------------
@usuarios_bp.route('/logout')
def logout():
    session.clear()
    flash("Sesión cerrada", "info")
    return redirect(url_for('usuarios.login'))

# -----------------------------
# OLVIDE CONTRASENA ENVIAR TOKEN DE RECUPERACION
# -----------------------------
@usuarios_bp.route('/olvide_contrasena', methods=['GET', 'POST'])
def olvide_contrasena():
    if request.method == 'POST':
        telefono = request.form['telefono'].strip()
        
        # Buscar primero en Personal por contacto (teléfono)
        personal = Personal.query.filter_by(contacto=telefono).first()
        
        if not personal:
            flash('No se encontró un trabajador con ese número de contacto.', 'danger')
            return redirect(url_for('usuarios.olvide_contrasena'))

        # Buscar el usuario asociado al personal
        usuario = Usuarios.query.filter_by(personal_id=personal.id).first()
        
        if not usuario:
            flash('No se encontró una cuenta asociada a ese número de contacto.', 'danger')
            return redirect(url_for('usuarios.olvide_contrasena'))

        # Generar contraseña temporal
        temp_password = secrets.token_urlsafe(8)[:8]  # Contraseña de 8 caracteres
        usuario.password = bcrypt.generate_password_hash(temp_password).decode('utf-8')
        usuario.debe_cambiar_contrasena = True
        db.session.commit()

        # Enviar contraseña TEMPORAL al correo centralizado de la empresa
        asunto = f"[TEMPORAL] Contraseña para {usuario.nombre}"
        cuerpo_html = f"""
        Contraseña Temporal - Solicitud de recuperación
        
        Nombre del trabajador: {usuario.nombre}
        Número de contacto: {personal.contacto}
        ID de usuario: {usuario.id_usuario}
        Rol: {usuario.rol}
        Fecha de solicitud: {datetime.now().strftime('%d/%m/%Y %H:%M')}
        Contraseña temporal:{temp_password}
        
        
        Instrucciones:
        
        Entrega esta contraseña a {usuario.nombre} (contacto: {personal.contacto})
        El trabajador deberá cambiarla al iniciar sesión
        Esta contraseña es válida únicamente para el primer inicio de sesión
        
        
        Generado automáticamente por el sistema Corseing.
        """

        # Obtener el correo centralizado desde la configuración
        correo_encargada = current_app.config.get('CORREO_GLOBAL', 'corseing@gmail.com')
        
        if enviar_correo(correo_encargada, asunto, cuerpo_html):
            flash(f'Solicitud procesada. La contraseña temporal se ha enviado al administrador.', 'success')
        else:
            flash('Error al enviar la solicitud al administrador. Contacta directamente.', 'danger')

        return redirect(url_for('usuarios.login'))

    return render_template('olvide_contrasena.html')

# -----------------------------
# CAMBIO DE CONTRASEÑA CON TOKEN
# -----------------------------
@usuarios_bp.route('/cambiar_password/<token>', methods=['GET', 'POST'])
def cambiar_password(token):
    usuario = Usuarios.query.filter_by(reset_token=token).first_or_404()

    if request.method == 'POST':
        nueva_pass = request.form.get('nueva_pass')
        confirmar_pass = request.form.get('confirmar_pass')

        if not nueva_pass or not confirmar_pass:
            flash("Debes llenar ambos campos", "warning")
            return redirect(url_for('usuarios.cambiar_password', token=token))

        if nueva_pass != confirmar_pass:
            flash("Las contraseñas no coinciden", "danger")
            return redirect(url_for('usuarios.cambiar_password', token=token))

        if len(nueva_pass) < 6:
            flash("La nueva contraseña debe tener al menos 6 caracteres", "warning")
            return redirect(url_for('usuarios.cambiar_password', token=token))

        usuario.password = bcrypt.generate_password_hash(nueva_pass).decode('utf-8')
        usuario.reset_token = None
        usuario.debe_cambiar_contrasena = False
        db.session.commit()

        flash("Contraseña actualizada correctamente. Ahora puedes iniciar sesión.", "success")
        return redirect(url_for('usuarios.login'))

    return render_template('cambiar_contrasena.html', usuario=usuario)

# -----------------------------
# CAMBIO DE CONTRASEÑA PRIMER LOGIN
# -----------------------------
@usuarios_bp.route('/cambiar_password_primera/<int:id>', methods=['GET', 'POST'])
def cambiar_password_primera(id):
    usuario = Usuarios.query.get_or_404(id)

    if not usuario:
        flash('Usuario no encontrado', 'danger')
        return redirect(url_for('usuarios.login'))

    if request.method == 'POST':
        nueva_pass = request.form.get('nueva_pass')
        confirmar_pass = request.form.get('confirmar_pass')

        # Validaciones
        if not nueva_pass or not confirmar_pass:
            flash('Debes llenar ambos campos.', 'warning')
            return redirect(url_for('usuarios.cambiar_password_primera', id=id))
        
        if nueva_pass != confirmar_pass:
            flash('Las contraseñas no coinciden.', 'danger')
            return redirect(url_for('usuarios.cambiar_password_primera', id=id))
        
        if len(nueva_pass) < 6:
            flash('La nueva contraseña debe tener al menos 6 caracteres.', 'warning')
            return redirect(url_for('usuarios.cambiar_password_primera', id=id))
        
        #  Actualizar contraseña en la base de datos
        usuario.password = bcrypt.generate_password_hash(nueva_pass).decode('utf-8')
        usuario.debe_cambiar_contrasena = False  # Ya no necesita cambiarla
        db.session.commit()

        flash('Contraseña actualizada correctamente. Ahora puedes iniciar sesión.', 'success')
        return redirect(url_for('usuarios.login'))

    return render_template('cambiar_contrasena_primera.html', usuario=usuario)
        




# -----------------------------
# PERFIL 
# -----------------------------
@usuarios_bp.route("/perfil", methods=["GET", "POST"])
@login_required
def perfil():
    if "user_id" not in session:
        return redirect(url_for("usuarios.login"))

    usuario = Usuarios.query.get(session["user_id"])

    if request.method == "POST":
        if "foto" in request.files:
            file = request.files["foto"]
            if file and file.filename and allowed_file(file.filename):
                from supabase_client import supabase
                import uuid
                
                ext = file.filename.rsplit(".", 1)[-1].lower()
                filename = f"{uuid.uuid4().hex}.{ext}"
                path = f"perfiles/{filename}"
                data = file.read()

                try:
                    supabase.storage.from_("uploads").upload(
                        path, data,
                        {"content-type": file.content_type, "upsert": "false"}
                    )
                    public_url = supabase.storage.from_("uploads").get_public_url(path)
                    
                    usuario.foto_perfil = public_url
                    db.session.commit()
                    session["foto_perfil"] = public_url
                    flash("Foto de perfil actualizada", "success")
                except Exception as e:
                    flash(f"Error al subir foto de perfil: {e}", "danger")

                return redirect(url_for("dashboard.dashboard"))
            else:
                flash("Por favor selecciona una imagen válida", "warning")

    return render_template("perfil.html", usuario=usuario)


# En usuarios_controller.py
# ...
@usuarios_bp.route('/perfil/configuracion', methods=['GET', 'POST'])
@login_required
def configuracion_perfil():
    # Asegurarse de que el usuario esté logueado
    if 'user_id' not in session:
        flash("Debes iniciar sesión para acceder a esta página.", "warning")
        return redirect(url_for('usuarios.login'))

    usuario_id = session['user_id']
    usuario = Usuarios.query.get(usuario_id)

    if not usuario:
        flash("Usuario no encontrado.", "danger")
        return redirect(url_for('dashboard.dashboard'))

    # Almacenar el valor original del correo para comparar después
    correo_original = usuario.email
    # Almacenar el valor original del nombre para comparar después
    nombre_original = usuario.nombre

    if request.method == 'POST':
        nombre = request.form.get('nombre')
        correo = request.form.get('correo')
        nueva_contrasena = request.form.get('nueva_contrasena')
        contrasena_actual = request.form.get('contrasena_actual')

        # Bandera para saber si se intenta cambiar el correo
        correo_cambiado = (correo != correo_original)
        # Bandera para saber si se intenta cambiar el nombre
        nombre_cambiado = (nombre != nombre_original)

        # Actualizar nombre
        if nombre and nombre_cambiado: # Solo si se envió un nombre diferente
            usuario.nombre = nombre
            # Sincronizar el nombre con el Personal asociado
            if usuario.personal_data: # Verificar si tiene Personal asociado
                usuario.personal_data.nombre = nombre

        # Actualizar correo
        if correo and correo_cambiado: # Solo si se envió un correo diferente
            # Si se cambia el correo, se requiere la contraseña actual
            if not contrasena_actual:
                flash("Debes ingresar tu contraseña actual para cambiar el correo.", "warning")
                return render_template('perfil_editar.html', usuario=usuario)

            # Verificar la contraseña actual
            if not bcrypt.check_password_hash(usuario.password, contrasena_actual):
                flash("La contraseña actual es incorrecta.", "danger")
                return render_template('perfil_editar.html', usuario=usuario)

            # Cambiar el correo
            usuario.email = correo

        # Actualizar contraseña
        if nueva_contrasena:
            # Si se cambia la contraseña, se requiere la contraseña actual
            if not contrasena_actual:
                flash("Debes ingresar tu contraseña actual para cambiarla.", "warning")
                return render_template('perfil_editar.html', usuario=usuario)

            # Verificar la contraseña actual
            if not bcrypt.check_password_hash(usuario.password, contrasena_actual):
                flash("La contraseña actual es incorrecta.", "danger")
                return render_template('perfil_editar.html', usuario=usuario)

            # Cambiar la contraseña
            usuario.password = bcrypt.generate_password_hash(nueva_contrasena).decode('utf-8')

        try:
            db.session.commit()
            # Actualizar la sesión si cambió el nombre del Usuario
            if nombre_cambiado:
                session['nombre'] = nombre
            # Actualizar el correo en la sesión si cambió
            if correo_cambiado:
                session['email'] = correo
            flash("Perfil actualizado correctamente.", "success")
            return redirect(url_for('usuarios.configuracion_perfil'))
        except Exception as e:
            db.session.rollback()
            flash(f"Error al actualizar el perfil: {str(e)}", "danger")

    # Si es GET o POST fallida, renderizar la plantilla
    return render_template('perfil_editar.html', usuario=usuario)