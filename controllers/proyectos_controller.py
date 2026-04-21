import traceback
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models import (
    db, Proyectos, Personal, Vehiculos, ProyectoPersonal,
    Asistencia, VehiculoProyecto, Materiales, MaterialesProyecto,
    Actividades, Avances, ProyectoUbicacion, MovimientoVehiculo,
    HistorialMateriales
)
from sqlalchemy import func, and_, or_
from sqlalchemy.orm import selectinload

from datetime import datetime as dt
from decorators import login_required, admin_required, admin_oficina_required
from flask import  request



proyectos_bp = Blueprint("proyectos", __name__)

# Mapeo de estados del formulario a la BD
MAPA_ESTADOS = {
    "Iniciado": "EN_PROGRESO",
    "Finalizado": "FINALIZADO",
    "Pendiente": "PENDIENTE"
}


def obtener_progreso_operativo(id_actividad):
    actividad = Actividades.query.get(id_actividad)
    if not actividad or not actividad.unidades_totales:
        return 0, 0, 0

    total = actividad.unidades_totales
    avanzado = (
        db.session.query(func.sum(Avances.unidades_avanzadas))
        .filter_by(id_actividad=id_actividad)
        .scalar()
    ) or 0
    porcentaje = int((avanzado / total) * 100) if total else 0
    return porcentaje, avanzado, total


