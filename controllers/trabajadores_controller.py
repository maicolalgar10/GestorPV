from flask import Blueprint, render_template, session, redirect, url_for, flash, request
from models import db, Usuarios, Tarjeta, ProgramacionPagoTarjeta
from datetime import datetime
from decorators import login_required, admin_oficina_required

trabajadores_bp = Blueprint("trabajadores", __name__)

@trabajadores_bp.route("/oficina/trabajadores")
@login_required
@admin_oficina_required
def index():
    usuario = Usuarios.query.get(session["user_id"])
    return render_template("trabajadores/index.html", usuario=usuario)

@trabajadores_bp.route("/oficina/trabajadores/nomina")
@login_required
@admin_oficina_required
def nomina():
    usuario = Usuarios.query.get(session["user_id"])
    empleados = Usuarios.query.filter_by(rol="EMPLEADO").all()
    return render_template("trabajadores/nomina.html", usuario=usuario, empleados=empleados)

@trabajadores_bp.route("/oficina/trabajadores/tarjetas")
@login_required
@admin_oficina_required
def tarjetas():
    usuario = Usuarios.query.get(session["user_id"])
    tarjetas_lista = Tarjeta.query.all()
    return render_template("trabajadores/tarjetas.html", usuario=usuario, tarjetas=tarjetas_lista)

@trabajadores_bp.route("/oficina/trabajadores/tarjetas/crear", methods=["POST"])
@login_required
@admin_oficina_required
def crear_tarjeta():
    try:
        nombre = request.form.get("nombre")
        numero = request.form.get("numero")
        
        if nombre and numero:
            nueva_tarjeta = Tarjeta(nombre=nombre, numero=numero)
            db.session.add(nueva_tarjeta)
            db.session.commit()
            flash("Tarjeta creada correctamente", "success")
        else:
            flash("Nombre y número son obligatorios", "warning")
            
    except Exception as e:
        db.session.rollback()
        flash(f"Error al crear la tarjeta: {str(e)}", "danger")
        
    return redirect(url_for("trabajadores.tarjetas"))

@trabajadores_bp.route("/oficina/trabajadores/tarjetas/programar-pago", methods=["POST"])
@login_required
@admin_oficina_required
def programar_pago_tarjeta():
    try:
        tarjeta_id = request.form.get("tarjeta_id")
        monto = request.form.get("monto")
        fecha_str = request.form.get("fecha_programada")
        concepto = request.form.get("concepto")
        cuenta_origen = request.form.get("cuenta_origen")
        
        if not (tarjeta_id and monto and fecha_str):
            flash("Todos los campos obligatorios deben ser completados.", "warning")
            return redirect(url_for("trabajadores.tarjetas"))
            
        fecha_prog = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        
        nuevo_pago = ProgramacionPagoTarjeta(
            tarjeta_id=int(tarjeta_id),
            monto=float(monto),
            fecha_programada=fecha_prog,
            concepto=concepto,
            cuenta_origen=cuenta_origen
        )
        
        db.session.add(nuevo_pago)
        db.session.commit()
        flash("Pago programado correctamente", "success")
        
    except Exception as e:
        db.session.rollback()
        flash(f"Error al programar el pago: {str(e)}", "danger")
        
    return redirect(url_for("trabajadores.tarjetas"))
