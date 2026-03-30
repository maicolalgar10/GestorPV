from flask import Blueprint, render_template, request, redirect, url_for, flash
from datetime import date as d, datetime
from models import db, Asistencia, Proyectos, Personal, ProyectoPersonal, AsignacionDiaria
import traceback
from collections import defaultdict

asistencia_bp = Blueprint("asistencia", __name__)

# ------------------------------
# 🔧 Función auxiliar
# ------------------------------
def hoy_ymd() -> str:
    return d.today().isoformat()

# =======================================================
# (1) 🧱 REGISTRO MASIVO DIARIO (Estilo Asignaciones)
# =======================================================
@asistencia_bp.route('/asistencia/diaria', methods=['GET', 'POST'])
def registro_diario_masivo():
    """
    Muestra las tarjetas por proyecto basadas en la ASIGNACIÓN DIARIA.
    Permite guardar la asistencia de todos con un solo botón.
    """
    fecha_str = request.args.get('fecha') or hoy_ymd()
    fecha_dt = d.fromisoformat(fecha_str)

    # --- LOGICA POST: GUARDAR TODO ---
    if request.method == 'POST':
        try:
            # Traemos las asignaciones de ese día para saber a quién procesar
            # (Opcional: Podrías iterar sobre Personal.query.filter_by(activo=True) si quieres listar a todos)
            asignaciones_hoy = AsignacionDiaria.query.filter_by(fecha=fecha_dt).all()
            
            # Usamos un set para evitar duplicados si un trabajador tiene doble asignación (raro pero posible)
            procesados = set()

            for asignacion in asignaciones_hoy:
                pid = asignacion.personal_id
                if pid in procesados: continue
                procesados.add(pid)

                # Obtener valores del formulario (Names generados dinámicamente)
                check_manana = request.form.get(f"manana_{pid}") == "on"
                check_tarde = request.form.get(f"tarde_{pid}") == "on"
                motivo = request.form.get(f"motivo_{pid}")
                
                # Cálculo de horas (4h por turno)
                horas_totales = (4 if check_manana else 0) + (4 if check_tarde else 0)

                # Verificar si ya existe registro
                asistencia = Asistencia.query.filter_by(personal_id=pid, fecha=fecha_dt).first()

                if asistencia:
                    # Actualizar
                    asistencia.trabajo_manana = check_manana
                    asistencia.trabajo_tarde = check_tarde
                    asistencia.horas_trabajadas = horas_totales
                    asistencia.motivo = motivo
                    # Mantenemos el proyecto asignado
                    asistencia.proyecto_id = asignacion.proyecto_id 
                else:
                    # Crear nuevo solo si marcó algo o puso motivo
                    if horas_totales > 0 or motivo:
                        nueva = Asistencia(
                            personal_id=pid,
                            proyecto_id=asignacion.proyecto_id,
                            fecha=fecha_dt,
                            trabajo_manana=check_manana,
                            trabajo_tarde=check_tarde,
                            horas_trabajadas=horas_totales,
                            motivo=motivo
                        )
                        db.session.add(nueva)

            db.session.commit()
            flash(f"Asistencia del {fecha_str} guardada correctamente.", "success")
            return redirect(url_for('asistencia.registro_diario_masivo', fecha=fecha_str))

        except Exception as e:
            db.session.rollback()
            print(traceback.format_exc())
            flash(f"Error masivo: {e}", "danger")

    # --- LOGICA GET: MOSTRAR VISTA MASONRY ---
    
    # 1. Traer la planificación (Asignaciones)
    asignaciones = AsignacionDiaria.query.filter_by(fecha=fecha_dt).all()
    
    # 2. Traer la realidad (Asistencias ya guardadas)
    asistencias_db = Asistencia.query.filter_by(fecha=fecha_dt).all()
    mapa_asistencia = {a.personal_id: a for a in asistencias_db}

    # 3. Agrupar por Proyecto
    grupos_proyectos = defaultdict(list)

    for asign in asignaciones:
        worker_data = {
            'personal': asign.personal,
            'asistencia': mapa_asistencia.get(asign.personal_id), # None si no se ha guardado
            'asignacion': asign
        }
        grupos_proyectos[asign.proyecto.nombre].append(worker_data)

    return render_template(
        "asistencia_diaria_masiva.html", # 👈 Esta es la plantilla nueva estilo Masonry
        grupos_proyectos=grupos_proyectos,
        fecha_seleccionada=fecha_str
    )