# ===============================================================
#  LISTAR Y CREAR PROYECTOS
# ===============================================================
@proyectos_bp.route('/proyectos', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_proyectos():
    hoy = dt.utcnow().date()
    if request.method == 'POST':
        try:
            nombre = request.form['nombre']
            lugar = request.form['lugar']
            responsable_id = int(request.form['responsable_id'])
            descripcion = request.form.get('descripcion')
            fecha_inicio = dt.strptime(request.form['fecha_inicio'], "%Y-%m-%d").date()
            fecha_fin = dt.strptime(request.form['fecha_fin'], "%Y-%m-%d").date()

            estado_form = request.form['estado']
            estado = MAPA_ESTADOS.get(estado_form, "PENDIENTE")

            #  Validar responsable
            responsable = Personal.query.get(responsable_id)
            if not responsable or not responsable.activo:
                flash("El responsable seleccionado no está activo o no existe", "warning")
                return redirect(url_for('proyectos.manage_proyectos'))

            #  Obtener personal adicional
            personal_ids = request.form.getlist('personal_id')  # ← definido aquí

            # ✅ Validar responsable
            responsable = Personal.query.get(responsable_id)
            if not responsable or not responsable.activo:
                flash("El responsable seleccionado no está activo o no existe", "warning")
                return redirect(url_for('proyectos.manage_proyectos'))

            # 1. Obtener lista del formulario
            personal_ids = request.form.getlist('personal_id')
            
            # 2. Crear un conjunto (SET) para eliminar duplicados automáticamente
            #    y añadir al responsable obligatoriamente.
            todos_los_ids = set(pid for pid in personal_ids if pid.strip())
            todos_los_ids.add(str(responsable_id))

            #  Crear nuevo proyecto
            nuevo_proyecto = Proyectos(
                nombre=nombre,
                lugar=lugar,
                responsable_id=responsable_id,
                descripcion=descripcion,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
                estado=estado
            )
            db.session.add(nuevo_proyecto)
            db.session.flush()  # Obtener ID antes del commit

            #  Asignar personal (Bucle único para todos)
            for p_id in todos_los_ids:
                persona = Personal.query.get(int(p_id))
                if persona and persona.activo:
                    db.session.add(ProyectoPersonal(
                        proyecto_id=nuevo_proyecto.id_proyecto,
                        personal_id=int(p_id)
                    ))

            #  Asignar vehículos
            vehiculo_ids = request.form.getlist('vehiculo_id')
            for v_id in vehiculo_ids:
                if v_id:
                    vehiculo = Vehiculos.query.get(int(v_id))
                    if vehiculo:
                        db.session.add(VehiculoProyecto(
                            id_vehiculo=vehiculo.id_vehiculo,
                            id_proyecto=nuevo_proyecto.id_proyecto,
                            fecha=dt.utcnow().date()
                        ))


            # Actualizar materiales
            if 'material_id' in request.form:
                # Luego, asignar los nuevos materiales
                materiales_ids = [mid for mid in request.form.getlist('material_id') if mid]
                for m_id in materiales_ids:
                    cantidad_str = request.form.get(f'cantidad_{m_id}')
                    if cantidad_str and cantidad_str.isdigit():
                        cantidad = int(cantidad_str)
                        material = Materiales.query.get(int(m_id))
                        if material and cantidad > 0:
                            if material.cantidad >= cantidad:
                                db.session.add(MaterialesProyecto(
                                    id_proyecto=nuevo_proyecto.id_proyecto,
                                    id_material=material.id_material,
                                    cantidad=cantidad
                                ))
                                material.cantidad -= cantidad
                            else:
                                flash(
                                    f"Stock insuficiente de {material.nombre} "
                                    f"(Disponible: {material.cantidad}, Solicitado: {cantidad})",
                                    "warning"
                                )

            db.session.commit()
            flash("Proyecto creado correctamente con asignaciones y materiales", "success")

        except Exception as e:
            db.session.rollback()
            print("⚠️ ERROR en creación de proyecto:", traceback.format_exc())
            flash(f"Error al crear el proyecto: {str(e)}", "danger")

        return redirect(url_for('proyectos.manage_proyectos'))

    # ===============================================================
    #  GET: Listado de proyectos
    # ===============================================================
    termino_busqueda = request.args.get('q', '').strip()

    # 1️⃣ CONSULTA ÓPTIMA CON JOIN PRECARGADOS
    query = Proyectos.query.options(
        selectinload(Proyectos.responsable),
        selectinload(Proyectos.personal_asignado).selectinload(ProyectoPersonal.personal)
    ).filter_by(visible=True) # ✅ FILTRAR SOLO PROYECTOS VISIBLES
    
    if termino_busqueda:
        query = query.filter(Proyectos.nombre.ilike(f'%{termino_busqueda}%'))
    
    page = request.args.get('page', 1, type=int)

    pagination = query.paginate(page=page, per_page=6, error_out=False)
    proyectos = pagination.items

    # 2️⃣ CARGA DE DATOS ADICIONALES (fuera del bucle)
    personal = Personal.query.filter_by(activo=True).all()
    vehiculos = Vehiculos.query.all()  # Puedes filtrar si es necesario
    materiales = Materiales.query.all()

    # 3️⃣ PRE-COMPUTAR DATOS DE ASISTENCIAS EN UNA SOLA CONSULTA
    asistencias_data = db.session.query(
        Asistencia.proyecto_id,
        Asistencia.personal_id,
        func.count().label("total")
    ).filter(
        (Asistencia.trabajo_manana == True) | (Asistencia.trabajo_tarde == True)
    ).group_by(Asistencia.proyecto_id, Asistencia.personal_id).all()
    
    # Convertir a diccionario para acceso rápido
    asistencias_dict = {}
    for row in asistencias_data:
        key = (row.proyecto_id, row.personal_id)
        asistencias_dict[key] = row.total

    # 4️⃣ PRE-COMPUTAR AVANCES DE ACTIVIDADES EN UNA SOLA CONSULTA
    avances_data = db.session.query(
        Avances.id_actividad,
        func.sum(Avances.unidades_avanzadas).label("avanzado")
    ).group_by(Avances.id_actividad).all()
    
    avances_dict = {row.id_actividad: row.avanzado or 0 for row in avances_data}

    # 5️⃣ PROCESAR PROYECTOS CON CÁLCULOS ÓPTIMOS
    proyectos_data = []
    for p in proyectos:
        # Personal asignado (sin consultas extra)
        personal_ids = {pp.personal.id for pp in p.personal_asignado if pp.personal and pp.personal.activo}
        if p.responsable and p.responsable.activo:
            personal_ids.add(p.responsable.id)
        
        personal_asignado = [p for p in personal if p.id in personal_ids and p.activo]
        
        # Calcular progreso de actividades
        total_actividades = len(p.actividades)
        completadas = 0
        actividades_data = []
        
        for act in p.actividades:
            total = act.unidades_totales or 0
            avanzado = avances_dict.get(act.id_actividad, 0)
            porcentaje = int((avanzado / total) * 100) if total > 0 else 0
            
            if porcentaje >= 100:
                completadas += 1
            
            actividades_data.append({
                "id": act.id_actividad,
                "nombre": act.nombre,
                "descripcion": act.descripcion,
                "unidades_totales": total,
                "avanzado": avanzado,
                "porcentaje": porcentaje
            })
        
        # Calcular progreso estimado por fecha
        progreso_fecha = 0
        if p.fecha_inicio and p.fecha_fin:
            total_dias = (p.fecha_fin - p.fecha_inicio).days
            dias_transcurridos = (hoy - p.fecha_inicio).days if hoy > p.fecha_inicio else 0
            if total_dias > 0:
                progreso_fecha = min(100, max(0, int((dias_transcurridos / total_dias) * 100)))

        # Calcular avance real por actividades
        avance_real = round((completadas / total_actividades) * 100, 2) if total_actividades > 0 else 0

        # Determinar estado visual
        estado_visual = "FINALIZADO" if avance_real >= 100 else "EN_PROGRESO"
        dias_atraso = 0
        dias_restantes = 0
        mensaje_estado = ""

        if avance_real >= 100:
            if not p.fecha_fin_real:
                p.fecha_fin_real = hoy
            p.estado = "FINALIZADO"
            estado_visual = "FINALIZADO"
            diferencia = (p.fecha_fin_real - p.fecha_fin).days
            if diferencia < 0:
                mensaje_estado = f"✅ Finalizado {abs(diferencia)} día{'s' if abs(diferencia) != 1 else ''} antes del tiempo"
            elif diferencia == 0:
                mensaje_estado = "✅ Finalizado justo a tiempo"
            else:
                mensaje_estado = f"✅ Finalizado con {diferencia} día{'s' if diferencia != 1 else ''} de retraso"
        else:
            diferencia = (hoy - p.fecha_fin).days
            if diferencia > 0:
                dias_atraso = diferencia
                p.estado = "ATRASADO"
                estado_visual = "ATRASADO"
                mensaje_estado = f"🔴 Atrasado {dias_atraso} días — Avance {int(avance_real)}%"
            else:
                dias_restantes = abs(diferencia)
                p.estado = "EN_PROGRESO"
                estado_visual = "EN_PROGRESO"
                mensaje_estado = f"🟡 En progreso — faltan {dias_restantes} días — Avance {int(avance_real)}%"

        # Materiales y vehículos
        materiales_data = [
            {"id": m.material.id_material, "nombre": m.material.nombre, "cantidad": m.cantidad}
            for m in p.materiales
        ]
        
        vehiculos_data = [
            {"id": v.vehiculo.id_vehiculo, "placa": v.vehiculo.placa, "marca": v.vehiculo.marca or "Sin marca"}
            for v in p.vehiculos
        ]

        # Asistencias por trabajador
        trabajadores_data = [
            {
                "id": t.id,
                "nombre": t.nombre,
                "rol": t.rol,
                "asistencias": asistencias_dict.get((p.id_proyecto, t.id), 0)
            }
            for t in personal_asignado
        ]

        proyectos_data.append({
            "proyecto": p,
            "progreso": progreso_fecha,
            "personal_asignado": personal_asignado,
            "personal_asignado_ids": [t.id for t in personal_asignado],
            "estado_visual": estado_visual,
            "mensaje_estado": mensaje_estado,
            "dias_atraso": dias_atraso,
            "trabajadores": trabajadores_data,
            "materiales": materiales_data,
            "vehiculos": vehiculos_data,
            "actividades": actividades_data,
            "materiales_asignados": {m["id"]: m["cantidad"] for m in materiales_data}
        })

    # Separar proyectos
    proyectos_activos = [p for p in proyectos_data if p['estado_visual'] != 'FINALIZADO']
    proyectos_finalizados = [p for p in proyectos_data if p['estado_visual'] == 'FINALIZADO']

    # Guardar cambios si se actualizó el estado
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"⚠️ Error al guardar estados: {e}")

    return render_template(
        'proyectos.html',
        proyectos_activos=proyectos_activos,
        proyectos_finalizados=proyectos_finalizados,
        personal=personal,
        vehiculos=vehiculos,
        materiales=materiales,
        q=termino_busqueda,
        pagination=pagination
    )


