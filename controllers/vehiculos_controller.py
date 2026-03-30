from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models import db, Vehiculos, Proyectos, VehiculoProyecto, MovimientoVehiculo
from datetime import datetime as dt, date
from decimal import Decimal
from operator import attrgetter
from sqlalchemy.orm import aliased
from decorators import login_required, admin_required, admin_encargado_required # Importa los decoradores



vehiculos_bp = Blueprint("vehiculos", __name__)

# 👉 Lista de vehículos
@vehiculos_bp.route("/vehiculos")
@login_required
@admin_required
def manage_vehiculos():
    hoy = date.today()

    vehiculos = Vehiculos.query.order_by(Vehiculos.placa).all()

    vehiculos_info = []

    for v in vehiculos:
        # Verificar si los documentos están al día
        v.documentos_al_dia = not (v.soat_vencimiento < hoy or v.tecno_vencimiento < hoy)

        #  NUEVA LÓGICA: Determinar estado de documentos
        # Calcular si SOAT o Tecnomecánica vencen en 7 días o menos
        soat_proximo_vencimiento = (v.soat_vencimiento - hoy).days <= 7 and v.soat_vencimiento >= hoy
        tecno_proximo_vencimiento = (v.tecno_vencimiento - hoy).days <= 7 and v.tecno_vencimiento >= hoy

        # Calcular si SOAT o Tecnomecánica ya vencieron
        soat_vencido = v.soat_vencimiento < hoy
        tecno_vencido = v.tecno_vencimiento < hoy

        # Asignar estado de alerta
        if soat_vencido or tecno_vencido:
            v.estado_documento = "vencido"  
        elif soat_proximo_vencimiento or tecno_proximo_vencimiento:
            v.estado_documento = "proximo_vencimiento"  
        else:
            v.estado_documento = "vigente"  

        # Buscar la última asignación del vehículo
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


# Crear nuevo vehículo
@vehiculos_bp.route('/vehiculos/nuevo', methods=['GET', 'POST'])
@login_required
@admin_required
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
            flash(" Vehículo agregado correctamente", "success")
            return redirect(url_for("vehiculos.manage_vehiculos"))

        except Exception as e:
            db.session.rollback()
            flash(f"Error al agregar el vehículo: {str(e)}", "danger")
            return redirect(url_for("vehiculos.manage_vehiculos"))

    return render_template(
        "nuevo_vehiculo.html",
        fecha_hoy=date.today()
    )


