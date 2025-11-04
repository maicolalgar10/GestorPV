import traceback
from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import (
    db, Proyectos, Personal, Vehiculos, ProyectoPersonal,
    Asistencia, VehiculoProyecto, Materiales, MaterialesProyecto,
    Actividades, Avances, ProyectoUbicacion
)
from sqlalchemy import func
from datetime import datetime as dt



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

            # ✅ Validar que el responsable no esté en el personal adicional
            if str(responsable_id) in personal_ids:
                flash("⚠️ El responsable no puede estar también en el personal adicional.", "warning")
                return redirect(url_for('proyectos.manage_proyectos'))

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
            db.session.flush()  # obtener id antes del commit

            # ✅ Asignar personal
            for p_id in personal_ids:
                p_id_int = int(p_id)
                persona = Personal.query.get(p_id_int)
                if persona and persona.activo:
                    db.session.add(ProyectoPersonal(
                        proyecto_id=nuevo_proyecto.id_proyecto,
                        personal_id=p_id_int
                    ))
                # ✅ Asegurar que el responsable también quede registrado como personal asignado
                if not any(int(p_id) == responsable_id for p_id in personal_ids):
                   db.session.add(ProyectoPersonal(
                       proyecto_id=nuevo_proyecto.id_proyecto,
                       personal_id=responsable_id
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
    proyectos = Proyectos.query.all()
    personal = Personal.query.filter_by(activo=True).all()
    
    vehiculos = (
        Vehiculos.query
        .outerjoin(VehiculoProyecto)
        .filter(VehiculoProyecto.id_proyecto == None)
        .all()
    )
    vehiculos = (
        Vehiculos.query
        .filter(
            Vehiculos.estado != 'Mantenimiento',
            Vehiculos.soat_vencimiento >= hoy,
            Vehiculos.tecno_vencimiento >= hoy,
            ~Vehiculos.id_vehiculo.in_(
                db.session.query(VehiculoProyecto.id_vehiculo)
                .join(Proyectos)
                .filter(Proyectos.estado.in_(["EN_PROGRESO", "PENDIENTE"]))
            )
        )
        .all()
    )


    materiales = Materiales.query.all()

    proyectos_data = []

    for p in proyectos:
        # 👷‍♂️ Personal asignado: responsable + personal adicional
        ids_para_incluir = set()

        # Responsable
        if p.responsable_id:
            responsable = Personal.query.get(p.responsable_id)
            if responsable and responsable.activo:
                ids_para_incluir.add(responsable.id)

        # Personal adicional
        for rel in p.personal_asignado:
            if rel.personal and rel.personal.activo:
                ids_para_incluir.add(rel.personal.id)

        # Convertir a objetos
        asignados = []
        for pid in ids_para_incluir:
            persona = Personal.query.get(pid)
            if persona and persona.activo:
                asignados.append(persona)

        # 🕒 Calcular asistencias
        asistencias = (
            db.session.query(
                Asistencia.personal_id,
                func.count().label("total")
            )
            .filter(
                Asistencia.proyecto_id == p.id_proyecto,
                (Asistencia.trabajo_manana == True) | (Asistencia.trabajo_tarde == True)
            )
            .group_by(Asistencia.personal_id)
            .all()
        )
        asistencias_dict = {a.personal_id: a.total for a in asistencias}

        # 📆 Progreso estimado por fecha
        progreso = 0  # ← ¡Inicializa aquí!
        dias_atraso = 0
        estado_visual = "EN_PROGRESO"
        mensaje_estado = ""

        if p.fecha_inicio and p.fecha_fin:
            total_dias = (p.fecha_fin - p.fecha_inicio).days
            dias_transcurridos = (dt.utcnow().date() - p.fecha_inicio).days
            if total_dias > 0:
                progreso = min(100, max(0, int((dias_transcurridos / total_dias) * 100)))


        # Crear un diccionario de materiales asignados: {id_material: cantidad}
        materiales_asignados = {}
        for mp in p.materiales:
            materiales_asignados[mp.id_material] = mp.cantidad
        # 📊 Actividades con progreso
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

        hoy =dt.utcnow().date()
        actualizar_estado = False

        # =============================
        # 📅 Lógica de estado mejorada
        # =============================
        if total_actividades > 0:
            avance_real = round((completadas / total_actividades)*100,2)

            if completadas ==total_actividades:
                #Si esta completamente terminado
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
                    dias_atraso = diferencia
                    p.estado = "ATRASADO"
                    estado_visual = "ATRASADO"
                    mensaje_estado = f"🔴 Atrasado {dias_atraso} días — Avance {int(avance_real)}%"
                    actualizar_estado = True
                else:
                    dias_restantes = abs(diferencia)
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

        proyectos_data.append({
            "proyecto": p,
            "progreso": progreso,
            "estado_visual": estado_visual,
            "mensaje_estado": mensaje_estado,
            "dias_atraso": dias_atraso,
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
            "vehiculos": [  # 👈 AGREGA ESTO
                {
                    "id": v.vehiculo.id_vehiculo,
                    "placa": v.vehiculo.placa,
                    "marca": v.vehiculo.marca or "Sin marca"
                }
                for v in p.vehiculos
            ],
            "actividades": actividades_data,
            "materiales_asignados": materiales_asignados  # ← nuevo

        })

    return render_template(
        'proyectos.html',
        proyectos_data=proyectos_data,
        personal=personal,
        vehiculos=vehiculos,
        materiales=materiales
    )



# ===============================================================
# 🗑️ Eliminar proyecto
# ===============================================================
@proyectos_bp.route('/proyectos/delete/<int:id_proyecto>', methods=['POST'])
def delete_proyecto(id_proyecto):
    proyecto = Proyectos.query.get(id_proyecto)
    if proyecto:
        db.session.delete(proyecto)
        db.session.commit()
        flash("Proyecto eliminado 🗑️", "success")
    else:
        flash("Proyecto no encontrado", "danger")
    return redirect(url_for("proyectos.manage_proyectos"))


# ===============================================================
# ✏️ Editar proyecto
# ===============================================================
@proyectos_bp.route('/proyectos/editar/<int:id_proyecto>', methods=['GET', 'POST'])
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
def asignar_personal(proyecto_id):
    personal_id = int(request.form['personal_id'])
    relacion = ProyectoPersonal(proyecto_id=proyecto_id, personal_id=personal_id)
    db.session.add(relacion)
    db.session.commit()
    flash("Personal asignado correctamente 👷", "success")
    return redirect(url_for("proyectos.manage_proyectos"))




@proyectos_bp.route("/proyectos/finalizados")
def proyectos_finalizados():
    proyectos = Proyectos.query.filter_by(estado="FINALIZADO").all()
    return render_template("proyectos_fin.html", proyectos=proyectos)

@proyectos_bp.route("/proyectos/progreso")
def proyectos_progreso():
    proyectos = Proyectos.query.filter_by(estado="EN_PROGRESO").all()
    return render_template("proyectos_pro.html", proyectos=proyectos)


# ===============================================================
# ✅ Finalizar proyecto
# ===============================================================
@proyectos_bp.route('/proyectos/finalizar/<int:id_proyecto>', methods=['POST'])
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
# 🚗 Actualizar vehículos de un proyecto (desde dashboard)
# ===============================================================
@proyectos_bp.route('/proyecto/<int:id_proyecto>/vehiculos', methods=['POST'])
def actualizar_vehiculos_proyecto(id_proyecto):
    proyecto = Proyectos.query.get_or_404(id_proyecto)
    
    try:
        # Borrar todos los registros actuales
        VehiculoProyecto.query.filter_by(id_proyecto=id_proyecto).delete()
        
        # Obtener los IDs seleccionados
        vehiculo_ids = request.form.getlist('vehiculo_id')
        
        # Asignar los nuevos
        for v_id in vehiculo_ids:
            v_id_int = int(v_id)
            vehiculo = Vehiculos.query.get(v_id_int)
            if vehiculo:
                db.session.add(VehiculoProyecto(
                    id_vehiculo=vehiculo.id_vehiculo,
                    id_proyecto=id_proyecto,
                    fecha=dt.utcnow().date()
                ))
        
        db.session.commit()
        flash("✅ Vehículos actualizados correctamente", "success")
        
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Error al actualizar los vehículos: {str(e)}", "danger")
    
    return redirect(url_for('proyectos.manage_proyectos'))