# ===============================================================
#  OCULTAR PROYECTO (en lugar de eliminarlo)
# ===============================================================
@proyectos_bp.route('/proyectos/hide/<int:id_proyecto>', methods=['POST'])
@login_required
@admin_required
def hide_proyecto(id_proyecto):
    proyecto = Proyectos.query.get_or_404(id_proyecto)
    
    try:
        # Cambiar visibilidad en lugar de eliminar
        proyecto.visible = False
        db.session.commit()
        
        flash(f"Proyecto '{proyecto.nombre}' ocultado correctamente. Datos preservados para análisis.", "success")
        
    except Exception as e:
        db.session.rollback()
        flash(f"Error al ocultar el proyecto: {str(e)}", "danger")
    
    return redirect(url_for('proyectos.manage_proyectos'))


# ===============================================================
#  MOSTRAR PROYECTO (en caso de error)
# ===============================================================
@proyectos_bp.route('/proyectos/show/<int:id_proyecto>', methods=['POST'])
@login_required
@admin_required
def show_proyecto(id_proyecto):
    proyecto = Proyectos.query.get_or_404(id_proyecto)
    
    try:
        # Restaurar visibilidad
        proyecto.visible = True
        db.session.commit()
        
        flash(f"Proyecto '{proyecto.nombre}' restaurado correctamente.", "success")
        
    except Exception as e:
        db.session.rollback()
        flash(f"Error al restaurar el proyecto: {str(e)}", "danger")
    
    return redirect(url_for('proyectos.manage_proyectos'))