# =======================================================
# (2) ✏️ EDICIÓN INDIVIDUAL (Detallada)
# =======================================================
@asistencia_bp.route("/personal/<int:personal_id>/asistencia", methods=["GET", "POST"])
def asistencia_trabajador(personal_id):
    """
    Permite editar la asistencia de UN solo trabajador.
    Útil para correcciones específicas o días pasados.
    """
    fecha_str = request.args.get("fecha") or hoy_ymd()
    fecha_dt = d.fromisoformat(fecha_str)

    trabajador = Personal.query.get_or_404(personal_id)

    # ... (Lógica de proyectos_asignados) ...
    proyectos_asignados = (
        Proyectos.query
        .join(ProyectoPersonal)
        .filter(ProyectoPersonal.personal_id == personal_id)
        .order_by(Proyectos.nombre.asc())
        .all()
    )

    if request.method == "POST":
        try:
            # 🚨 CORRECCIÓN MENOR: Asegurar que las horas se manejen como float para precisión
            # Esto previene errores de redondeo o división si se usa 4.0/2 en algún punto.
            horas_m = float(request.form.get("horas_manana") or 0)
            horas_t = float(request.form.get("horas_tarde") or 0)
            
            # ... (Resto del POST sigue igual) ...
            trabajo_manana = request.form.get("manana_check") == "on"
            trabajo_tarde = request.form.get("tarde_check") == "on"
            
            # Proyecto y Motivo
            proyecto_id = request.form.get("proyecto_id")
            proyecto_id = int(proyecto_id) if proyecto_id else None
            motivo = request.form.get("motivo")
            
            # Fecha del formulario (por si cambió)
            fecha_form = request.form.get("fecha")
            fecha_form_dt = d.fromisoformat(fecha_form)

            # Buscar si existe
            fila = Asistencia.query.filter_by(personal_id=personal_id, fecha=fecha_form_dt).first()

            if fila:
                fila.proyecto_id = proyecto_id
                fila.trabajo_manana = trabajo_manana
                fila.trabajo_tarde = trabajo_tarde
                fila.horas_trabajadas = horas_m + horas_t # Usamos la suma de floats
                fila.motivo = motivo
            else:
                if (horas_m + horas_t) > 0 or motivo:
                    db.session.add(Asistencia(
                        personal_id=personal_id,
                        proyecto_id=proyecto_id,
                        fecha=fecha_form_dt,
                        trabajo_manana=trabajo_manana,
                        trabajo_tarde=trabajo_tarde,
                        horas_trabajadas=horas_m + horas_t, # Usamos la suma de floats
                        motivo=motivo
                    ))

            db.session.commit()
            flash(f"Asistencia de {trabajador.nombre} guardada.", "success")
            return redirect(url_for("asistencia.asistencia_trabajador", personal_id=personal_id, fecha=fecha_form))

        except Exception as e:
            db.session.rollback()
            print(traceback.format_exc())
            flash(f"Error: {e}", "danger")

    # --- GET: Preparar datos para el formulario individual ---
    
    # ... (Lógica de historial) ...

    # Datos del día seleccionado para llenar el form
    registro_dia = Asistencia.query.filter_by(personal_id=personal_id, fecha=fecha_dt).first()
    proyecto_seleccionado_id = registro_dia.proyecto_id if registro_dia and registro_dia.proyecto_id else None
    
    # --- LÓGICA CORREGIDA PARA CALCULAR HORAS INDIVIDUALES (2.0 -> 4.0) ---
    horas_manana_carga = 0.0 # Usar float por defecto
    horas_tarde_carga = 0.0 
    
    # Historial de 7 días (Definido fuera de cualquier condicional)
    historial = (
        Asistencia.query.filter_by(personal_id=personal_id)
        .order_by(Asistencia.fecha.desc())
        .limit(7)
        .all()
    )


    if registro_dia:
        # La lógica más simple es usar las banderas booleanas (establecidas por el flujo masivo)
        # para cargar 4.0 horas por cada turno marcado.
        
        if registro_dia.trabajo_manana:
            # Si solo AM fue marcado (o AM y PM), cargamos 4.0h en la mañana.
            # Esto cubre el caso donde horas_trabajadas es 4 (solo AM) y evita el 2.0.
            horas_manana_carga = 4.0
        
        if registro_dia.trabajo_tarde:
            # Si solo PM fue marcado (o AM y PM), cargamos 4.0h en la tarde.
            horas_tarde_carga = 4.0
            
        # Caso de edición manual previa (Sin banderas o con un total no estándar 4/8)
        # Si las banderas NO explican la asistencia (es decir, ambas son False, pero horas > 0),
        # usamos el total guardado para dividirlo (Opción 4 de tu lógica anterior).
        if not registro_dia.trabajo_manana and not registro_dia.trabajo_tarde and registro_dia.horas_trabajadas > 0:
            # Asistencia registrada manualmente sin usar los checkboxes AM/PM. Dividimos el total.
            horas_manana_carga = float(registro_dia.horas_trabajadas) / 2
            horas_tarde_carga = float(registro_dia.horas_trabajadas) / 2

    # ... (Resto de la lógica de historial sin cambios) ...

    # Diccionario para la tabla de historial (Mantenemos el historial sin cambios)
    asistencia_registrada = {
        a.fecha.isoformat(): {
            "horas_trabajadas": a.horas_trabajadas,
            "motivo": a.motivo,
            "proyecto_id": a.proyecto_id
        } for a in historial
    }
    
    # Insertar el día actual si existe en el mapa
    if registro_dia:
        asistencia_registrada[fecha_str] = { # Reemplazar el update con una asignación completa para claridad
             "horas_trabajadas": registro_dia.horas_trabajadas,
             "motivo": registro_dia.motivo,
             "proyecto_id": registro_dia.proyecto_id,
             "manana": registro_dia.trabajo_manana, 
             "tarde": registro_dia.trabajo_tarde,
             "horas_m_carga": horas_manana_carga, # 👈 CARGA CORREGIDA
             "horas_t_carga": horas_tarde_carga # 👈 CARGA CORREGIDA
        }

    return render_template(
        "asistencia.html", 
        # ... (otras variables)
        trabajador=trabajador,
        proyectos=proyectos_asignados,
        fecha_str=fecha_str,
        registro_dia=registro_dia,
        horas_manana_carga=horas_manana_carga, # 👈 PASAR A LA PLANTILLA
        horas_tarde_carga=horas_tarde_carga, # 👈 PASAR A LA PLANTILLA
        asistencia_registrada=asistencia_registrada,
        proyecto_seleccionado_id=proyecto_seleccionado_id, # 👈 PASAR A LA PLANTILLA
    )
# =======================================================
# (3) 🗑️ ELIMINAR ASISTENCIA
# =======================================================
@asistencia_bp.route('/asistencia/eliminar/<int:personal_id>/<string:fecha>')
def delete_asistencia(personal_id, fecha):
    try:
        fecha_dt = d.fromisoformat(fecha)
        registro = Asistencia.query.filter_by(personal_id=personal_id, fecha=fecha_dt).first()
        if registro:
            db.session.delete(registro)
            db.session.commit()
            flash("Asistencia eliminada.", "success")
        else:
            flash("No se encontró el registro.", "warning")
    except Exception as e:
        db.session.rollback()
        flash(f"Error: {e}", "danger")
        
    return redirect(url_for('asistencia.asistencia_trabajador', personal_id=personal_id, fecha=fecha))