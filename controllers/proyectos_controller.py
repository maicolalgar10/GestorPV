import traceback
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models import (
    db, Proyectos, Personal, Vehiculos, ProyectoPersonal,
    Asistencia, VehiculoProyecto, Materiales, MaterialesProyecto,
    Actividades, Avances, ProyectoUbicacion, MovimientoVehiculo
)
from sqlalchemy import func
from datetime import datetime as dt
from decorators import login_required, admin_required



proyectos_bp = Blueprint("proyectos", __name__)

# 🔄 Mapeo de estados del formulario a la BD
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
# ➕ Agregar material al proyecto (desde edición)
# ===============================================================
@proyectos_bp.route('/proyecto/<int:id_proyecto>/agregar_material', methods=['POST'])
@login_required
@admin_required
def agregar_material_proyecto(id_proyecto):
    try:
        id_material = int(request.form['id_material'])
        cantidad = int(request.form['cantidad'])

        material = Materiales.query.get(id_material)
        if not material:
            flash("⚠️ Material no encontrado.", "warning")
            return redirect(url_for('proyectos.editar_proyecto', id_proyecto=id_proyecto))

        if material.cantidad < cantidad:
            flash(f"⚠️ Stock insuficiente de {material.nombre}. Disponible: {material.cantidad}", "warning")
            return redirect(url_for('proyectos.editar_proyecto', id_proyecto=id_proyecto))

        # Crear asignación
        asignacion = MaterialesProyecto(
            id_proyecto=id_proyecto,
            id_material=id_material,
            cantidad=cantidad,
            estado="PENDIENTE"
        )

        material.cantidad -= cantidad
        db.session.add(asignacion)
        db.session.commit()
        flash("✅ Material agregado al proyecto", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"❌ Error: {str(e)}", "danger")

    return redirect(url_for('proyectos.editar_proyecto', id_proyecto=id_proyecto))


