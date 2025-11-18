import datetime
import os
from flask import Blueprint, render_template, redirect, request, url_for, flash, session
from datetime import date, timedelta, datetime
from decimal import Decimal
from werkzeug.utils import secure_filename
from models import db, Usuarios, Proyectos, Personal, Vehiculos, ProyectoPersonal, Materiales, MaterialesProyecto, Asistencia, Avances, Notificaciones
from frases import frase_del_dia
from decorators import login_required, admin_required, admin_encargado_required # Importa los decoradores


# Creamos el blueprint
dashboard_bp = Blueprint("dashboard", __name__)

# -----------------------------
# INICIO / HOME
# -----------------------------
@dashboard_bp.route("/")
def home():
    if "user_id" in session:
        return redirect(url_for("dashboard.dashboard"))
    return redirect(url_for("usuarios.login"))

# -----------------------------
# DASHBOARD PRINCIPAL
# -----------------------------
@dashboard_bp.route("/dashboard")
@login_required
def dashboard():
    # Verificar sesión
    frase = frase_del_dia()
    if "user_id" not in session:
        flash("⚠️ Debes iniciar sesión primero", "warning")
        return redirect(url_for("usuarios.login"))

    rol = session.get("rol", "EMPLEADO")

    # Redirigir si es empleado
    if rol == "EMPLEADO":
        return redirect(url_for("dashboard.dashboard_trabajador"))

    # ======================
    # DASHBOARD DEL ADMIN
    # ======================
    proyectos = Proyectos.query.all()
    personal = Personal.query.all()
    vehiculos = Vehiculos.query.all()
    materiales = Materiales.query.all()

    # Separar proyectos activos y finalizados
    proyectos_activos = [p for p in proyectos if p.estado and p.estado.strip().upper() != "FINALIZADO"]
    proyectos_terminados = [p for p in proyectos if p.estado and p.estado.strip().upper() == "FINALIZADO"]

    proyectos_activos_data = []
    for p in proyectos_activos:
        relaciones_p = ProyectoPersonal.query.filter_by(proyecto_id=p.id_proyecto).all()

        # Solo personal activo
        relaciones_activos = [
            rel for rel in relaciones_p
            if rel.personal and getattr(rel.personal, "activo", True)
        ]

        # ================================
        # CÁLCULO DEL COSTO TOTAL
        # ================================
        costo_total = Decimal(0)
        for rel in relaciones_activos:
            # Si no tiene dias_asignados, intentar calcularlo desde Asistencia
            if getattr(rel, "dias_asignados", None) is None:
                rel.dias_asignados = 0  # por seguridad

            # (opcional) calcular automáticamente según la tabla Asistencia
            dias_trabajados = Asistencia.query.filter_by(
                proyecto_id=p.id_proyecto, personal_id=rel.personal_id
            ).count()

            # Si hay registros de asistencia, reemplazamos el valor
            if dias_trabajados > 0:
                rel.dias_asignados = dias_trabajados

            costo_total += rel.personal.costo_diario * rel.dias_asignados

        proyectos_activos_data.append({
            "id": p.id_proyecto,
            "nombre": p.nombre,
            "lugar": p.lugar,
            "responsable": p.responsable.nombre if p.responsable else "No asignado",
            "personal": relaciones_activos,
            "costo_total": costo_total,
            "vehiculos": [f"{rel.vehiculo.placa} - {rel.vehiculo.modelo}" for rel in p.vehiculos],
            "estado": p.estado
        })


    # ======================
    # PROYECTOS FINALIZADOS
    # ======================
    proyectos_finalizados = []
    for p in proyectos_terminados:
        proyectos_finalizados.append({
            "id": p.id_proyecto,
            "nombre": p.nombre,
            "lugar": p.lugar,
            "responsable": p.responsable.nombre if p.responsable else "No asignado",
            "estado": p.estado,
            "fecha_inicio": p.fecha_inicio,
            "fecha_fin": p.fecha_fin
        })

    # ======================
    # ALERTAS
    # ======================
    hoy = date.today()
    proximos_dias = hoy + timedelta(days=30)
    alertas = []

    # Vehículos
    for v in vehiculos:
        if v.soat_vencimiento < hoy:
            alertas.append({"mensaje": f"🚨 El SOAT del vehículo {v.placa} está VENCIDO ({v.soat_vencimiento})", "tipo": "danger"})
        elif v.soat_vencimiento <= proximos_dias:
            alertas.append({"mensaje": f"⚠️ El SOAT del vehículo {v.placa} vence pronto ({v.soat_vencimiento})", "tipo": "warning"})

        if v.tecno_vencimiento < hoy:
            alertas.append({"mensaje": f"🚨 La Técnico-Mecánica del vehículo {v.placa} está VENCIDA ({v.tecno_vencimiento})", "tipo": "danger"})
        elif v.tecno_vencimiento <= proximos_dias:
            alertas.append({"mensaje": f"⚠️ La Técnico-Mecánica del vehículo {v.placa} vence pronto ({v.tecno_vencimiento})", "tipo": "warning"})

    # Materiales
    for m in materiales:
        if m.cantidad <= m.stock_minimo:
            alertas.append({"mensaje": f"🚨 El material '{m.nombre}' está en nivel CRÍTICO ({m.cantidad} {m.unidad})", "tipo": "danger"})
        elif m.cantidad <= m.stock_minimo + 5:
            alertas.append({"mensaje": f"⚠️ El material '{m.nombre}' está en nivel BAJO ({m.cantidad} {m.unidad})", "tipo": "warning"})

    vehiculos_disponibles = Vehiculos.query.filter_by(estado="Disponible").all()
    proyectos_recientes = Proyectos.query.order_by(Proyectos.fecha_inicio.desc()).limit(5).all()
    
    
    # 🔔 Notificaciones (solo no leídas)
    notificaciones = (
        Notificaciones.query
        .filter_by(id_usuario_destino=session["user_id"], leido=False)
        .order_by(Notificaciones.creado_en.desc())
        .all()
    )


    return render_template(
        "dashboard.html",
        proyectos_activos=proyectos_activos_data,
        proyectos_finalizados=proyectos_finalizados,
        personal=personal,
        vehiculos=vehiculos,
        vehiculos_disponibles=vehiculos_disponibles,
        materiales=materiales,
        alertas=alertas,
        proyectos_recientes=proyectos_recientes,
        frase=frase,
        notificaciones=notificaciones
    )

