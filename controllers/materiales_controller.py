from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import db, Materiales, MaterialesProyecto, Proyectos
from datetime import datetime, date

materiales_bp = Blueprint("materiales", __name__)

# 👉 Listar materiales
@materiales_bp.route("/materiales")
def manage_materiales():
    materiales = Materiales.query.all()
    proyectos = Proyectos.query.all()
    asignaciones = MaterialesProyecto.query.all()

    return render_template(
        "materiales.html",
        materiales=materiales,
        proyectos=proyectos,
        asignaciones=asignaciones,
        fecha_hoy=date.today()
    )


# 👉 Crear nuevo material
@materiales_bp.route("/materiales/nuevo", methods=["GET", "POST"])
def nuevo_material():
    if request.method == "POST":
        try:
            nombre = request.form["nombre"]
            unidad = request.form["unidad"]
            cantidad = int(request.form.get("cantidad", 0))
            stock_minimo = int(request.form.get("stock_minimo", 0))

            nuevo = Materiales(
                nombre=nombre,
                unidad=unidad,
                cantidad=cantidad,
                stock_minimo=stock_minimo
            )
            db.session.add(nuevo)
            db.session.commit()
            flash("📦 Material agregado correctamente", "success")
            return redirect(url_for("materiales.manage_materiales"))

        except Exception as e:
            db.session.rollback()
            flash(f"❌ Error al agregar el material: {str(e)}", "danger")
            return redirect(url_for("materiales.manage_materiales"))

    return render_template("nuevo_material.html")


# 👉 Editar material
@materiales_bp.route("/materiales/editar/<int:id>", methods=["GET", "POST"])
def editar_material(id):
    material = Materiales.query.get_or_404(id)

    if request.method == "POST":
        try:
            material.nombre = request.form["nombre"]
            material.unidad = request.form["unidad"]
            material.cantidad = int(request.form.get("cantidad", material.cantidad))
            material.stock_minimo = int(request.form.get("stock_minimo", material.stock_minimo))

            db.session.commit()
            flash("✏️ Material actualizado correctamente", "success")
            return redirect(url_for("materiales.manage_materiales"))

        except Exception as e:
            db.session.rollback()
            flash(f"❌ Error al actualizar el material: {str(e)}", "danger")
            return redirect(url_for("materiales.manage_materiales"))

    return render_template("editar_material.html", material=material)


# 👉 Eliminar material
@materiales_bp.route("/materiales/delete/<int:id>", methods=["POST"])
def delete_material(id):
    material = Materiales.query.get_or_404(id)
    try:
        db.session.delete(material)
        db.session.commit()
        flash("✅ Material eliminado correctamente", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Error al eliminar el material: {str(e)}", "danger")
    return redirect(url_for("materiales.manage_materiales"))


# ----------------------------
# GESTIÓN DE MATERIALES-PROYECTO
# ----------------------------

# 👉 Asignar material a proyecto
@materiales_bp.route("/materiales/asignar", methods=["POST"])
def asignar_material():
    try:
        id_material = int(request.form["id_material"])
        id_proyecto = int(request.form["id_proyecto"])
        cantidad_asignada = int(request.form["cantidad"])
        estado = request.form.get("estado", "PENDIENTE")
        fecha_entrega = request.form.get("fecha_entrega")

        # Buscar material
        material = Materiales.query.get_or_404(id_material)

        # Verificar stock
        if material.cantidad < cantidad_asignada:
            flash(f"⚠️ No hay suficiente stock de {material.nombre}. Disponible: {material.cantidad}", "warning")
            return redirect(url_for("materiales.manage_materiales"))

        # Crear asignación
        asignacion = MaterialesProyecto(
            id_material=id_material,
            id_proyecto=id_proyecto,
            cantidad=cantidad_asignada,
            estado=estado,
            fecha_entrega=datetime.strptime(fecha_entrega, "%Y-%m-%d").date() if fecha_entrega else None,
        )

        # Descontar stock general
        material.cantidad -= cantidad_asignada

        db.session.add(asignacion)
        db.session.commit()
        flash("📌 Material asignado al proyecto correctamente", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"❌ Error al asignar material: {str(e)}", "danger")

    return redirect(url_for("materiales.manage_materiales"))


# 👉 Eliminar asignación de material a proyecto
@materiales_bp.route("/materiales/asignacion/delete/<int:id>", methods=["POST"])
def delete_asignacion(id):

    
    asignacion = MaterialesProyecto.query.get_or_404(id)
    try:
        # Devolver stock al eliminar asignación
        material = Materiales.query.get(asignacion.id_material)
        if material:
            material.cantidad += asignacion.cantidad

        db.session.delete(asignacion)
        db.session.commit()
        flash("🗑️ Asignación eliminada correctamente", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Error al eliminar asignación: {str(e)}", "danger")
    return redirect(url_for("materiales.manage_materiales"))



