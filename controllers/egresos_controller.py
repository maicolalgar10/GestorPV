import os
from datetime import datetime
from flask import Blueprint, render_template, request, flash, redirect, url_for, session, current_app
from models import db, Usuarios, EgresoCaja, EgresoCajaDesglose
from helpers import clean_amount
from werkzeug.utils import secure_filename
from functools import wraps

egresos_bp = Blueprint('egresos', __name__)

# Reutilizar validadores o definir dependencias
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Por favor inicie sesión para acceder a esta página.", "warning")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated_function

def admin_oficina_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "rol" not in session or session["rol"] not in ["ADMIN", "OFICINA"]:
            flash("Acceso denegado. Se requiere rol de Administrador o de Oficina.", "danger")
            return redirect(url_for("dashboard.index"))
        return f(*args, **kwargs)
    return decorated_function

@egresos_bp.route('/oficina/egresos/')
@login_required
@admin_oficina_required
def index():
    usuario = Usuarios.query.get(session["user_id"])
    egresos = EgresoCaja.query.order_by(EgresoCaja.fecha.desc()).all()
    return render_template("oficina/egresos.html", usuario=usuario, egresos=egresos)

@egresos_bp.route('/oficina/egresos/crear', methods=['POST'])
@login_required
@admin_oficina_required
def crear():
    try:
        persona_prestamo = request.form.get('persona_prestamo')
        identificacion = request.form.get('identificacion')
        fecha = request.form.get('fecha')
        monto_str = request.form.get('monto_total')
        concepto = request.form.get('concepto')
        forma_pago = request.form.get('forma_pago')

        if not persona_prestamo or not fecha or not monto_str:
            flash('Faltan campos obligatorios.', 'warning')
            return redirect(url_for('egresos.index'))

        monto_total = clean_amount(monto_str)

        nuevo_egreso = EgresoCaja(
            persona_prestamo=persona_prestamo,
            identificacion=identificacion,
            fecha=datetime.strptime(fecha, '%Y-%m-%d').date(),
            monto_total=monto_total,
            concepto=concepto,
            forma_pago=forma_pago
        )

        db.session.add(nuevo_egreso)
        db.session.commit()
        flash('Egreso de caja registrado exitosamente.', 'success')
    except Exception as e:
        db.session.rollback()
        print(f"Error al crear egreso de caja: {e}")
        flash('Ocurrió un error al registrar el egreso.', 'danger')

    return redirect(url_for('egresos.index'))

@egresos_bp.route('/oficina/egresos/desglose/agregar', methods=['POST'])
@login_required
@admin_oficina_required
def agregar_desglose():
    try:
        egreso_id = request.form.get('egreso_id')
        concepto_gasto = request.form.get('concepto_gasto')
        monto_str = request.form.get('monto')
        fecha_gasto = request.form.get('fecha_gasto')
        observacion = request.form.get('observacion')

        if not egreso_id or not concepto_gasto or not monto_str or not fecha_gasto:
            flash('Faltan campos obligatorios en el desglose.', 'warning')
            return redirect(url_for('egresos.index'))

        monto = clean_amount(monto_str)

        # Procesar archivo PDF si existe
        pdf_url = None
        pdf_file = request.files.get('pdf_soporte')
        if pdf_file and pdf_file.filename != '':
            if not pdf_file.filename.lower().endswith('.pdf'):
                flash('El soporte debe ser un archivo PDF.', 'warning')
                return redirect(url_for('egresos.index'))
            
            filename = secure_filename(f"egreso_{egreso_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf")
            # Ensure upload folder exists
            upload_path = os.path.join(current_app.root_path, 'static', 'uploads', 'egresos')
            os.makedirs(upload_path, exist_ok=True)
            
            file_path = os.path.join(upload_path, filename)
            pdf_file.save(file_path)
            pdf_url = f"uploads/egresos/{filename}"

        nuevo_desglose = EgresoCajaDesglose(
            egreso_id=egreso_id,
            concepto_gasto=concepto_gasto,
            monto=monto,
            fecha_gasto=datetime.strptime(fecha_gasto, '%Y-%m-%d').date(),
            pdf_url=pdf_url,
            observacion=observacion
        )

        db.session.add(nuevo_desglose)
        db.session.commit()
        flash('Gasto desglosado agregado exitosamente.', 'success')
    except Exception as e:
        db.session.rollback()
        print(f"Error al agregar desglose de egreso: {e}")
        flash('Ocurrió un error al agregar el gasto.', 'danger')

    return redirect(url_for('egresos.index'))