# ===============================================================
# 🗑️ Eliminar material del proyecto (desde edición)
# ===============================================================
@proyectos_bp.route('/proyecto/materiales/eliminar/<int:id_material_proyecto>', methods=['POST'])
@login_required
@admin_required
def eliminar_material_proyecto(id_material_proyecto):
    asignacion = MaterialesProyecto.query.get_or_404(id_material_proyecto)
    try:
        material = Materiales.query.get(asignacion.id_material)
        if material:
            material.cantidad += asignacion.cantidad

        db.session.delete(asignacion)
        db.session.commit()
        flash("🗑️ Material eliminado del proyecto", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Error: {str(e)}", "danger")

    return redirect(url_for('proyectos.editar_proyecto', id_proyecto=asignacion.id_proyecto))




# ===============================================================
# 📍 LISTAR Y CREAR PROYECTOS
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

            # ✅ Validar responsable
            responsable = Personal.query.get(responsable_id)
            if not responsable or not responsable.activo:
                flash("⚠️ El responsable seleccionado no está activo o no existe", "warning")
                return redirect(url_for('proyectos.manage_proyectos'))

            # ✅ Obtener personal adicional
            personal_ids = request.form.getlist('personal_id')  # ← definido aquí

            # ✅ Validar responsable
            responsable = Personal.query.get(responsable_id)
            if not responsable or not responsable.activo:
                flash("⚠️ El responsable seleccionado no está activo o no existe", "warning")
                return redirect(url_for('proyectos.manage_proyectos'))

            # 1. Obtener lista del formulario
            personal_ids = request.form.getlist('personal_id')
            
            # 2. Crear un conjunto (SET) para eliminar duplicados automáticamente
            #    y añadir al responsable obligatoriamente.
            todos_los_ids = set(pid for pid in personal_ids if pid.strip())
            todos_los_ids.add(str(responsable_id))

            # ✅ Crear nuevo proyecto
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

            # ✅ Asignar personal (Bucle único para todos)
            for p_id in todos_los_ids:
                persona = Personal.query.get(int(p_id))
                if persona and persona.activo:
                    db.session.add(ProyectoPersonal(
                        proyecto_id=nuevo_proyecto.id_proyecto,
                        personal_id=int(p_id)
                    ))

            # ✅ Asignar vehículos
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


            # 📦 Actualizar materiales
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
                                    f"⚠️ Stock insuficiente de {material.nombre} "
                                    f"(Disponible: {material.cantidad}, Solicitado: {cantidad})",
                                    "warning"
                                )

            db.session.commit()
            flash("✅ Proyecto creado correctamente con asignaciones y materiales", "success")

        except Exception as e:
            db.session.rollback()
            print("⚠️ ERROR en creación de proyecto:", traceback.format_exc())
            flash(f"❌ Error al crear el proyecto: {str(e)}", "danger")

        return redirect(url_for('proyectos.manage_proyectos'))

    # ===============================================================
    # 📋 GET: Listado de proyectos
    # ===============================================================
    termino_busqueda = request.args.get('q', '').strip()

    if termino_busqueda:
        proyectos = Proyectos.query.filter(Proyectos.nombre.ilike(f'%{termino_busqueda}%')).all()
    else:
        proyectos = Proyectos.query.all()

    personal = Personal.query.filter_by(activo=True).all()

    hoy_fecha = dt.today()
    vehiculos_disponibles = (
        Vehiculos.query
        .outerjoin(VehiculoProyecto)
        .filter(
            Vehiculos.estado != 'Mantenimiento',
            Vehiculos.soat_vencimiento >= hoy_fecha,
            Vehiculos.tecno_vencimiento >= hoy_fecha
        )
        .all()
    )
    vehiculos = vehiculos_disponibles

    materiales = Materiales.query.all()

    proyectos_data = []

    for p in proyectos:
        # ... (cálculo de personal asignado) ...
        ids_para_incluir = set()
        if p.responsable_id:
            responsable = Personal.query.get(p.responsable_id)
            if responsable and responsable.activo:
                ids_para_incluir.add(responsable.id)

        for rel in p.personal_asignado:
            if rel.personal and rel.personal.activo:
                ids_para_incluir.add(rel.personal.id)

        asignados = [Personal.query.get(pid) for pid in ids_para_incluir if Personal.query.get(pid) and Personal.query.get(pid).activo]
        personal_asignado_ids_para_template = [a.id for a in asignados]

        # ... (cálculo de asistencias) ...
        asistencias = (
            db.session.query(Asistencia.personal_id, func.count().label("total"))
            .filter(
                Asistencia.proyecto_id == p.id_proyecto,
                (Asistencia.trabajo_manana == True) | (Asistencia.trabajo_tarde == True)
            )
            .group_by(Asistencia.personal_id)
            .all()
        )
        asistencias_dict = {a.personal_id: a.total for a in asistencias}

        # ... (progreso estimado por fecha) ...
        progreso = 0
        if p.fecha_inicio and p.fecha_fin:
            total_dias = (p.fecha_fin - p.fecha_inicio).days
            dias_transcurridos = (dt.utcnow().date() - p.fecha_inicio).days
            if total_dias > 0:
                progreso = min(100, max(0, int((dias_transcurridos / total_dias) * 100)))

        # ... (materiales asignados) ...
        materiales_asignados = {}
        for mp in p.materiales:
            materiales_asignados[mp.id_material] = mp.cantidad

        # ... (actividades con progreso) ...
        actividades_data = []
        total_actividades = len(p.actividades)
        completadas = 0
        for act in p.actividades:
            total = act.unidades_totales or 0
            avanzado = (
                db.session.query(func.sum(Avances.unidades_avanzadas))
                .filter_by(id_actividad=act.id_actividad)
                .scalar()
            ) or 0
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

        hoy = dt.utcnow().date()
        actualizar_estado = False

        # =============================
        # 📅 Lógica de estado mejorada - CORREGIDA
        # =============================
        # ✅ Inicializar variables que se usan fuera del bloque if
        dias_atraso = 0
        dias_restantes = 0
        avance_real = 0

        if total_actividades > 0:
            avance_real = round((completadas / total_actividades) * 100, 2)

            if completadas == total_actividades:
                # Si esta completamente terminado
                if not p.fecha_fin_real:
                    p.fecha_fin_real = hoy
                p.estado = "FINALIZADO"
                estado_visual = "FINALIZADO"
                actualizar_estado = True

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
                    dias_atraso = diferencia # ✅ Definida aquí
                    p.estado = "ATRASADO"
                    estado_visual = "ATRASADO"
                    mensaje_estado = f"🔴 Atrasado {dias_atraso} días — Avance {int(avance_real)}%"
                    actualizar_estado = True
                else:
                    dias_restantes = abs(diferencia) # ✅ Definida aquí
                    p.estado = "EN_PROGRESO"
                    estado_visual = "EN_PROGRESO"
                    mensaje_estado = f"🟡 En progreso — faltan {dias_restantes} días — Avance {int(avance_real)}%"
                    actualizar_estado = True
        else:
            estado_visual = "PENDIENTE"
            mensaje_estado = "SIN ACTIVIDADES REGISTRADAS"
            p.estado = "PENDIENTE"
            actualizar_estado = True

        if actualizar_estado:
            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                print(f"⚠️ Error al actualizar estado del proyecto {p.nombre}: {e}")

        # ✅ Asegurarse de que 'estado_visual' y 'mensaje_estado' estén definidos
        # por si acaso la lógica anterior falla (aunque no debería)
        estado_visual = estado_visual if 'estado_visual' in locals() else "DESCONOCIDO"
        mensaje_estado = mensaje_estado if 'mensaje_estado' in locals() else "Estado no calculado"


        proyectos_data.append({
            "proyecto": p,
            "progreso": progreso,
            "personal_asignado": asignados,
            "personal_asignado_ids": personal_asignado_ids_para_template,
            "estado_visual": estado_visual, # ✅ Esta línea ahora debería funcionar
            "mensaje_estado": mensaje_estado, # ✅ Y esta también
            "dias_atraso": dias_atraso, # ✅ Ahora siempre está definida
            "trabajadores": [
                {
                    "id": t.id,
                    "nombre": t.nombre,
                    "rol": t.rol,
                    "asistencias": asistencias_dict.get(t.id, 0)
                }
                for t in asignados
            ],
            "materiales": [
                {
                    "id": m.material.id_material,
                    "nombre": m.material.nombre,
                    "cantidad": m.cantidad
                }
                for m in p.materiales
            ],
            "vehiculos": [
                {
                    "id": v.vehiculo.id_vehiculo,
                    "placa": v.vehiculo.placa,
                    "marca": v.vehiculo.marca or "Sin marca"
                }
                for v in p.vehiculos
            ],
            "actividades": actividades_data,
            "materiales_asignados": materiales_asignados
        })

    # ===============================================================
    # 🔁 SEPARAR PROYECTOS EN DOS LISTAS
    # ===============================================================
    proyectos_activos = []
    proyectos_finalizados = []

    for item in proyectos_data:
        # ✅ Ahora 'estado_visual' debería existir en 'item'
        if item['estado_visual'] == 'FINALIZADO':
            proyectos_finalizados.append(item)
        else:
            proyectos_activos.append(item)

    return render_template(
        'proyectos.html',
        proyectos_activos=proyectos_activos,
        proyectos_finalizados=proyectos_finalizados,
        personal=personal,
        vehiculos=vehiculos,
        materiales=materiales,
        q=termino_busqueda
    )