# ===============================================================
#  EDITAR PROYECTO
# ===============================================================
@proyectos_bp.route('/proyectos/editar/<int:id_proyecto>', methods=['GET', 'POST'])
@login_required
@admin_required
def editar_proyecto(id_proyecto):
    hoy = dt.utcnow().date()
    proyecto = Proyectos.query.get_or_404(id_proyecto)

    if request.method == 'POST':
        try:
            print("🔍 Formulario recibido:")
            print("Claves en request.form:", list(request.form.keys()))
            print("personal_id en form:", 'personal_id' in request.form)
            if 'personal_id' in request.form:
                print("Valores de personal_id:", request.form.getlist('personal_id'))
            else:
                print("⚠️ personal_id NO está en el formulario")
            print("="*50)

            proyecto.nombre = request.form['nombre']
            proyecto.lugar = request.form['lugar']
            proyecto.responsable_id = int(request.form['responsable_id'])
            proyecto.descripcion = request.form.get('descripcion')
            proyecto.fecha_inicio = dt.strptime(request.form['fecha_inicio'], "%Y-%m-%d").date()
            proyecto.fecha_fin = dt.strptime(request.form['fecha_fin'], "%Y-%m-%d").date()
            estado_form = request.form['estado']
            proyecto.estado = MAPA_ESTADOS.get(estado_form, "PENDIENTE")

            # Actualizar personal: solo si se enviaron datos
            if 'personal_id' in request.form:
                # 1. Obtener IDs del formulario
                personal_ids_form = request.form.getlist('personal_id')
                
                # 2. Convertir a enteros y filtrar vacíos
                personal_ids = {int(pid) for pid in personal_ids_form if pid.strip()}
                
                # 3. Asegurar que el responsable esté incluido
                personal_ids.add(proyecto.responsable_id)

                # 4. Eliminar relaciones actuales
                ProyectoPersonal.query.filter_by(proyecto_id=id_proyecto).delete()

                # 5. Agregar nuevas relaciones
                for p_id in personal_ids:
                    persona = Personal.query.get(p_id)
                    if persona and persona.activo:
                        relacion = ProyectoPersonal(
                            proyecto_id=id_proyecto,
                            personal_id=p_id
                        )
                        db.session.add(relacion)

            # Actualizar vehículos
            if 'vehiculo_id' in request.form:
                vehiculo_ids_form = request.form.getlist('vehiculo_id')
                vehiculo_ids = {int(vid) for vid in vehiculo_ids_form if vid.strip()}

                # Eliminar relaciones actuales
                VehiculoProyecto.query.filter_by(id_proyecto=id_proyecto).delete()

                # Agregar nuevas relaciones
                for v_id in vehiculo_ids:
                    vehiculo = Vehiculos.query.get(v_id)
                    if vehiculo:
                        relacion = VehiculoProyecto(
                            id_proyecto=id_proyecto,
                            id_vehiculo=v_id,
                            fecha=dt.utcnow().date()
                        )
                        db.session.add(relacion)

            # ================================
            # ACTUALIZAR MATERIALES (SOLO ASIGNACIÓN)
            # ================================
            if 'material_id' in request.form:
                materiales_ids = [mid for mid in request.form.getlist('material_id') if mid]
                for m_id in materiales_ids:
                    cantidad_str = request.form.get(f'cantidad_{m_id}')
                    
                    if cantidad_str and cantidad_str.isdigit():
                        cantidad = int(cantidad_str)
                        material = Materiales.query.get(int(m_id))
                        
                        # Ya no validamos stock (material.cantidad) ni restamos nada.
                        # Simplemente registramos que este proyecto usará X cantidad.
                        if material and cantidad > 0:
                            db.session.add(MaterialesProyecto(
                                id_proyecto=proyecto.id_proyecto,
                                id_material=material.id_material,
                                cantidad=cantidad
                            ))

            db.session.commit()
            flash("Proyecto actualizado correctamente", "success")
            return redirect(url_for('proyectos.manage_proyectos'))

        except Exception as e:
            db.session.rollback()
            flash(f"Error al actualizar el proyecto: {str(e)}", "danger")

    # Cargar personal activo
    personal = Personal.query.filter_by(activo=True).all()

    # Vehículos: asignados al proyecto actual + disponibles (no asignados a ningún otro proyecto)
    vehiculos_asignados = [vp.vehiculo for vp in proyecto.vehiculos]
    vehiculos_disponibles = Vehiculos.query.filter(
        ~Vehiculos.id_vehiculo.in_([v.id_vehiculo for v in vehiculos_asignados])
    ).all()
    vehiculos = vehiculos_asignados + vehiculos_disponibles

    # Materiales: asignados al proyecto actual + disponibles
    materiales_asignados = [mp.material for mp in proyecto.materiales]
    materiales_disponibles = Materiales.query.filter(
        ~Materiales.id_material.in_([m.id_material for m in materiales_asignados])
    ).all()
    materiales = materiales_asignados + materiales_disponibles

    return render_template(
        'editar_proyecto.html',
        proyecto=proyecto,
        personal=personal,
        vehiculos=vehiculos,
        materiales=materiales
    )


