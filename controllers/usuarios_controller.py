from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models import db, Usuarios
from flask_bcrypt import Bcrypt
from flask import current_app
from werkzeug.utils import secure_filename
import os
import secrets
from flask_mail import Message
from extensions import mail

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

        if not user:
            flash("❌ Usuario no encontrado", "danger")
        elif bcrypt.check_password_hash(user.password, password):
            session['user_id'] = user.id_usuario
            session['nombre'] = user.nombre
            session['rol'] = user.rol
            flash("✅ Login exitoso", "success")
            return redirect(url_for('dashboard.dashboard'))
        else:
            flash("❌ Credenciales incorrectas", "danger")

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


        msg = Message(
            subject='Recuperar contraseña',
            sender=current_app.config['MAIL_USERNAME'],
            recipients=[email],
            body=f'Hola, para restablecer tu contraseña entra al siguiente enlace:\n\n{url_for("usuarios.cambiar_password", token=token, _external=True)}'
        )
        mail.send(msg)

        flash('Te hemos enviado un enlace a tu correo para restablecer la contraseña.', 'success')
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
# DECORADOR LOGIN_REQUIRED
# -----------------------------
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            flash("⚠️ Debes iniciar sesión primero", "warning")
            return redirect(url_for('usuarios.login'))
        return f(*args, **kwargs)
    return wrapper


# -----------------------------
# PERFIL 
# -----------------------------
@usuarios_bp.route("/perfil", methods=["GET", "POST"])
def perfil():
    if "user_id" not in session:
        return redirect(url_for("usuarios.login"))

    usuario = Usuarios.query.get(session["user_id"])

    if request.method == "POST":
        if "foto" in request.files:
            file = request.files["foto"]
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
                file.save(filepath)

                # Guardar en BD
                usuario.foto_perfil = f"uploads/perfiles/{filename}"
                db.session.commit()

                # 👇 Actualizar también la sesión
                session["foto_perfil"] = usuario.foto_perfil

                flash("✅ Foto de perfil actualizada", "success")
                return redirect(url_for("dashboard.dashboard"))

    return render_template("perfil.html", usuario=usuario)