# ===============================================================
# 🗑️ Eliminar proyecto
# ===============================================================
@proyectos_bp.route('/proyectos/delete/<int:id_proyecto>', methods=['POST'])
@login_required
def delete_proyecto(id_proyecto):
    proyecto = Proyectos.query.get_or_404(id_proyecto)

    try:
        print(f"\n🗑️ Iniciando eliminación del proyecto '{proyecto.nombre}' (ID: {id_proyecto})")

        # 🔍 1. Buscar y eliminar movimientos relacionados (anterior y nuevo)
        movimientos_anteriores = MovimientoVehiculo.query.filter_by(proyecto_anterior_id=id_proyecto).all()
        movimientos_nuevos = MovimientoVehiculo.query.filter_by(proyecto_nuevo_id=id_proyecto).all()

        for mv in movimientos_anteriores + movimientos_nuevos:
            db.session.delete(mv)
            print(f"🗑️ Eliminado movimiento ID {mv.id_movimiento} relacionado con proyecto ID {id_proyecto}")

        # 🔍 2. Buscar vehículos que tenían este proyecto como su proyecto_actual y actualizarlos
        vehiculos_con_proyecto_actual = Vehiculos.query.filter_by(proyecto_actual_id=id_proyecto).all()
        for v in vehiculos_con_proyecto_actual:
            print(f"🔧 Actualizando vehículo '{v.placa}' (ID: {v.id_vehiculo}): proyecto_actual_id de {id_proyecto} a NULL")
            v.proyecto_actual_id = None
            # Opcional: v.ubicacion_actual = None
            v.updated_at = dt.utcnow()

        # 🔍 3. Buscar y eliminar relaciones Proyecto-Vehículo (VehiculoProyecto)
        relaciones_pv = VehiculoProyecto.query.filter_by(id_proyecto=id_proyecto).all() # ✅ CORRECTO: id_proyecto es el nombre en VehiculoProyecto
        for rpv in relaciones_pv:
            db.session.delete(rpv)
            print(f"🗑️ Eliminada relación VehiculoProyecto para vehículo ID {rpv.id_vehiculo} y proyecto ID {id_proyecto}")

        # 🔍 4. Buscar y eliminar relaciones Proyecto-Personal (ProyectoPersonal) - ✅ CORREGIDO
        relaciones_pp = ProyectoPersonal.query.filter_by(proyecto_id=id_proyecto).all() # 👈 CAMBIADO A 'proyecto_id'
        for rpp in relaciones_pp:
            db.session.delete(rpp)
            print(f"🗑️ Eliminada relación ProyectoPersonal para personal ID {rpp.personal_id} y proyecto ID {id_proyecto}")

        # 🔍 5. Buscar y eliminar relaciones Proyecto-Material (MaterialesProyecto)
        relaciones_pm = MaterialesProyecto.query.filter_by(id_proyecto=id_proyecto).all() # ✅ CORRECTO: id_proyecto es el nombre en MaterialesProyecto
        for rpm in relaciones_pm:
            # Opcional: Devolver el stock del material al inventario general
            material = Materiales.query.get(rpm.id_material)
            if material:
                material.cantidad += rpm.cantidad
            db.session.delete(rpm)
            print(f"🗑️ Eliminada relación MaterialesProyecto para material ID {rpm.id_material} y proyecto ID {id_proyecto}")

        # 🔍 6. Buscar y eliminar relaciones Proyecto-Ubicacion (ProyectoUbicacion)
        relaciones_pu = ProyectoUbicacion.query.filter_by(proyecto_id=id_proyecto).all() # ✅ CORRECTO: proyecto_id es el nombre en ProyectoUbicacion
        for rpu in relaciones_pu:
            db.session.delete(rpu)
            print(f"🗑️ Eliminada relación ProyectoUbicacion para ubicación ID {rpu.id} y proyecto ID {id_proyecto}")

        # 🔍 7. Buscar y eliminar relaciones Asistencia-Proyecto (si existe tal relación)
        # Asumiendo que Asistencia tiene un proyecto_id
        asistencias_del_proyecto = Asistencia.query.filter_by(proyecto_id=id_proyecto).all()
        for a in asistencias_del_proyecto:
            db.session.delete(a)
            print(f"🗑️ Eliminada relación Asistencia para personal ID {a.personal_id} en proyecto ID {id_proyecto}")

        # 🔍 8. Buscar y eliminar Actividades del Proyecto (y posiblemente Avances relacionados)
        actividades_del_proyecto = Actividades.query.filter_by(id_proyecto=id_proyecto).all()
        for act in actividades_del_proyecto:
            # Opcional: Eliminar también los avances de esta actividad si no se eliminan en cascada
            # Avances.query.filter_by(id_actividad=act.id_actividad).delete()
            db.session.delete(act)
            print(f"🗑️ Eliminada Actividad ID {act.id_actividad} del proyecto ID {id_proyecto}")

        # ✅ 9. Finalmente, eliminar el proyecto
        db.session.delete(proyecto)
        db.session.commit()
        flash(f"🗑️ Proyecto '{proyecto.nombre}' eliminado correctamente junto con sus relaciones.", "success")
        print(f"✅ Proyecto '{proyecto.nombre}' (ID: {id_proyecto}) eliminado exitosamente.")

    except Exception as e:
        db.session.rollback()
        print(f"❌ Error al eliminar el proyecto {proyecto.nombre} (ID: {id_proyecto}): {e}")
        flash(f"❌ Error al eliminar el proyecto: {str(e)}", "danger")

    return redirect(url_for('proyectos.manage_proyectos'))