#  Editar vehículo
@vehiculos_bp.route('/vehiculos/editar/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
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
            flash("Vehículo actualizado correctamente", "success")
            return redirect(url_for("vehiculos.manage_vehiculos"))

        except Exception as e:
            db.session.rollback()
            flash(f"Error al actualizar el vehículo: {str(e)}", "danger")
            return redirect(url_for("vehiculos.manage_vehiculos"))

    return render_template(
        "editar_vehiculo.html",
        vehiculo=vehiculo,
        fecha_hoy=date.today()
    )


#  Eliminar vehículo
@vehiculos_bp.route('/vehiculos/delete/<int:id>', methods=['POST'])
@login_required
@admin_required
def delete_vehiculo(id):
    vehiculo = Vehiculos.query.get_or_404(id)
    try:
        db.session.delete(vehiculo)
        db.session.commit()
        flash("Vehículo eliminado correctamente", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error al eliminar el vehículo: {str(e)}", "danger")
    return redirect(url_for("vehiculos.manage_vehiculos"))


# vehiculos_controller.py
@vehiculos_bp.route('/gestion')
@login_required
@admin_required
def gestion_vehiculos():
    # 1. Obtener todos los vehículos ordenados por placa
    vehiculos = Vehiculos.query.order_by(Vehiculos.placa).all()

    # 2. Obtener todos los movimientos ordenados por fecha_hora descendente (más reciente arriba)
    # Usamos order_by directamente en la consulta para que la base de datos haga el trabajo
    movimientos_globales = MovimientoVehiculo.query.order_by(MovimientoVehiculo.fecha_hora.desc()).all()

    # 3. Obtener proyectos
    proyectos = Proyectos.query.all()

    # 4. Renderizar la plantilla con los datos ordenados
    return render_template(
        "gestion_vehiculos.html",
        vehiculos=vehiculos,      # Vehículos ordenados por placa
        proyectos=proyectos,      # Lista de proyectos
        movimientos_globales=movimientos_globales # Movimientos ordenados por fecha (más reciente arriba)
    )


# vehiculos_controller.py
@vehiculos_bp.route('/cambiar_asignacion/<int:id_vehiculo>', methods=['POST'])
@login_required
@admin_required
def cambiar_asignacion(id_vehiculo):
    try:
        print(f"\n🔍 [DEBUG] Iniciando cambio de asignación para vehículo ID: {id_vehiculo}")

        vehiculo = Vehiculos.query.get_or_404(id_vehiculo)
        print(f"✅ [DEBUG] Vehículo encontrado: {vehiculo.placa}")

        # Obtener los datos del formulario
        proyecto_nuevo_id = request.form.get('proyecto_nuevo_id')
        ubicacion_nueva = request.form.get('ubicacion_nueva')
        motivo = request.form.get('motivo', '')

        print(f"📋 [DEBUG] Datos recibidos - Proyecto Nuevo ID: {proyecto_nuevo_id}, Ubicación Nueva: {ubicacion_nueva}, Motivo: {motivo}")

        # Guardar el estado anterior
        proyecto_anterior_id = vehiculo.proyecto_actual_id
        #  OBTENER EL NOMBRE DEL PROYECTO ANTERIOR EN VEZ DE LA UBICACIÓN
        proyecto_anterior_nombre = None
        if vehiculo.proyecto_actual:
             proyecto_anterior_nombre = vehiculo.proyecto_actual.nombre

        #  USAR EL NOMBRE DEL PROYECTO ANTERIOR COMO 'ubicacion_anterior' en el movimiento
        ubicacion_anterior_para_registro = proyecto_anterior_nombre if proyecto_anterior_nombre else 'Sin asignar'

        print(f"🔄 [DEBUG] Estado anterior - Proyecto ID: {proyecto_anterior_id}, Nombre Proyecto: {proyecto_anterior_nombre}")

        # Actualizar el vehículo
        vehiculo.proyecto_actual_id = int(proyecto_nuevo_id) if proyecto_nuevo_id else None
        vehiculo.ubicacion_actual = ubicacion_nueva # La ubicación actual sí se actualiza con lo que se ingresa
        vehiculo.updated_at = dt.utcnow() # Asegúrate de que el modelo Vehiculos tenga este campo o quítalo si no lo usas

        print(f"📝 [DEBUG] Vehículo actualizado en memoria - Nuevo Proyecto ID: {vehiculo.proyecto_actual_id}, Nueva Ubicación: {vehiculo.ubicacion_actual}")

        # Crear el registro de movimiento
        movimiento = MovimientoVehiculo(
            id_vehiculo=id_vehiculo,
            id_usuario=session.get('user_id'),  # Ajusta según tu sistema de sesión
            proyecto_anterior_id=proyecto_anterior_id,
            proyecto_nuevo_id=int(proyecto_nuevo_id) if proyecto_nuevo_id else None,
            # ✅ USAR EL NOMBRE DEL PROYECTO ANTERIOR COMO UBICACIÓN ANTERIOR EN EL REGISTRO
            ubicacion_anterior=ubicacion_anterior_para_registro,
            # ✅ USAR LA UBICACIÓN INGRESADA COMO UBICACIÓN NUEVA EN EL REGISTRO
            ubicacion_nueva=ubicacion_nueva,
            motivo=motivo
        )
        db.session.add(movimiento)
        print(f"➕ [DEBUG] Movimiento creado y añadido a la sesión. Ubicación anterior registrada: '{ubicacion_anterior_para_registro}', Ubicación nueva: '{ubicacion_nueva}'")

        # Intentar hacer commit
        db.session.commit()
        print(f"✅ [DEBUG] Commit exitoso. Asignación y movimiento guardados.")

        flash("Asignación actualizada y movimiento registrado.", "success")

    except Exception as e:
        # Capturar cualquier error
        db.session.rollback()
        print(f"❌ [ERROR] Ocurrió un error: {e}")
        flash(f"Error al cambiar la asignación: {str(e)}", "danger")

    return redirect(url_for('vehiculos.gestion_vehiculos'))


# vehiculos_controller.py
@vehiculos_bp.route('/historial_completo')
@login_required
@admin_required
def historial_completo():
    # Obtener parámetros de filtro desde la URL
    fecha_desde = request.args.get('fecha_desde', '')
    fecha_hasta = request.args.get('fecha_hasta', '')
    placa = request.args.get('placa', '')
    proyecto = request.args.get('proyecto', '')

    # Página actual
    page = request.args.get('page', 1, type=int)

    # Construir la consulta base
    query = MovimientoVehiculo.query

    # Crear alias para Proyectos
    ProyectoAnterior = aliased(Proyectos)
    ProyectoNuevo = aliased(Proyectos)

    # Aplicar filtros si se proporcionan
    if fecha_desde:
        try:
            fecha_desde_dt = dt.strptime(fecha_desde, "%Y-%m-%d")
            query = query.filter(MovimientoVehiculo.fecha_hora >= fecha_desde_dt)
        except ValueError:
            flash("Formato de fecha 'Desde' inválido. Use YYYY-MM-DD.", "warning")

    if fecha_hasta:
        try:
            fecha_hasta_dt = dt.strptime(fecha_hasta, "%Y-%m-%d")
            query = query.filter(MovimientoVehiculo.fecha_hora <= fecha_hasta_dt)
        except ValueError:
            flash("Formato de fecha 'Hasta' inválido. Use YYYY-MM-DD.", "warning")

    if placa:
        query = query.join(MovimientoVehiculo.vehiculo).filter(Vehiculos.placa.ilike(f'%{placa}%'))

    if proyecto:
        # Filtrar por nombre de proyecto (desde proyecto_anterior o proyecto_nuevo)
        query = query.outerjoin(ProyectoAnterior, MovimientoVehiculo.proyecto_anterior_id == ProyectoAnterior.id_proyecto)\
                   .outerjoin(ProyectoNuevo, MovimientoVehiculo.proyecto_nuevo_id == ProyectoNuevo.id_proyecto)\
                   .filter(
                       db.or_(
                           ProyectoAnterior.nombre.ilike(f'%{proyecto}%'),
                           ProyectoNuevo.nombre.ilike(f'%{proyecto}%')
                       )
                   )

    # Paginación
    per_page = 10  # Número de registros por página
    movimientos_paginados = query.order_by(MovimientoVehiculo.fecha_hora.desc()).paginate(page=page, per_page=per_page, error_out=False)

    # Pasar los datos a la plantilla
    return render_template("vehiculos_historial.html", movimientos=movimientos_paginados.items, fecha_desde=fecha_desde, fecha_hasta=fecha_hasta, placa=placa, proyecto=proyecto, pagination=movimientos_paginados)
    