from flask import Blueprint, request, redirect, url_for, flash
from models import db, Actividades
from models import db, Actividades, Avances  # solo si usas cálculo de progreso

actividades_bp = Blueprint('actividades', __name__)

# ===============================================================
# ➕ CREAR ACTIVIDAD (con o sin ubicación)
# ===============================================================
@actividades_bp.route('/crear', methods=['POST'])
def agregar_actividad():
    try:
        nombre = request.form['nombre'].strip()
        descripcion = request.form.get('descripcion')
        unidades_totales = int(request.form.get('unidades_totaleas', 0))
        proyecto_id = request.form.get('proyecto_id')
        ubicacion_id = request.form.get('ubicacion_id')  # opcional

        actividad = Actividades(
            nombre=nombre,
            descripcion=descripcion,
            unidades_totales=unidades_totales,
            id_proyecto=proyecto_id,
            id_ubicacion=int(ubicacion_id) if ubicacion_id else None
        )

        db.session.add(actividad)
        db.session.commit()

        flash('✅ Actividad creada exitosamente', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'❌ Error al crear la actividad: {str(e)}', 'danger')

    return redirect(url_for('proyectos.manage_proyectos'))


# ===============================================================
# ✏️ EDITAR ACTIVIDAD
# ===============================================================
@actividades_bp.route('/editar/<int:id_actividad>', methods=['POST'])
def editar_actividad(id_actividad):
    actividad = Actividades.query.get_or_404(id_actividad)
    try:
        actividad.nombre = request.form['nombre'].strip()
        actividad.descripcion = request.form.get('descripcion')
        actividad.unidades_totales = int(request.form.get('unidades_totales', 0))
        db.session.commit()
        flash("✅ Actividad actualizada correctamente", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Error al actualizar la actividad: {str(e)}", "danger")

    return redirect(url_for('proyectos.manage_proyectos'))


# ===============================================================
# 🗑️ ELIMINAR ACTIVIDAD
# ===============================================================
@actividades_bp.route('/eliminar/<int:id_actividad>', methods=['POST'])
def eliminar_actividad(id_actividad):
    actividad = Actividades.query.get(id_actividad)
    if not actividad:
        flash("⚠️ Actividad no encontrada", "warning")
        return redirect(url_for('proyectos.manage_proyectos'))

    try:
        db.session.delete(actividad)
        db.session.commit()
        flash("🗑️ Actividad eliminada correctamente", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Error al eliminar la actividad: {str(e)}", "danger")

    return redirect(url_for('proyectos.manage_proyectos'))
