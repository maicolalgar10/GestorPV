from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models import db, Usuarios
from flask_bcrypt import Bcrypt
from flask import current_app
from werkzeug.utils import secure_filename
import os
import secrets
from mail_utils import enviar_correo
from decorators import login_required, admin_required


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in current_app.config["ALLOWED_EXTENSIONS"]
    )

usuarios_bp = Blueprint("usuarios", __name__)
bcrypt = Bcrypt()
# -----------------------------
# LOGIN
# -----------------------------
@usuarios_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard.dashboard'))

    if request.method == 'POST':
        email = request.form['email'].strip()
        password = request.form['password']

        user = Usuarios.query.filter_by(email=email).first()

        # ✅ PRIMERO: Verificar si el usuario existe
        if not user:
            flash("❌ Usuario no encontrado", "danger")
            return render_template("login.html") # Asegúrate de retornar para no seguir procesando

        # ✅ AHORA: 'user' está garantizado que no es None.
        # 🔒 Bloquear usuarios con personal inactivo
        # ✅ CORRECTO: Verifica si tiene personal_data y si está inactivo
        if user.personal_data and not user.personal_data.activo:
            flash("🚫 Tu cuenta ha sido desactivada. Contacta con el administrador.", "danger")
            return render_template("login.html")

        # ✅ AHORA: Verificar la contraseña
        elif bcrypt.check_password_hash(user.password, password):
            # Si la contraseña es correcta, verificar si debe cambiar la contraseña
            if user.debe_cambiar_contrasena:
                session['user_id'] = user.id_usuario
                session['nombre'] = user.nombre
                session['rol'] = user.rol
                session['foto_perfil'] = user.foto_perfil or '/static/uploads/perfiles/default.png'
                flash("⚠️ Debes cambiar tu contraseña antes de continuar.", "warning")
                return redirect(url_for('usuarios.cambiar_password_primera', id=user.id_usuario))  # Redirigir a cambiar contraseña

            # Si no debe cambiar la contraseña, proceder con el login normal
            session['user_id'] = user.id_usuario
            session['nombre'] = user.nombre
            session['rol'] = user.rol
            session['foto_perfil'] = user.foto_perfil or '/static/uploads/perfiles/default.png'
        
            flash("✅ Login exitoso", "success")
            return redirect(url_for('dashboard.dashboard'))
        else:
            # Si el usuario *sí existe* pero la contraseña es incorrecta
            flash("❌ Credenciales incorrectas", "danger")
            return render_template("login.html") # Asegúrate de retornar aquí también


    return render_template("login.html")


# -----------------------------
# REGISTRO
# -----------------------------
@usuarios_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        nombre = request.form['nombre'].strip()
        email = request.form['email'].strip()
        password = request.form['password']  # ADMIN, ENCARGADO, EMPLEADO

        existing = Usuarios.query.filter_by(email=email).first()
        if existing:
            flash("❌ Email ya registrado", "danger")
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
        flash("✅ Usuario registrado correctamente", "success")
        return redirect(url_for('usuarios.login'))

    return render_template("olvide_contrasena.html")


# -----------------------------
# LOGOUT
# -----------------------------
@usuarios_bp.route('/logout')
def logout():
    session.clear()
    flash("👋 Sesión cerrada", "info")
    return redirect(url_for('usuarios.login'))