# ===============================================================
#  AGREGAR MATERIAL AL PROYECTO (desde edición)
# ===============================================================
@proyectos_bp.route('/proyecto/<int:id_proyecto>/agregar_material', methods=['POST'])
@login_required
@admin_required
def agregar_material_proyecto(id_proyecto):
    try:
        id_material = int(request.form['id_material'])
        
        material = Materiales.query.get(id_material)
        if not material:
            flash("Material no encontrado.", "warning")
            return redirect(url_for('proyectos.editar_proyecto', id_proyecto=id_proyecto))

       
        # Crear asignación
        asignacion = MaterialesProyecto(
            id_proyecto=id_proyecto,
            id_material=id_material,
            estado="PENDIENTE"
        )
        db.session.add(asignacion)
        db.session.commit()
        flash("Material agregado al proyecto", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"Error: {str(e)}", "danger")
    
    return redirect(url_for('proyectos.editar_proyecto', id_proyecto=id_proyecto))


# ===============================================================
#  ELIMINAR MATERIAL DEL PROYECTO (desde edición)
# ===============================================================
@proyectos_bp.route('/proyecto/materiales/eliminar/<int:id_material_proyecto>', methods=['POST'])
@login_required
@admin_required
def eliminar_material_proyecto(id_material_proyecto):
    try:
        relacion = MaterialesProyecto.query.get_or_404(id_material_proyecto)
        # Guardamos el ID del proyecto antes de borrar la relación para el redirect
        id_proyecto_destino = relacion.id_proyecto
        
        # Simplemente eliminamos la relación, sin tocar material.cantidad
        db.session.delete(relacion)
        db.session.commit()
        
        flash("Material removido del proyecto", "success")
        return redirect(url_for('proyectos.editar_proyecto', id_proyecto=id_proyecto_destino))
        
    except Exception as e:
        db.session.rollback()
        flash(f"Error al eliminar material: {str(e)}", "danger")
        return redirect(url_for('proyectos.manage_proyectos'))