# ===============================================================
# ✏️ Editar proyecto
# ===============================================================
@proyectos_bp.route('/proyectos/editar/<int:id_proyecto>', methods=['GET', 'POST'])
@login_required
@admin_required
def editar_proyecto(id_proyecto):
    hoy = dt.utcnow().date()
    
    proyecto = Proyectos.query.get_or_404(id_proyecto)

    if request.method == 'POST':
        try:

            print("\n🔍 Formulario recibido:")
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

            # 🔄 Actualizar personal: solo si se enviaron datos
            if 'personal_id' in request.form:                    
                flash(f"🔍 Personal IDs recibidos: {request.form.getlist('personal_id')}", "info")  # Para ver en la interfaz


                # 👇 Imprime en consola (log del servidor)
                print("\n" + "="*50)
                print("DEBUG: Editando proyecto ID =", id_proyecto)
                print("Personal IDs recibidos:", request.form.getlist('personal_id'))
                print("="*50)

                # Borrar solo si hay datos nuevos
                ProyectoPersonal.query.filter_by(proyecto_id=id_proyecto).delete()
                personal_ids = [pid for pid in request.form.getlist('personal_id') if pid.strip()]


                for p_id in personal_ids:
                    persona = Personal.query.get(int(p_id)) 
                    print(f"✅ Procesando trabajador ID: {p_id}")

                    if persona and persona.activo:
                        print(f"   ➤ Nombre: {persona.nombre}, Rol: {persona.rol or 'Sin rol'}")
                        db.session.add(ProyectoPersonal(
                            proyecto_id=proyecto.id_proyecto,
                            personal_id=int(p_id)
                        ))
                        
                # ✅ Asegurar que el responsable también quede en el personal asignado
                if str(proyecto.responsable_id) not in personal_ids:
                    db.session.add(ProyectoPersonal(
                        proyecto_id=proyecto.id_proyecto,
                        personal_id=proyecto.responsable_id
                    ))


            # 🔄 Actualizar vehículos: solo si se enviaron datos
            if 'vehiculo_id' in request.form:
                VehiculoProyecto.query.filter_by(id_proyecto=id_proyecto).delete()

                vehiculo_ids = request.form.getlist('vehiculo_id')
                for v_id in vehiculo_ids:
                    if v_id:
                        vehiculo = Vehiculos.query.get(int(v_id))
                        if vehiculo:
                            db.session.add(VehiculoProyecto(
                                id_vehiculo=vehiculo.id_vehiculo,
                                id_proyecto=proyecto.id_proyecto,
                                fecha=dt.utcnow().date()
                            ))

            # 📦 Actualizar materiales
            if 'material_id' in request.form:
                # Primero, devolver el stock de los materiales actuales
                materiales_actuales = MaterialesProyecto.query.filter_by(id_proyecto=proyecto.id_proyecto).all()
                for m_actual in materiales_actuales:
                    material = Materiales.query.get(m_actual.id_material)
                    if material:
                        material.cantidad += m_actual.cantidad
                    db.session.delete(m_actual)

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
                                    id_proyecto=proyecto.id_proyecto,
                                    id_material=material.id_material,
                                    cantidad=cantidad
                                ))
                                material.cantidad -= cantidad
                            else:
                                flash(
                                    f"⚠️ Stock insuficiente de {material.nombre} "
                                    f"(Disponible: {material.cantidad}, Solicitado: {cantidad})",
                                    "warning"
                                )
            db.session.commit()
            flash("✅ Proyecto actualizado correctamente", "success")
            return redirect(url_for('proyectos.manage_proyectos'))

        except Exception as e:
            db.session.rollback()
            flash(f"❌ Error al actualizar el proyecto: {str(e)}", "danger")

    # 👷‍♂️ Cargar personal activo
    personal = Personal.query.filter_by(activo=True).all()

    # 🚗 Vehículos: asignados al proyecto actual + disponibles (no asignados a ningún otro proyecto)
    vehiculos_asignados = [vp.vehiculo for vp in proyecto.vehiculos]
    vehiculos_disponibles = (
        Vehiculos.query
        .outerjoin(VehiculoProyecto)
        .filter(
            (VehiculoProyecto.id_proyecto.is_(None)),  # no asignados
            (Vehiculos.estado != 'Mantenimiento'),
            (Vehiculos.soat_vencimiento >= hoy),
            (Vehiculos.tecno_vencimiento >= hoy)
        )
        .all()
    ) 

    # 📦 Materiales: todos los materiales

    # Combinar sin duplicados (por si acaso)
    vehiculos_dict = {v.id_vehiculo: v for v in vehiculos_asignados + vehiculos_disponibles}
    vehiculos = list(vehiculos_dict.values())

    # IDs para pre-seleccionar en el formulario
    personal_asignado_ids = [pp.personal_id for pp in proyecto.personal_asignado]
    vehiculos_asignados_ids = [vp.id_vehiculo for vp in proyecto.vehiculos]



    # 📦 Materiales asignados
    materiales_asignados_dict = {}
    for mp in proyecto.materiales:
        materiales_asignados_dict[mp.id_material] = mp.cantidad    

    materiales = Materiales.query.all()
    materiales_asignados_ids = [mp.id_material for mp in proyecto.materiales]

    print("\n📋 Materiales asignados al proyecto ID", id_proyecto, ":")
    for m in proyecto.materiales:
        print(f"  - Material ID: {m.id_material}, Cantidad: {m.cantidad}")
    print("="*50)

    return render_template(
        "editar_proyecto.html",
        proyecto=proyecto,
        personal=personal,
        vehiculos=vehiculos,
        personal_asignado_ids=personal_asignado_ids,
        vehiculos_asignados_ids=vehiculos_asignados_ids,
        materiales_asignados_ids=materiales_asignados_ids,
        materiales_asignados_dict=materiales_asignados_dict
    )


