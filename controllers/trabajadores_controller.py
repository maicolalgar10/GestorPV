from flask import Blueprint, render_template, session, redirect, url_for, flash, request
from models import db, Usuarios, Tarjeta
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