# ===============================================================
#  PROYECTOS FINALIZADOS
# ===============================================================
@proyectos_bp.route("/proyectos/finalizados")
@login_required
@admin_required
def proyectos_finalizados():
    proyectos = Proyectos.query.options(
        db.joinedload(Proyectos.responsable)
    ).filter_by(estado="FINALIZADO", visible=True).all()  #  FILTRAR VISIBLES
    return render_template("proyectos_fin.html", proyectos=proyectos)


# ===============================================================
#  PROYECTOS EN PROGRESO
# ===============================================================
@proyectos_bp.route("/proyectos/progreso")
@login_required
@admin_required
def proyectos_progreso():
    proyectos = Proyectos.query.options(
        db.joinedload(Proyectos.responsable)
    ).filter(Proyectos.estado != "FINALIZADO", Proyectos.visible == True).all()  #  FILTRAR VISIBLES
    return render_template("proyectos_pro.html", proyectos=proyectos)


# ===============================================================
#  FINALIZAR PROYECTO
# ===============================================================
@proyectos_bp.route('/proyectos/finalizar/<int:id_proyecto>', methods=['POST'])
@login_required
@admin_required
def finalizar_proyecto(id_proyecto):
    proyecto = Proyectos.query.get_or_404(id_proyecto)
    proyecto.estado = "FINALIZADO"
    db.session.commit()
    flash(f"El proyecto '{proyecto.nombre}' ha sido marcado como Finalizado", "success")
    return redirect(url_for('dashboard.dashboard'))


# ===============================================================
#  AGREGAR ACTIVIDAD A PROYECTO
# ===============================================================
@proyectos_bp.route('/proyecto/<int:id_proyecto>/agregar_actividad', methods=['POST'])
@login_required
@admin_required
def agregar_actividad(id_proyecto):
    try:
        nombre = request.form['nombre']
        descripcion = request.form.get('descripcion')
        unidades_totales = int(request.form.get('unidades_totales', 0))

        nueva_actividad = Actividades(
            id_proyecto=id_proyecto,
            nombre=nombre,
            descripcion=descripcion,
            unidades_totales=unidades_totales
        )
        db.session.add(nueva_actividad)
        db.session.commit()
        flash("Actividad agregada correctamente al proyecto", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"Error al crear la actividad: {str(e)}", "danger")
    
    return redirect(url_for('proyectos.manage_proyectos'))


# ===============================================================
#  AGREGAR UBICACIÓN A UN PROYECTO
# ===============================================================
@proyectos_bp.route('/proyecto/<int:id_proyecto>/agregar_ubicacion', methods=['POST'])
@login_required
@admin_required
def agregar_ubicacion(id_proyecto):
    try:
        nombre = request.form['nombre']
        direccion = request.form.get('direccion')
        fecha_inicio = dt.strptime(request.form['fecha_inicio'], "%Y-%m-%d").date()
        fecha_fin_str = request.form.get('fecha_fin')
        fecha_fin = dt.strptime(fecha_fin_str, "%Y-%m-%d").date() if fecha_fin_str else None
        estado = request.form.get('estado', 'Planeado')

        # Verificar si ya existe una ubicación con el mismo nombre en este proyecto
        existe = ProyectoUbicacion.query.filter_by(proyecto_id=id_proyecto, nombre=nombre).first()
        if existe:
            flash(f"Ya existe una ubicación con el nombre '{nombre}' para este proyecto.", "warning")
            return redirect(url_for('proyectos.manage_proyectos'))

        nueva_ubicacion = ProyectoUbicacion(
            proyecto_id=id_proyecto,
            nombre=nombre,
            direccion=direccion,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            estado=estado,
            progreso=0
        )
        db.session.add(nueva_ubicacion)
        db.session.commit()
        flash("Ubicación agregada correctamente al proyecto", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"Error al crear la ubicación: {str(e)}", "danger")
    
    return redirect(url_for('proyectos.manage_proyectos'))