# -----------------------------
# OLVIDE CONTRASENA ENVIAR TOKEN DE RECUPERACION
# -----------------------------
@usuarios_bp.route('/olvide_contrasena', methods=['GET', 'POST'])
def olvide_contrasena():
    if request.method == 'POST':
        email = request.form['email']
        usuario = Usuarios.query.filter_by(email=email).first()

        
        if not usuario:
            flash('No existe una cuenta con ese correo.', 'danger')
            return redirect(url_for('usuarios.olvide_contrasena'))

        # Enviar correo con enlace de restablecimiento
        token = secrets.token_urlsafe(32)
        usuario.reset_token = token
        db.session.commit()


        # URL de recuperación
        enlace = url_for('usuarios.cambiar_password', token=token, _external=True)

        # 📧 Enviar correo con Mailjet
        asunto = "🔐 Recuperar contraseña - Corseing"
        cuerpo_html = f"""
        Hola {usuario.nombre},
        Has solicitado restablecer tu contraseña.
        Haz clic en el siguiente enlace para continuar:
        {enlace} Restablecer contraseña
        
        Si no solicitaste este cambio, ignora este mensaje.
        
        Este correo fue generado automáticamente por el sistema Corseing.
        """

        if enviar_correo(usuario.email, asunto, cuerpo_html):
            flash('📨 Te hemos enviado un enlace a tu correo para restablecer la contraseña.', 'success')
        else:
            flash('❌ No se pudo enviar el correo. Inténtalo más tarde.', 'danger')

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
            flash("⚠️ Debes llenar ambos campos", "warning")
            return redirect(url_for('usuarios.cambiar_password', token=token))

        if nueva_pass != confirmar_pass:
            flash("❌ Las contraseñas no coinciden", "danger")
            return redirect(url_for('usuarios.cambiar_password', token=token))

        if len(nueva_pass) < 6:
            flash("⚠️ La nueva contraseña debe tener al menos 6 caracteres", "warning")
            return redirect(url_for('usuarios.cambiar_password', token=token))

        usuario.password = bcrypt.generate_password_hash(nueva_pass).decode('utf-8')
        usuario.reset_token = None
        usuario.debe_cambiar_contrasena = False
        db.session.commit()

        flash("✅ Contraseña actualizada correctamente. Ahora puedes iniciar sesión.", "success")
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
            flash('⚠️ Debes llenar ambos campos.', 'warning')
            return redirect(url_for('usuarios.cambiar_password_primera', id=id))
        
        if nueva_pass != confirmar_pass:
            flash('❌ Las contraseñas no coinciden.', 'danger')
            return redirect(url_for('usuarios.cambiar_password_primera', id=id))
        
        if len(nueva_pass) < 6:
            flash('⚠️ La nueva contraseña debe tener al menos 6 caracteres.', 'warning')
            return redirect(url_for('usuarios.cambiar_password_primera', id=id))
        
        # ✅ Actualizar contraseña en la base de datos
        usuario.password = bcrypt.generate_password_hash(nueva_pass).decode('utf-8')
        usuario.debe_cambiar_contrasena = False  # Ya no necesita cambiarla
        db.session.commit()

        flash('✅ Contraseña actualizada correctamente. Ahora puedes iniciar sesión.', 'success')
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
            if file and file.filename and allowed_file(file.filename):  # ✅ Verifica que el archivo tenga nombre
                filename = secure_filename(file.filename)
                
                # ✅ Asegúrate de que la carpeta existe
                upload_path = os.path.join(current_app.config["UPLOAD_FOLDER"])
                os.makedirs(upload_path, exist_ok=True)
                
                filepath = os.path.join(upload_path, filename)
                file.save(filepath)

                # Guardar ruta relativa en BD
                usuario.foto_perfil = f"/static/uploads/perfiles/{filename}"
                db.session.commit()

                # Actualizar sesión
                session["foto_perfil"] = usuario.foto_perfil

                flash("✅ Foto de perfil actualizada", "success")
                return redirect(url_for("dashboard.dashboard"))
            else:
                flash("⚠️ Por favor selecciona una imagen válida", "warning")

    return render_template("perfil.html", usuario=usuario)


# En usuarios_controller.py
# ...
@usuarios_bp.route('/perfil/configuracion', methods=['GET', 'POST'])
@login_required
def configuracion_perfil():
    # Asegurarse de que el usuario esté logueado
    if 'user_id' not in session:
        flash("⚠️ Debes iniciar sesión para acceder a esta página.", "warning")
        return redirect(url_for('usuarios.login'))

    usuario_id = session['user_id']
    usuario = Usuarios.query.get(usuario_id)

    if not usuario:
        flash("❌ Usuario no encontrado.", "danger")
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
            # ✅ Sincronizar el nombre con el Personal asociado
            if usuario.personal_data: # Verificar si tiene Personal asociado
                usuario.personal_data.nombre = nombre

        # Actualizar correo
        if correo and correo_cambiado: # Solo si se envió un correo diferente
            # Si se cambia el correo, se requiere la contraseña actual
            if not contrasena_actual:
                flash("⚠️ Debes ingresar tu contraseña actual para cambiar el correo.", "warning")
                return render_template('perfil_editar.html', usuario=usuario)

            # Verificar la contraseña actual
            if not bcrypt.check_password_hash(usuario.password, contrasena_actual):
                flash("⚠️ La contraseña actual es incorrecta.", "danger")
                return render_template('perfil_editar.html', usuario=usuario)

            # Cambiar el correo
            usuario.email = correo

        # Actualizar contraseña
        if nueva_contrasena:
            # Si se cambia la contraseña, se requiere la contraseña actual
            if not contrasena_actual:
                flash("⚠️ Debes ingresar tu contraseña actual para cambiarla.", "warning")
                return render_template('perfil_editar.html', usuario=usuario)

            # Verificar la contraseña actual
            if not bcrypt.check_password_hash(usuario.password, contrasena_actual):
                flash("⚠️ La contraseña actual es incorrecta.", "danger")
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
            flash("✅ Perfil actualizado correctamente.", "success")
            return redirect(url_for('usuarios.configuracion_perfil'))
        except Exception as e:
            db.session.rollback()
            flash(f"❌ Error al actualizar el perfil: {str(e)}", "danger")

    # Si es GET o POST fallida, renderizar la plantilla
    return render_template('perfil_editar.html', usuario=usuario)
# ...