# ===============================================================
# 👷 Asignar personal desde formulario
# ===============================================================
@proyectos_bp.route('/proyecto/<int:proyecto_id>/asignar_personal', methods=['POST'])
@login_required
@admin_required
def asignar_personal(proyecto_id):
    personal_id = int(request.form['personal_id'])
    relacion = ProyectoPersonal(proyecto_id=proyecto_id, personal_id=personal_id)
    db.session.add(relacion)
    db.session.commit()
    flash("Personal asignado correctamente 👷", "success")
    return redirect(url_for("proyectos.manage_proyectos"))




@proyectos_bp.route("/proyectos/finalizados")
@login_required
@admin_required
def proyectos_finalizados():
    proyectos = Proyectos.query.filter_by(estado="FINALIZADO").all()
    return render_template("proyectos_fin.html", proyectos=proyectos)

@proyectos_bp.route("/proyectos/progreso")
@login_required
@admin_required
def proyectos_progreso():
    proyectos = Proyectos.query.filter(Proyectos.estado != "FINALIZADO").all()
    return render_template("proyectos_pro.html", proyectos=proyectos)

# ===============================================================
# ✅ Finalizar proyecto
# ===============================================================
@proyectos_bp.route('/proyectos/finalizar/<int:id_proyecto>', methods=['POST'])
@login_required
@admin_required
def finalizar_proyecto(id_proyecto):
    proyecto = Proyectos.query.get_or_404(id_proyecto)
    proyecto.estado = "FINALIZADO"
    db.session.commit()
    flash(f"El proyecto '{proyecto.nombre}' ha sido marcado como Finalizado ✅", "success")
    return redirect(url_for('dashboard.dashboard'))