# ===============================================================
#  EDITAR UBICACIÓN DE UN PROYECTO
# ===============================================================
@proyectos_bp.route('/proyecto/ubicacion/<int:id_ubicacion>/editar', methods=['POST'])
@login_required
@admin_required
def editar_ubicacion(id_ubicacion):
    ubicacion = ProyectoUbicacion.query.get_or_404(id_ubicacion)
    
    try:
        ubicacion.nombre = request.form['nombre']
        ubicacion.direccion = request.form.get('direccion')
        ubicacion.fecha_inicio = dt.strptime(request.form['fecha_inicio'], "%Y-%m-%d").date()
        fecha_fin_str = request.form.get('fecha_fin')
        ubicacion.fecha_fin = dt.strptime(fecha_fin_str, "%Y-%m-%d").date() if fecha_fin_str else None
        ubicacion.estado = request.form.get('estado', ubicacion.estado)
        ubicacion.progreso = int(request.form.get('progreso', ubicacion.progreso))

        db.session.commit()
        flash("Ubicación actualizada correctamente", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"Error al editar la ubicación: {str(e)}", "danger")
    
    return redirect(url_for('proyectos.manage_proyectos'))


# ===============================================================
#  ACTUALIZAR PERSONAL DE UN PROYECTO (desde dashboard)
# ===============================================================
@proyectos_bp.route('/proyecto/<int:id_proyecto>/personal', methods=['POST'])
@login_required
@admin_required
def actualizar_personal_proyecto(id_proyecto):
    proyecto = Proyectos.query.get_or_404(id_proyecto)
    
    try:
        # Borrar todos los registros actuales
        ProyectoPersonal.query.filter_by(proyecto_id=id_proyecto).delete()
        
        # Obtener los IDs seleccionados
        personal_ids = request.form.getlist('personal_id')

        # Asignar los nuevos (excluyendo al responsable si está marcado)
        for p_id in personal_ids:
            p_id_int = int(p_id)
            # Evitar duplicar al responsable
            if p_id_int == proyecto.responsable_id:
                continue
            persona = Personal.query.get(p_id_int)
            if persona and persona.activo:
                db.session.add(ProyectoPersonal(
                    proyecto_id=id_proyecto,
                    personal_id=p_id_int
                ))

        db.session.commit()
        flash("Personal actualizado correctamente", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"Error al actualizar el personal: {str(e)}", "danger")
    
    return redirect(url_for('proyectos.manage_proyectos'))


# ===============================================================
#  ACTUALIZAR VEHÍCULOS DE UN PROYECTO (desde dashboard)
# ===============================================================
@proyectos_bp.route('/proyecto/<int:id_proyecto>/vehiculos', methods=['POST'])
@login_required
@admin_required
def actualizar_vehiculos_proyecto(id_proyecto):
    proyecto = Proyectos.query.get_or_404(id_proyecto)
    
    try:
        # Borrar todos los registros actuales
        VehiculoProyecto.query.filter_by(id_proyecto=id_proyecto).delete()
        
        # Obtener los IDs seleccionados
        vehiculo_ids = request.form.getlist('vehiculo_id')

        # Asignar los nuevos
        for v_id in vehiculo_ids:
            vehiculo = Vehiculos.query.get(int(v_id))
            if vehiculo:
                # Registrar movimiento de salida si el vehículo estaba en otro proyecto
                if vehiculo.proyecto_actual_id:
                    movimiento_salida = MovimientoVehiculo(
                        id_vehiculo=vehiculo.id_vehiculo,
                        id_usuario=session.get('user_id'),
                        proyecto_anterior_id=vehiculo.proyecto_actual_id,
                        proyecto_nuevo_id=None,  # Sale del proyecto actual
                        ubicacion_anterior=vehiculo.ubicacion_actual,
                        ubicacion_nueva=None,  # Se desconoce
                        motivo=f"Removido del proyecto '{proyecto.nombre}' desde la gestión de proyectos."
                    )
                    db.session.add(movimiento_salida)
                
                # Asociar vehículo al nuevo proyecto
                relacion = VehiculoProyecto(
                    id_vehiculo=vehiculo.id_vehiculo,
                    id_proyecto=id_proyecto,
                    fecha=dt.utcnow().date()
                )
                db.session.add(relacion)

                # Actualizar asignación actual del vehículo
                vehiculo.proyecto_actual_id = id_proyecto
                vehiculo.updated_at = dt.utcnow()

        db.session.commit()
        flash("Vehículos actualizados correctamente. Movimientos registrados.", "success")

    except Exception as e:
        db.session.rollback()
        print(f"❌ Error al actualizar los vehículos del proyecto: {str(e)}")
        flash(f"Error al actualizar los vehículos: {str(e)}", "danger")
    
    return redirect(url_for('proyectos.manage_proyectos'))


