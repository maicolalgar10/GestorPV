from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from models import db, Materiales, MaterialesProyecto, Proyectos, SolicitudMateriales, Notificaciones, Usuarios, DetalleSolicitudMaterial
from datetime import datetime, date
from decorators import login_required, admin_required, admin_bodega_required
import os
from werkzeug.utils import secure_filename
from pathlib import Path
from sqlalchemy.exc import IntegrityError



materiales_bp = Blueprint("materiales", __name__)

# En materiales_controller.py (o en utils.py)
ALLOWED_EXTENSIONS = {'pdf', 'xlsx', 'xls', 'doc', 'docx', 'jpg', 'jpeg', 'png'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


#  Listar materiales
@materiales_bp.route("/materiales")
@login_required
@admin_required
def manage_materiales():
    materiales = Materiales.query.all()
    proyectos = Proyectos.query.filter_by(visible=True).all()    
    asignaciones = MaterialesProyecto.query.all()

    #  AÑADIR ESTA LÍNEA: Solicitudes recientes
    solicitudes = SolicitudMateriales.query.order_by(SolicitudMateriales.fecha_solicitud.desc()).limit(10).all()

    return render_template(
        "materiales.html",
        materiales=materiales,
        proyectos=proyectos,
        asignaciones=asignaciones,
        solicitudes=solicitudes,  #  PASAR SOLICITUDES A LA PLANTILLA
        fecha_hoy=date.today()
    )


#  Crear nuevo material
@materiales_bp.route("/materiales/nuevo", methods=["GET", "POST"])
@login_required
@admin_required
def nuevo_material():
    if request.method == "POST":
        try:
            nombre = request.form["nombre"]
            unidad = request.form["unidad"]

            nuevo = Materiales(
                nombre=nombre,
                unidad=unidad,
            )
            db.session.add(nuevo)
            db.session.commit()
            flash("Material agregado correctamente", "success")
            return redirect(url_for("materiales.manage_materiales"))

        except Exception as e:
            db.session.rollback()
            flash(f"Error al agregar el material: {str(e)}", "danger")
            return redirect(url_for("materiales.manage_materiales"))

    return render_template("materiales.manage_materiales")


#  Editar material
@materiales_bp.route("/materiales/editar/<int:id>", methods=["GET", "POST"])
@login_required
@admin_required
def editar_material(id):
    material = Materiales.query.get_or_404(id)

    if request.method == "POST":
        try:
            material.nombre = request.form["nombre"]
            material.unidad = request.form["unidad"]
            
            db.session.commit()
            flash("Material actualizado correctamente", "success")

        except Exception as e:
            db.session.rollback()
            flash(f"Error al actualizar el material: {str(e)}", "danger")

    return render_template("materiales.manage_materiales", material=material)


#  Eliminar material
@materiales_bp.route("/materiales/delete/<int:id>", methods=["POST"])
@login_required
@admin_required
def delete_material(id):
    material = Materiales.query.get_or_404(id)
    try:
        db.session.delete(material)
        db.session.commit()
        flash("Material eliminado correctamente", "success")
    
    except IntegrityError:
        # Este error ocurre cuando la base de datos bloquea el borrado por las FK
        db.session.rollback()
        flash("No se puede eliminar: este material ya tiene registros o historial en algunas solicitudes de bodega.", "warning")
        
    except Exception as e:
        # Para cualquier otro error inesperado
        db.session.rollback()
        flash(f"Error inesperado al eliminar el material: {str(e)}", "danger")

    return redirect(url_for("materiales.manage_materiales"))

# ----------------------------
# GESTIÓN DE MATERIALES-PROYECTO
# ----------------------------

#  Asignar material a proyecto
@materiales_bp.route("/materiales/asignar", methods=["POST"])
@login_required
@admin_required
def asignar_material():
    try:
        id_material = int(request.form["id_material"])
        id_proyecto = int(request.form["id_proyecto"])
        estado = request.form.get("estado", "PENDIENTE")
        fecha_entrega = request.form.get("fecha_entrega")

        
        # Crear asignación
        asignacion = MaterialesProyecto(
            id_material=id_material,
            id_proyecto=id_proyecto,
            estado=estado,
            fecha_entrega=datetime.strptime(fecha_entrega, "%Y-%m-%d").date() if fecha_entrega else None,
        )


        db.session.add(asignacion)
        db.session.commit()
        flash("Material asignado al proyecto correctamente", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"Error al asignar material: {str(e)}", "danger")

    return redirect(url_for("materiales.manage_materiales"))


#  Eliminar asignación de material a proyecto
@materiales_bp.route("/materiales/asignacion/delete/<int:id>", methods=["POST"])
@login_required
@admin_required
def delete_asignacion(id):

    
    asignacion = MaterialesProyecto.query.get_or_404(id)
    try:
        
        db.session.delete(asignacion)
        db.session.commit()
        flash("Asignación retirada del proyecto", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error al eliminar: {str(e)}", "danger")
    return redirect(url_for("materiales.manage_materiales"))



# Solicitud de materiales (RESPONSABLE → Bodega)
@materiales_bp.route('/solicitudes/crear', methods=['POST'])
@login_required
# Cambié admin_required por una validación más flexible si es necesario
def crear_solicitud():
    try:
        # 1. Obtener datos de la cabecera
        id_proyecto = request.form.get('proyecto_id')
        observaciones = request.form.get('observaciones', '').strip()
        
        # 2. Obtener listas dinámicas del formulario
        materiales_nombres = request.form.getlist('material_nombre[]')
        cantidades = request.form.getlist('cantidad[]')

        # --- VALIDACIÓN DE SEGURIDAD ---
        if not id_proyecto:
            flash("Debes seleccionar un proyecto de la lista.", "warning")
            return redirect(request.referrer) # Regresa a la página donde estaba

        # 3. Crear la cabecera de la solicitud
        nueva_solicitud = SolicitudMateriales(
            id_proyecto=id_proyecto,
            id_usuario_solicitante=session['user_id'],
            observaciones=observaciones,
            estado='PENDIENTE',  # Estado inicial explícito
            fecha_solicitud=datetime.now(),
            visible_para_bodega=True  # Aseguramos que bodega la vea de inmediato
        )
        
        db.session.add(nueva_solicitud)
        db.session.flush()  # Genera el ID para los detalles

        # 4. Procesar los materiales (Detalles)
        items_agregados = 0
        for nombre, cant in zip(materiales_nombres, cantidades):
            nombre = nombre.strip()
            if nombre and cant:
                try:
                    cantidad_valida = float(cant)
                    if cantidad_valida <= 0: continue
                    
                    detalle = DetalleSolicitudMaterial(
                        id_solicitud=nueva_solicitud.id_solicitud,
                        nombre_material_escrito=nombre, 
                        cantidad=cantidad_valida,
                        cantidad_entregada=0  # Inicialmente nada entregado
                    )
                    db.session.add(detalle)
                    items_agregados += 1
                except ValueError:
                    continue # Si la cantidad no es un número válido, saltar

        if items_agregados == 0:
            db.session.rollback()
            flash("Debes agregar al menos un material con cantidad válida.", "warning")
            return redirect(request.referrer)

        # 5. Manejo del Archivo Adjunto (PDF/Excel/Imagen)
        archivo = request.files.get('archivo')
        if archivo and archivo.filename != '':
            if allowed_file(archivo.filename): # Asegúrate de tener esta función definida
                filename = secure_filename(archivo.filename)
                unique_filename = f"SOL_{nueva_solicitud.id_solicitud}_{datetime.now().strftime('%H%M%S')}_{filename}"
                
                # Ruta: static/uploads/solicitudes/
                ruta_relativa = os.path.join("uploads", "solicitudes", unique_filename).replace("\\", "/")
                ruta_completa =     os.path.join(current_app.root_path, "static", ruta_relativa)
                
                os.makedirs(os.path.dirname(ruta_completa), exist_ok=True)
                archivo.save(ruta_completa)
                nueva_solicitud.archivo_ruta = ruta_relativa
            else:
                flash("El formato de archivo no es permitido.", "danger")

        db.session.commit()
        flash(f"Solicitud #{nueva_solicitud.id_solicitud} enviada a bodega correctamente.", "success")
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ ERROR en crear_solicitud: {str(e)}")
        flash("Hubo un error al procesar la solicitud. Revisa los datos.", "danger")

    # 6. Redirección inteligente
    # Si tienes el dashboard con pestañas, redirige ahí
    return redirect(url_for('dashboard.dashboard')) # O la ruta de tu pestaña principal




# En materiales_controller.py
@materiales_bp.route('/bodega/solicitudes/<int:id_solicitud>/en_proceso', methods=['POST'])
@login_required
@admin_bodega_required
def marcar_en_proceso(id_solicitud):
    try:
        solicitud = SolicitudMateriales.query.get_or_404(id_solicitud)
        solicitud.estado = 'EN_PROCESO'
        solicitud.id_usuario_responsable = session['user_id']
        solicitud.fecha_actualizacion = date.today()

        # Notificar al admin
        notificacion = Notificaciones(
            id_usuario_destino=solicitud.id_usuario_solicitante,
            mensaje=f" La solicitud #{solicitud.id_solicitud} fue marcada como 'En Proceso' por Bodega.",
            leido=False
        )
        db.session.add(notificacion)

        db.session.commit()
        flash("Solicitud marcada como 'En Proceso'", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"Error al marcar como 'En Proceso': {str(e)}", "danger")

    return redirect(url_for('materiales.solicitudes_bodega'))  # REDIRIGIR A LA MISMA PÁGINA


# Cambiar estado a COMPLETADO
@materiales_bp.route('/bodega/solicitudes/<int:id_solicitud>/completado', methods=['POST'])
@login_required
@admin_bodega_required
def marcar_completado(id_solicitud):
    try:
        solicitud = SolicitudMateriales.query.get_or_404(id_solicitud)
        solicitud.estado = 'COMPLETADO'
        solicitud.fecha_actualizacion = date.today()

        # Notificar al admin
        notificacion = Notificaciones(
            id_usuario_destino=solicitud.id_usuario_solicitante,
            mensaje=f"La solicitud #{solicitud.id_solicitud} fue marcada como 'Completada' por Bodega.",
            leido=False
        )
        db.session.add(notificacion)

        db.session.commit()
        flash("Solicitud marcada como 'Completada'", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"Error al marcar como 'Completada': {str(e)}", "danger")

    return redirect(url_for('materiales.solicitudes_bodega'))

# Cambiar estado a RECHAZADO
@materiales_bp.route('/bodega/solicitudes/<int:id_solicitud>/rechazado', methods=['POST'])
@login_required
@admin_bodega_required
def marcar_rechazado(id_solicitud):
    try:
        solicitud = SolicitudMateriales.query.get_or_404(id_solicitud)
        solicitud.estado = 'RECHAZADO'
        solicitud.fecha_actualizacion = date.today()

        # Notificar al admin
        notificacion = Notificaciones(
            id_usuario_destino=solicitud.id_usuario_solicitante,
            mensaje=f"La solicitud #{solicitud.id_solicitud} fue rechazada por Bodega.",
            leido=False
        )
        db.session.add(notificacion)

        db.session.commit()
        flash("Solicitud marcada como 'Rechazada'", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"Error al marcar como 'Rechazada': {str(e)}", "danger")

    return redirect(url_for('materiales.solicitudes_bodega'))


# Eliminar solicitud (solo para completadas o rechazadas)
@materiales_bp.route('/materiales/solicitudes/<int:id_solicitud>/ocultar', methods=['POST'])
@login_required
def ocultar_solicitud_trabajador(id_solicitud):
    try:
        solicitud = SolicitudMateriales.query.get_or_404(id_solicitud)
        
        # 1. SEGURIDAD: Solo el dueño de la solicitud puede ocultarla
        if solicitud.id_usuario_solicitante != session['user_id']:
            flash("No tienes permiso para modificar este registro.", "danger")
            return redirect(url_for('dashboard.dashboard_trabajador'))

        # 2. REGLA DE NEGOCIO: Solo permitir ocultar si ya terminó el proceso
        # (Así el trabajador no oculta algo que Bodega aún debe entregar)
        if solicitud.estado not in ['COMPLETADO', 'RECHAZADO']:
            flash(f"No puedes quitar solicitudes en estado: {solicitud.estado}", "warning")
            return redirect(url_for('dashboard.dashboard_trabajador'))

        # 3. LÓGICA PROFESIONAL: Marcamos como no visible para el trabajador
        # El registro sigue existiendo en la DB para el Bodeguero.
        solicitud.visible_para_trabajador = False 
        
        db.session.commit()
        flash("La solicitud se ha quitado de tu historial visual.", "success")

    except Exception as e:
        db.session.rollback()
        print(f"Error al ocultar solicitud: {str(e)}")
        flash("Ocurrió un error al intentar actualizar el historial.", "danger")

    return redirect(url_for('dashboard.dashboard_trabajador'))

# Ocultar solicitud para bodega (no eliminarla)
@materiales_bp.route('/bodega/solicitudes/<int:id_solicitud>/ocultar', methods=['POST'])
@login_required
@admin_bodega_required
def ocultar_solicitud_bodega(id_solicitud):
    try:
        solicitud = SolicitudMateriales.query.get_or_404(id_solicitud)
        solicitud.visible_para_bodega = False # Cambia solo esta solicitud
        db.session.commit()
        flash("Solicitud ocultada del historial", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error: {str(e)}", "danger")

    # REDIRIGE AL DASHBOARD REAL
    return redirect(url_for('dashboard.dashboard_bodega'))



# Dashboard de bodega (ver solicitudes por estado)
@materiales_bp.route('/bodega/solicitudes')
@login_required
@admin_bodega_required
def solicitudes_bodega():
    # FILTRAR POR VISIBILIDAD
    pendientes = SolicitudMateriales.query.filter_by(estado='PENDIENTE', visible_para_bodega=True).all()
    en_proceso = SolicitudMateriales.query.filter_by(estado='EN_PROCESO', visible_para_bodega=True).all()
    completados = SolicitudMateriales.query.filter_by(estado='COMPLETADO', visible_para_bodega=True).all()
    rechazados = SolicitudMateriales.query.filter_by(estado='RECHAZADO', visible_para_bodega=True).all()
    usuario = Usuarios.query.get(session['user_id'])

    return render_template(
        'dashboard_bodega.html',
        pendientes=pendientes,
        en_proceso=en_proceso,
        completados=completados,
        rechazados=rechazados,
        usuario=usuario
    )



# Es por si el pedido no esta completo
@materiales_bp.route('/solicitudes/procesar/<int:id_solicitud>', methods=['POST'])
@login_required
@admin_bodega_required # O el decorador que uses para restringir a bodega
def procesar_entrega_bodega(id_solicitud):
    solicitud = SolicitudMateriales.query.get_or_404(id_solicitud)
    
    try:
        # 1. Capturar datos generales del formulario
        fecha_gen = request.form.get('fecha_entrega_estimada')
        nota_gen = request.form.get('observacion_bodega')

        if fecha_gen:
            solicitud.fecha_entrega_estimada = datetime.strptime(fecha_gen, '%Y-%m-%d').date()
        
        solicitud.observacion_bodega = nota_gen # Se actualiza siempre (puede quedar vacío)
        solicitud.id_usuario_responsable = session['user_id'] # Registramos quién despachó

        # 2. Procesar cada material del detalle
        for detalle in solicitud.detalles:
            # IMPORTANTE: En el HTML usamos 'entrega_{{ item.id_detalle }}'
            # Ajusta 'id_detalle' al nombre real de la PK en tu modelo DetalleSolicitud
            cant_despachada_hoy = request.form.get(f'entrega_{detalle.id}', type=int, default=0)

            if cant_despachada_hoy > 0:
                # A. Validar que no entreguen más de lo pedido
                entregado_previo = detalle.cantidad_entregada or 0
                pendiente = detalle.cantidad - entregado_previo
                
                if cant_despachada_hoy > pendiente:
                    cant_despachada_hoy = pendiente # Capamos al máximo pendiente

                # B. ACTUALIZAR INVENTARIO (Si el material existe en la tabla Materiales)
                if detalle.material:
                    if detalle.material.cantidad < cant_despachada_hoy:
                        flash(f"Stock insuficiente para {detalle.material.nombre}. Stock: {detalle.material.cantidad}", "warning")
                        # Opcional: podrías hacer un continue o dejar que despache en negativo
                    
                    detalle.material.cantidad -= cant_despachada_hoy

                # C. Actualizar el acumulado en el detalle
                detalle.cantidad_entregada = entregado_previo + cant_despachada_hoy

        # 3. Lógica de estados
        # Verificamos si después de este despacho todo quedó cubierto
        todos_completos = all((d.cantidad_entregada or 0) >= d.cantidad for d in solicitud.detalles)
        
        if todos_completos:
            solicitud.estado = 'COMPLETADO'
        else:
            solicitud.estado = 'EN_PROCESO' # Con espacio, tal cual lo espera tu HTML

        solicitud.fecha_actualizacion = datetime.now()

        db.session.commit()
        flash("Despacho registrado y stock actualizado con éxito.", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"Error crítico al procesar: {str(e)}", "danger")
        print(f"Error: {e}") # Para debugging

    return redirect(url_for('materiales.solicitudes_bodega'))