from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import db, Vehiculos, Proyectos, VehiculoProyecto
from datetime import datetime as dt, date
from decimal import Decimal

vehiculos_bp = Blueprint("vehiculos", __name__)

# 👉 Lista de vehículos
@vehiculos_bp.route("/vehiculos")
def manage_vehiculos():
    hoy = date.today()
    print("🔍 Conectado a:", db.engine.url)

    vehiculos = Vehiculos.query.all()
    print("🚗 Vehículos encontrados:", len(vehiculos))

    vehiculos_info = []

    for v in vehiculos:
        # 📅 Verificar si los documentos están al día
        v.documentos_al_dia = not (v.soat_vencimiento < hoy or v.tecno_vencimiento < hoy)

        # 🔗 Buscar la última asignación del vehículo
        uso = VehiculoProyecto.query.filter_by(id_vehiculo=v.id_vehiculo)\
            .order_by(VehiculoProyecto.id_vp.desc()).first()

        proyecto_nombre = None
        if uso:
            proyecto = Proyectos.query.filter_by(id_proyecto=uso.id_proyecto).first()
            proyecto_nombre = proyecto.nombre if proyecto else None

        vehiculos_info.append({
            "vehiculo": v,
            "proyecto": proyecto_nombre or "Sin asignar"
        })

    return render_template(
        "vehiculos.html",
        vehiculos_info=vehiculos_info,
        fecha_hoy=hoy
    )


# 👉 Crear nuevo vehículo
@vehiculos_bp.route('/vehiculos/nuevo', methods=['GET', 'POST'])
def nuevo_vehiculo():
    if request.method == 'POST':
        try:
            placa = request.form['placa']
            marca = request.form['marca']
            modelo = request.form['modelo']
            soat_vencimiento = dt.strptime(request.form['soat_vencimiento'], "%Y-%m-%d").date()
            tecno_vencimiento = dt.strptime(request.form['tecno_vencimiento'], "%Y-%m-%d").date()
            estado = request.form['estado']

            documentos_al_dia = not (soat_vencimiento < date.today() or tecno_vencimiento < date.today())

            nuevo = Vehiculos(
                placa=placa,
                marca=marca,
                modelo=modelo,
                soat_vencimiento=soat_vencimiento,
                tecno_vencimiento=tecno_vencimiento,
                estado=estado,
                documentos_al_dia=documentos_al_dia
            )

            db.session.add(nuevo)
            db.session.commit()
            flash("🚗 Vehículo agregado correctamente", "success")
            return redirect(url_for("vehiculos.manage_vehiculos"))

        except Exception as e:
            db.session.rollback()
            flash(f"❌ Error al agregar el vehículo: {str(e)}", "danger")
            return redirect(url_for("vehiculos.manage_vehiculos"))

    return render_template(
        "nuevo_vehiculo.html",
        fecha_hoy=date.today()
    )


# 👉 Editar vehículo
@vehiculos_bp.route('/vehiculos/editar/<int:id>', methods=['GET', 'POST'])
def editar_vehiculo(id):
    vehiculo = Vehiculos.query.get_or_404(id)

    if request.method == 'POST':
        try:
            vehiculo.placa = request.form['placa']
            vehiculo.marca = request.form['marca']
            vehiculo.modelo = request.form['modelo']
            vehiculo.soat_vencimiento = dt.strptime(request.form['soat_vencimiento'], "%Y-%m-%d").date()
            vehiculo.tecno_vencimiento = dt.strptime(request.form['tecno_vencimiento'], "%Y-%m-%d").date()
            vehiculo.estado = request.form['estado']

            # Recalcular documentos al día
            vehiculo.documentos_al_dia = not (
                vehiculo.soat_vencimiento < date.today() or vehiculo.tecno_vencimiento < date.today()
            )

            db.session.commit()
            flash("✏️ Vehículo actualizado correctamente", "success")
            return redirect(url_for("vehiculos.manage_vehiculos"))

        except Exception as e:
            db.session.rollback()
            flash(f"❌ Error al actualizar el vehículo: {str(e)}", "danger")
            return redirect(url_for("vehiculos.manage_vehiculos"))

    return render_template(
        "editar_vehiculo.html",
        vehiculo=vehiculo,
        fecha_hoy=date.today()
    )


# 👉 Eliminar vehículo
@vehiculos_bp.route('/vehiculos/delete/<int:id>', methods=['POST'])
def delete_vehiculo(id):
    vehiculo = Vehiculos.query.get_or_404(id)
    try:
        db.session.delete(vehiculo)
        db.session.commit()
        flash("✅ Vehículo eliminado correctamente", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Error al eliminar el vehículo: {str(e)}", "danger")
    return redirect(url_for("vehiculos.manage_vehiculos"))