# ===============================================================
#  ACTUALIZAR MATERIALES DE UN PROYECTO (desde dashboard)
# ===============================================================
@proyectos_bp.route('/proyecto/<int:id_proyecto>/materiales', methods=['POST'])
@login_required
@admin_required
def actualizar_materiales_proyecto(id_proyecto):
    proyecto = Proyectos.query.get_or_404(id_proyecto)
    
    try:
        # 1. Eliminar las asignaciones anteriores (sin devolver stock)
        materiales_actuales = MaterialesProyecto.query.filter_by(id_proyecto=id_proyecto).all()
        for mp in materiales_actuales:
            db.session.delete(mp)

        # 2. Asignar los nuevos materiales seleccionados
        if 'material_id' in request.form:
            materiales_ids = [mid for mid in request.form.getlist('material_id') if mid]
            for m_id in materiales_ids:
                cantidad_str = request.form.get(f'cantidad_{m_id}')
                
                if cantidad_str and cantidad_str.isdigit():
                    cantidad = int(cantidad_str)
                    material = Materiales.query.get(int(m_id))
                    
                    # Solo verificamos que el material exista y la cantidad sea válida
                    if material and cantidad > 0:
                        db.session.add(MaterialesProyecto(
                            id_proyecto=id_proyecto,
                            id_material=material.id_material,
                            cantidad=cantidad
                        ))

        db.session.commit()
        flash("Materiales del proyecto actualizados correctamente", "success")

    except Exception as e:
        db.session.rollback()
        print("⚠️ ERROR al actualizar materiales:", traceback.format_exc())
        flash(f"Error al actualizar materiales: {str(e)}", "danger")
    
    return redirect(url_for('proyectos.manage_proyectos'))


@proyectos_bp.route("/marcar_facturado/<int:id_proyecto>", methods=["POST"])
@login_required
@admin_oficina_required
def marcar_facturado(id_proyecto):

    proyecto = Proyectos.query.get_or_404(id_proyecto)
    
    proyecto.facturado = True
    proyecto.visible = False  # <--- Esto hace que desaparezca de la vista de trabajadores
    
    db.session.commit()
    flash(f"El proyecto {proyecto.nombre} ha sido facturado y archivado.", "success")
    return redirect(url_for("dashboard.dashboard_oficina"))



@proyectos_bp.route('/actualizar_estado_factura/<int:id_proyecto>', methods=['POST'])
@login_required
def actualizar_estado_factura(id_proyecto):
    nuevo_estado = request.form.get('nuevo_estado')
    proyecto = Proyectos.query.get_or_404(id_proyecto)
    
    # Actualizamos el estado
    proyecto.estado_factura = nuevo_estado
    
    # Si se marca como facturado, podrías querer archivarlo o mantenerlo visible
    if nuevo_estado == 'facturado':
        # proyecto.visible = False # Opcional: ocultarlo si ya se cobró
        pass
        
    db.session.commit()
    flash(f"Estado de {proyecto.nombre} actualizado a {nuevo_estado.upper()}", "success")
    return redirect(url_for('dashboard.dashboard_oficina'))