# ===============================================================
# AGREGAR ACTIVIDADEES A PROYECTO
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

        flash("✅ Actividad agregada correctamente al proyecto", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"❌ Error al crear la actividad: {str(e)}", "danger")

    return redirect(url_for('proyectos.manage_proyectos'))



# ===============================================================
# ➕ AGREGAR UBICACIÓN A UN PROYECTO
# ===============================================================
@proyectos_bp.route('/proyecto/<int:id_proyecto>/agregar_ubicacion', methods=['POST'])
@login_required
@admin_required
def agregar_ubicacion(id_proyecto):
    try:
        nombre = request.form['nombre'].strip()
        direccion = request.form.get('direccion')
        fecha_inicio = dt.strptime(request.form['fecha_inicio'], "%Y-%m-%d").date()
        fecha_fin_str = request.form.get('fecha_fin')
        fecha_fin = dt.strptime(fecha_fin_str, "%Y-%m-%d").date() if fecha_fin_str else None
        estado = request.form.get('estado', 'Planeado')

        # Validar duplicados (por nombre)
        existe = ProyectoUbicacion.query.filter_by(proyecto_id=id_proyecto, nombre=nombre).first()
        if existe:
            flash(f"⚠️ Ya existe una ubicación con el nombre '{nombre}' para este proyecto.", "warning")
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
        flash("✅ Ubicación agregada correctamente al proyecto", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"❌ Error al agregar la ubicación: {str(e)}", "danger")

    return redirect(url_for('proyectos.manage_proyectos'))