# -----------------------------
# DASHBOARD DEL TRABAJADOR
# -----------------------------
@dashboard_bp.route("/dashboard/trabajador")
@login_required
def dashboard_trabajador():
    frase = frase_del_dia()  # genera una diferente cada día

    if "user_id" not in session:
        flash("⚠️ Debes iniciar sesión primero", "warning")
        return redirect(url_for("usuarios.login"))

    usuario = Usuarios.query.get(session["user_id"])
    if not usuario.personal_data:
        return render_template("dashboard_trabajador.html", usuario=usuario, proyectos=[])

    personal_id = usuario.personal_data.id


    proyectos_asignados = (
        db.session.query(Proyectos)
        .join(ProyectoPersonal)
        .filter(ProyectoPersonal.personal_id == personal_id)
        .distinct() 
        .all()
    )

    # Calcular progreso PONDERADO
    for proyecto in proyectos_asignados:
        total_unidades_proyecto = 0
        total_avanzado_proyecto = 0

        for actividad in proyecto.actividades:
            total = actividad.unidades_totales or 0
            avanzado = (
                db.session.query(db.func.sum(Avances.unidades_avanzadas))
                .filter_by(id_actividad=actividad.id_actividad)
                .scalar()
            ) or 0

            actividad.avanzado = avanzado
            actividad.porcentaje = int((avanzado / total) * 100) if total > 0 else 0

            total_unidades_proyecto += total
            total_avanzado_proyecto += avanzado

        if total_unidades_proyecto > 0:
            proyecto.progreso_general = round((total_avanzado_proyecto / total_unidades_proyecto) * 100, 1)
        else:
            proyecto.progreso_general = 0

    hoy = datetime.utcnow().date()
    proyectos_activos = [
        p for p in proyectos_asignados
        if not p.estado or p.estado.strip().upper() != "FINALIZADO"
    ]

    # 🔔 Notificaciones (solo no leídas)
    notificaciones = (
        Notificaciones.query
        .filter_by(id_usuario_destino=session["user_id"], leido=False)
        .order_by(Notificaciones.creado_en.desc())
        .all()
    )

    return render_template(
        "dashboard_trabajador.html",
        usuario=usuario,
        proyectos=proyectos_activos,
        frase=frase,
        now=hoy,
        datetime=datetime,
        notificaciones=notificaciones
    )

