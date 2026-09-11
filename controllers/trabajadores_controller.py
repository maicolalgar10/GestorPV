from flask import Blueprint, render_template, session, redirect, url_for, flash
from models import db, Usuarios
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
    empleados = Usuarios.query.filter_by(rol="EMPLEADO").all()
    return render_template("trabajadores/tarjetas.html", usuario=usuario, empleados=empleados)