# ===============================================================
# ✏️ EDITAR UBICACIÓN
# ===============================================================
@proyectos_bp.route('/ubicacion/editar/<int:id_ubicacion>', methods=['POST'])
@login_required
@admin_required
def editar_ubicacion(id_ubicacion):
    ubicacion = ProyectoUbicacion.query.get_or_404(id_ubicacion)
    try:
        ubicacion.nombre = request.form['nombre'].strip()
        ubicacion.direccion = request.form.get('direccion')
        ubicacion.fecha_inicio = dt.strptime(request.form['fecha_inicio'], "%Y-%m-%d").date()
        fecha_fin_str = request.form.get('fecha_fin')
        ubicacion.fecha_fin = dt.strptime(fecha_fin_str, "%Y-%m-%d").date() if fecha_fin_str else None
        ubicacion.estado = request.form.get('estado', ubicacion.estado)
        ubicacion.progreso = int(request.form.get('progreso', ubicacion.progreso))

        db.session.commit()
        flash("✅ Ubicación actualizada correctamente", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Error al editar la ubicación: {str(e)}", "danger")

    return redirect(url_for('proyectos.manage_proyectos'))


# ===============================================================
# 🗑️ ELIMINAR UBICACIÓN
# ===============================================================
@proyectos_bp.route('/ubicacion/eliminar/<int:id_ubicacion>', methods=['POST'])
@login_required
@admin_required
def eliminar_ubicacion(id_ubicacion):
    ubicacion = ProyectoUbicacion.query.get(id_ubicacion)
    if not ubicacion:
        flash("⚠️ Ubicación no encontrada", "warning")
        return redirect(url_for('proyectos.manage_proyectos'))

    try:
        db.session.delete(ubicacion)
        db.session.commit()
        flash("🗑️ Ubicación eliminada correctamente", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Error al eliminar la ubicación: {str(e)}", "danger")

    return redirect(url_for('proyectos.manage_proyectos'))


def recalcular_progreso_ubicacion(id_ubicacion):
    
    ubicacion = ProyectoUbicacion.query.get(id_ubicacion)
    if not ubicacion:
        return

    actividades = ubicacion.actividades
    if not actividades:
        ubicacion.progreso = 0
    else:
        promedios = []
        for act in actividades:
            total = act.unidades_totales or 0
            avanzado = (
                db.session.query(func.sum(Avances.unidades_avanzadas))
                .filter_by(id_actividad=act.id_actividad)
                .scalar()
            ) or 0
            porcentaje = int((avanzado / total) * 100) if total else 0
            promedios.append(porcentaje)
        ubicacion.progreso = int(sum(promedios) / len(promedios)) if promedios else 0

    db.session.commit()


# ===============================================================
# 📦 Actualizar materiales de un proyecto
# ===============================================================
@proyectos_bp.route('/proyecto/<int:id_proyecto>/materiales', methods=['POST'])
@login_required
@admin_required
def actualizar_materiales_proyecto(id_proyecto):

    proyecto = Proyectos.query.get_or_404(id_proyecto)
    
    try:
        # 1. Devolver stock de materiales actuales
        materiales_actuales = MaterialesProyecto.query.filter_by(id_proyecto=id_proyecto).all()
        for mp in materiales_actuales:
            material = Materiales.query.get(mp.id_material)
            if material:
                material.cantidad += mp.cantidad
            db.session.delete(mp)
        
        # 2. Procesar nuevos materiales
        materiales_seleccionados = request.form.getlist('material_id')
        for id_material_str in materiales_seleccionados:
            id_material = int(id_material_str)
            cantidad_str = request.form.get(f'cantidad_{id_material}')
            
            if not cantidad_str or not cantidad_str.isdigit():
                continue
                
            cantidad = int(cantidad_str)
            if cantidad <= 0:
                continue
                
            material = Materiales.query.get(id_material)
            if not material:
                continue
                
            if material.cantidad < cantidad:
                flash(f"⚠️ Stock insuficiente de {material.nombre}. Disponible: {material.cantidad}", "warning")
                continue
                
            # Asignar material
            db.session.add(MaterialesProyecto(
                id_proyecto=id_proyecto,
                id_material=id_material,
                cantidad=cantidad
            ))
            material.cantidad -= cantidad
        
        db.session.commit()
        flash("✅ Materiales actualizados correctamente", "success")
        
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Error al actualizar materiales: {str(e)}", "danger")
    
    return redirect(url_for('proyectos.manage_proyectos'))


# ===============================================================
# 👷 Actualizar personal de un proyecto (desde dashboard)
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
        flash("✅ Personal actualizado correctamente", "success")
        
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Error al actualizar el personal: {str(e)}", "danger")
    
    return redirect(url_for('proyectos.manage_proyectos'))


# ===============================================================
# 🚗 Actualizar vehículos de un proyecto (desde dashboard/gestión proyectos)
# ===============================================================
# proyectos_controller.py
# proyectos_controller.py
@proyectos_bp.route('/proyecto/<int:id_proyecto>/vehiculos', methods=['POST'])
@admin_required # Aplica el decorador adecuado
def actualizar_vehiculos_proyecto(id_proyecto):
    proyecto = Proyectos.query.get_or_404(id_proyecto)

    try:
        # 1. Obtener los IDs seleccionados en el formulario
        vehiculo_ids_seleccionados = request.form.getlist('vehiculo_id')

        # 2. Obtener el estado actual de los vehículos involucrados ANTES de hacer cambios
        vehiculos_anteriores_relacion = VehiculoProyecto.query.filter_by(id_proyecto=id_proyecto).all()
        vehiculos_anteriores_ids = {vp.id_vehiculo for vp in vehiculos_anteriores_relacion}

        # 3. Borrar TODOS los registros actuales de vehículos para este proyecto
        VehiculoProyecto.query.filter_by(id_proyecto=id_proyecto).delete()

        # 4. Asignar los NUEVOS vehículos seleccionados
        for v_id_str in vehiculo_ids_seleccionados:
            if v_id_str: # Verifica que no sea una cadena vacía
                v_id_int = int(v_id_str)
                vehiculo = Vehiculos.query.get(v_id_int)
                if vehiculo:
                    # 🔍 BONUS: DESASIGNAR vehiculo de OTROS PROYECTOS ACTIVOS (OPCIONAL - según regla de negocio)
                    # Buscar si el vehículo está asignado a otro proyecto activo y eliminar esa relación
                    # Asumiendo que "activo" significa estado != "FINALIZADO"
                    relacion_otro_proyecto = VehiculoProyecto.query.join(Proyectos).filter(
                        VehiculoProyecto.id_vehiculo == v_id_int,
                        Proyectos.estado != "FINALIZADO",
                        Proyectos.id_proyecto != id_proyecto  # No eliminar la relación con el proyecto actual (que ya se borró)
                    ).first()

                    if relacion_otro_proyecto:
                        # Registrar movimiento de salida desde el otro proyecto
                        proyecto_anterior_otro = relacion_otro_proyecto.proyecto
                        proyecto_anterior_nombre_otro = proyecto_anterior_otro.nombre if proyecto_anterior_otro else 'Sin asignar'
                        ubicacion_anterior_para_registro_otro = proyecto_anterior_nombre_otro # Usamos el nombre del proyecto como ubicación

                        movimiento_salida_otro = MovimientoVehiculo(
                            id_vehiculo=vehiculo.id_vehiculo,
                            id_usuario=session.get('user_id'),
                            proyecto_anterior_id=proyecto_anterior_otro.id_proyecto if proyecto_anterior_otro else None,
                            proyecto_nuevo_id=None, # Sale del otro proyecto, no entra a ninguno todavía
                            ubicacion_anterior=ubicacion_anterior_para_registro_otro,
                            ubicacion_nueva='Sin asignar',
                            motivo=f"Removido del proyecto '{proyecto_anterior_nombre_otro}' para asignarlo al proyecto '{proyecto.nombre}'."
                        )
                        db.session.add(movimiento_salida_otro)
                        print(f"⚠️ Vehículo {vehiculo.placa} removido del proyecto '{proyecto_anterior_nombre_otro}' (antes de asignarlo a {proyecto.nombre}).")

                        # Eliminar la relación con el otro proyecto
                        db.session.delete(relacion_otro_proyecto)

                        # Opcional: Actualizar la asignación actual del vehículo si se borró de otro proyecto
                        # Esto es redundante si el bucle de abajo lo hace, pero es bueno para consistencia si el vehículo no se vuelve a asignar aquí
                        # vehiculo.proyecto_actual_id = id_proyecto # No aquí, sino después de la asignación definitiva


                    # Crear la nueva relación proyecto-vehículo
                    nueva_relacion = VehiculoProyecto(
                        id_vehiculo=vehiculo.id_vehiculo,
                        id_proyecto=id_proyecto,
                        fecha=dt.utcnow().date()
                    )
                    db.session.add(nueva_relacion)

                    # 5. Registrar el movimiento y actualizar asignación actual del vehículo
                    # Obtenemos el proyecto anterior (el que tenía asignado el vehículo antes de *este cambio específico*)
                    # Este valor es el del proyecto actual del vehículo ANTES de esta iteración del bucle
                    proyecto_anterior_id = vehiculo.proyecto_actual_id
                    proyecto_anterior_nombre = None
                    if vehiculo.proyecto_actual:
                         proyecto_anterior_nombre = vehiculo.proyecto_actual.nombre

                    ubicacion_anterior_para_registro = proyecto_anterior_nombre if proyecto_anterior_nombre else 'Sin asignar'
                    ubicacion_nueva_para_registro = proyecto.nombre

                    # Actualizar la asignación actual del vehículo
                    vehiculo.proyecto_actual_id = id_proyecto
                    vehiculo.updated_at = dt.utcnow()

                    # Crear el registro de movimiento
                    movimiento = MovimientoVehiculo(
                        id_vehiculo=vehiculo.id_vehiculo,
                        id_usuario=session.get('user_id'),
                        proyecto_anterior_id=proyecto_anterior_id,
                        proyecto_nuevo_id=id_proyecto,
                        ubicacion_anterior=ubicacion_anterior_para_registro,
                        ubicacion_nueva=ubicacion_nueva_para_registro,
                        motivo=f"Asignado al proyecto '{proyecto.nombre}' desde la gestión de proyectos."
                    )
                    db.session.add(movimiento)
                    print(f"✅ Movimiento registrado para {vehiculo.placa}: De '{ubicacion_anterior_para_registro}' a '{ubicacion_nueva_para_registro}'.")

        # 6. Identificar vehículos que fueron REMOVIDOS de este proyecto (como antes)
        vehiculos_removidos_ids = vehiculos_anteriores_ids - set(vehiculo_ids_seleccionados)
        for vid_removido in vehiculos_removidos_ids:
             vehiculo_removido = Vehiculos.query.get(vid_removido)
             if vehiculo_removido:
                 proyecto_anterior_id = vehiculo_removido.proyecto_actual_id
                 proyecto_anterior_nombre = None
                 if vehiculo_removido.proyecto_actual:
                     proyecto_anterior_nombre = vehiculo_removido.proyecto_actual.nombre

                 ubicacion_anterior_para_registro = proyecto_anterior_nombre if proyecto_anterior_nombre else 'Sin asignar'

                 movimiento_salida = MovimientoVehiculo(
                     id_vehiculo=vehiculo_removido.id_vehiculo,
                     id_usuario=session.get('user_id'),
                     proyecto_anterior_id=proyecto_anterior_id,
                     proyecto_nuevo_id=None,
                     ubicacion_anterior=ubicacion_anterior_para_registro,
                     ubicacion_nueva='Sin asignar',
                     motivo=f"Removido del proyecto '{proyecto.nombre}' desde la gestión de proyectos."
                 )
                 db.session.add(movimiento_salida)
                 print(f"✅ Movimiento de salida registrado para {vehiculo_removido.placa}: De '{ubicacion_anterior_para_registro}' a 'Sin asignar'.")
                 vehiculo_removido.proyecto_actual_id = None
                 vehiculo_removido.updated_at = dt.utcnow()

        db.session.commit()
        flash("✅ Vehículos actualizados correctamente. Movimientos registrados.", "success")

    except Exception as e:
        db.session.rollback()
        print(f"❌ Error al actualizar los vehículos del proyecto: {str(e)}")
        flash(f"❌ Error al actualizar los vehículos: {str(e)}", "danger")

    return redirect(url_for('proyectos.manage_proyectos'))