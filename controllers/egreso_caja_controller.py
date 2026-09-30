import os
from datetime import datetime
from flask import Blueprint, render_template, request, flash, redirect, url_for, session, current_app
from models import db, Usuarios, EgresoCaja, EgresoCajaDesglose
from helpers import clean_amount
from werkzeug.utils import secure_filename
from functools import wraps

egreso_caja_bp = Blueprint('egreso_caja', __name__)

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

@egreso_caja_bp.route('/oficina/egreso_caja')
@login_required
@admin_oficina_required
def index():
    usuario = Usuarios.query.get(session["user_id"])
    egresos = EgresoCaja.query.order_by(EgresoCaja.fecha.desc()).all()
    return render_template("oficina/egresos.html", usuario=usuario, egresos=egresos)

@egreso_caja_bp.route('/oficina/egreso_caja/crear', methods=['POST'])
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
            return redirect(url_for('egreso_caja.index'))

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

    return redirect(url_for('egreso_caja.index'))

@egreso_caja_bp.route('/oficina/egreso_caja/desglose/agregar', methods=['POST'])
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
            return redirect(url_for('egreso_caja.index'))

        monto = clean_amount(monto_str)

        pdf_url = None
        pdf_file = request.files.get('pdf_soporte')
        if pdf_file and pdf_file.filename != '':
            if not pdf_file.filename.lower().endswith('.pdf'):
                flash('El soporte debe ser un archivo PDF.', 'warning')
                return redirect(url_for('egreso_caja.index'))
            
            filename = secure_filename(f"egreso_{egreso_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf")
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

    return redirect(url_for('egreso_caja.index'))


@egreso_caja_bp.route('/oficina/egreso_caja/editar/<int:id>', methods=['POST'])
@login_required
@admin_oficina_required
def editar(id):
    egreso = EgresoCaja.query.get_or_404(id)
    try:
        egreso.persona_prestamo = request.form.get('persona_prestamo')
        egreso.identificacion = request.form.get('identificacion')
        egreso.fecha = datetime.strptime(request.form.get('fecha'), '%Y-%m-%d').date()
        egreso.monto_total = clean_amount(request.form.get('monto_total'))
        egreso.concepto = request.form.get('concepto')
        egreso.forma_pago = request.form.get('forma_pago')
        
        db.session.commit()
        flash('Egreso principal actualizado correctamente.', 'success')
    except Exception as e:
        db.session.rollback()
        print(f"Error al editar egreso principal: {e}")
        flash('Error al actualizar el egreso.', 'danger')
        
    return redirect(url_for('egreso_caja.index'))

@egreso_caja_bp.route('/oficina/egreso_caja/eliminar/<int:id>', methods=['POST'])
@login_required
@admin_oficina_required
def eliminar(id):
    egreso = EgresoCaja.query.get_or_404(id)
    try:
        db.session.delete(egreso)
        db.session.commit()
        flash('Egreso y todos sus desgloses eliminados exitosamente.', 'success')
    except Exception as e:
        db.session.rollback()
        print(f"Error al eliminar egreso principal: {e}")
        flash('Error al eliminar el egreso.', 'danger')
        
    return redirect(url_for('egreso_caja.index'))

@egreso_caja_bp.route('/oficina/egreso_caja/desglose/editar/<int:id>', methods=['POST'])
@login_required
@admin_oficina_required
def editar_desglose(id):
    desglose = EgresoCajaDesglose.query.get_or_404(id)
    try:
        desglose.concepto_gasto = request.form.get('concepto_gasto')
        desglose.monto = clean_amount(request.form.get('monto'))
        desglose.fecha_gasto = datetime.strptime(request.form.get('fecha_gasto'), '%Y-%m-%d').date()
        desglose.observacion = request.form.get('observacion')
        
        # Procesar nuevo archivo PDF si existe
        pdf_file = request.files.get('pdf_soporte')
        if pdf_file and pdf_file.filename != '':
            if not pdf_file.filename.lower().endswith('.pdf'):
                flash('El soporte debe ser un archivo PDF.', 'warning')
                return redirect(url_for('egreso_caja.index'))
            
            filename = secure_filename(f"egreso_{desglose.egreso_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf")
            upload_path = os.path.join(current_app.root_path, 'static', 'uploads', 'egresos')
            os.makedirs(upload_path, exist_ok=True)
            
            file_path = os.path.join(upload_path, filename)
            pdf_file.save(file_path)
            
            # Borrar el archivo viejo si se desea, pero por simplicidad solo actualizamos la url
            desglose.pdf_url = f"uploads/egresos/{filename}"
            
        db.session.commit()
        flash('Gasto desglosado actualizado correctamente.', 'success')
    except Exception as e:
        db.session.rollback()
        print(f"Error al editar desglose de egreso: {e}")
        flash('Error al actualizar el gasto.', 'danger')
        
    return redirect(url_for('egreso_caja.index'))

@egreso_caja_bp.route('/oficina/egreso_caja/desglose/eliminar/<int:id>', methods=['POST'])
@login_required
@admin_oficina_required
def eliminar_desglose(id):
    desglose = EgresoCajaDesglose.query.get_or_404(id)
    try:
        db.session.delete(desglose)
        db.session.commit()
        flash('Gasto desglosado eliminado exitosamente.', 'success')
    except Exception as e:
        db.session.rollback()
        print(f"Error al eliminar desglose de egreso: {e}")
        flash('Error al eliminar el gasto desglosado.', 'danger')
        
    return redirect(url_for('egreso_caja.index'))
