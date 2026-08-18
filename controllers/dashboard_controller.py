import datetime
import os
from flask import Blueprint, render_template, redirect, request, url_for, flash, session
from datetime import date, timedelta, datetime
from decimal import Decimal
from werkzeug.utils import secure_filename
from models import db, Usuarios, Proyectos, Personal, Vehiculos, ProyectoPersonal, Materiales, SolicitudMateriales, Asistencia, Notificaciones, Cotizacion, DetalleSolicitudMaterial, RequisicionOficina
from frases import frase_del_dia
from decorators import login_required, admin_required, admin_encargado_required, admin_bodega_required, admin_oficina_required
from sqlalchemy import func
from sqlalchemy.orm import joinedload, selectinload

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
# DASHBOARD PRINCIPAL (ADMIN)
# -----------------------------
@dashboard_bp.route("/dashboard")
@login_required
def dashboard():
    # Verificar sesión
    frase = frase_del_dia()
    if "user_id" not in session:
        flash("Debes iniciar sesión primero", "warning")
        return redirect(url_for("usuarios.login"))

    rol = session.get("rol", "EMPLEADO")

    # Redirigir según rol
    if rol == "EMPLEADO":
        return redirect(url_for("dashboard.dashboard_trabajador"))
    elif rol == "OFICINA":
        return redirect(url_for("dashboard.dashboard_oficina"))
    elif rol == "BODEGA":
        return redirect(url_for("dashboard.dashboard_bodega"))

    # ======================
    # DASHBOARD DEL ADMIN
    # ======================
    proyectos = Proyectos.query.all()
    personal = Personal.query.all()
    vehiculos = Vehiculos.query.all()
    materiales = Materiales.query.all()

    # AJUSTE PARA EL ADMIN: Solo cargar proyectos visibles
    proyectos = Proyectos.query.filter_by(visible=True).all()

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
    proximos_dias = hoy + timedelta(days=7)
    alertas = []

    # Vehículos
    for v in vehiculos:
        if v.soat_vencimiento < hoy:
            alertas.append({"mensaje": f"El SOAT del vehículo {v.placa} está VENCIDO ({v.soat_vencimiento})", "tipo": "danger"})
        elif v.soat_vencimiento <= proximos_dias:
            alertas.append({"mensaje": f"El SOAT del vehículo {v.placa} vence pronto ({v.soat_vencimiento})", "tipo": "warning"})

        if v.tecno_vencimiento < hoy:
            alertas.append({"mensaje": f"La Técnico-Mecánica del vehículo {v.placa} está VENCIDA ({v.tecno_vencimiento})", "tipo": "danger"})
        elif v.tecno_vencimiento <= proximos_dias:
            alertas.append({"mensaje": f"La Técnico-Mecánica del vehículo {v.placa} vence pronto ({v.tecno_vencimiento})", "tipo": "warning"})

    

    vehiculos_disponibles = Vehiculos.query.filter_by(estado="Disponible").all()
    proyectos_recientes = Proyectos.query.order_by(Proyectos.fecha_inicio.desc()).limit(5).all()
    
    
    #  Notificaciones (solo no leídas)
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
    frase = frase_del_dia()

    usuario = Usuarios.query.get(session["user_id"])
    if not usuario.personal_data:
        return render_template("dashboard_trabajador.html", usuario=usuario, proyectos=[], solicitudes=[])

    personal_id = usuario.personal_data.id

    # --- 1. PROYECTOS ASIGNADOS ---
    proyectos_asignados = (
        db.session.query(Proyectos)
        .options(selectinload(Proyectos.materiales)) # <-- Fuerza a cargar la relación actualizada
        .options(joinedload(Proyectos.responsable))
        .join(ProyectoPersonal)
        .filter(ProyectoPersonal.personal_id == personal_id)
        .filter(Proyectos.visible == True)
        .distinct() 
        .all()
    )

    # Ahora permitimos que el trabajador vea TODO lo que tiene asignado y sea visible, 
    # sin importar si el estado cambió automáticamente a FINALIZADO.
    proyectos_activos = [
        p for p in proyectos_asignados
        if p.visible == True
    ]

    es_responsable=any(p.responsable_id == personal_id for p in proyectos_activos)

    # --- 2. SOLICITUDES DE MATERIAL  ---
    # Traemos todas las solicitudes hechas por este usuario, ordenadas por la más reciente
    solicitudes = SolicitudMateriales.query.filter_by(
    id_usuario_solicitante=session['user_id'],
    visible_para_trabajador=True  # <--- Solo mostrar las activas
    ).order_by(SolicitudMateriales.fecha_solicitud.desc()).all()

    # --- 3. NOTIFICACIONES ---
    notificaciones = (
        Notificaciones.query
        .filter_by(id_usuario_destino=session["user_id"], leido=False)
        .order_by(Notificaciones.creado_en.desc())
        .all()
    )

    hoy = datetime.utcnow().date()

    return render_template(
        "dashboard_trabajador.html",
        usuario=usuario,
        proyectos=proyectos_activos,
        solicitudes=solicitudes, # <--- ¡IMPORTANTE PASAR ESTO!
        frase=frase,
        now=hoy,
        datetime=datetime,
        notificaciones=notificaciones,
        es_responsable=es_responsable
    )

# -----------------------------
# DASHBOARD DE OFICINA
# -----------------------------
@dashboard_bp.route("/dashboard/oficina")
@login_required
@admin_oficina_required
def dashboard_oficina():
    frase = frase_del_dia()


    # 📌 Historial de cotizaciones (todas)
    cotizaciones_historial = (
        Cotizacion.query
        .order_by(Cotizacion.id.desc())
        .limit(5)
        .all()
    )

    # 📌 Seguimiento de tesorería (solo con contrato)
    from models import Contrato

    contratos = (
        Contrato.query
        .order_by(Contrato.id.desc())
        .limit(5)
        .all()
    )

    # Notificaciones no leídas
    notificaciones = Notificaciones.query.filter_by(
        id_usuario_destino=session["user_id"], leido=False
    ).order_by(Notificaciones.creado_en.desc()).all()

    # Usuario actual
    usuario = Usuarios.query.get(session.get("user_id"))
    
    print("TOTAL COTIZACIONES:", Cotizacion.query.count())
    print("CON CONTRATO:", Cotizacion.query.filter(Cotizacion.contrato.has()).count())

    # 📌 Bancos disponibles para el nuevo modal
    from models import Bancos
    bancos = Bancos.query.all()

    # Cálculo seguro de stock de materiales
    try:
        from models import db, Materiales
        total_m = db.session.query(db.func.count(Materiales.id_material)).scalar()
        total_materiales = int(total_m) if total_m else 0
    except Exception as e:
        print("Error calculando total_materiales:", e)
        total_materiales = 0

    return render_template(
        "dashboard_oficina.html",
        usuario=usuario,
        frase=frase,
        cotizaciones_historial=cotizaciones_historial,
        contratos=contratos,
        notificaciones=notificaciones,
        bancos=bancos,
        total_materiales=total_materiales
    )

# -----------------------------
# DASHBOARD DE OFICINA -> MATERIALES
# -----------------------------
@dashboard_bp.route("/dashboard/oficina/materiales")
@login_required
@admin_oficina_required
def gestion_materiales_oficina():
    # Notificaciones (para la barra lateral/global)
    notificaciones = Notificaciones.query.filter_by(
        id_usuario_destino=session["user_id"], leido=False
    ).order_by(Notificaciones.creado_en.desc()).all()

    # Requisiciones de bodega a oficina
    requisiciones_oficina = RequisicionOficina.query.order_by(RequisicionOficina.fecha_solicitud.desc()).all()
    
    usuario = Usuarios.query.get(session.get("user_id"))

    return render_template(
        "gestion_materiales_oficina.html",
        usuario=usuario,
        notificaciones=notificaciones,
        requisiciones_oficina=requisiciones_oficina
    )
# ============================================================
# MÓDULO PROVEEDORES — 4 rutas
# ============================================================

# ─── GET /dashboard/proveedores ───────────────────────────
@dashboard_bp.route("/dashboard/proveedores")
@login_required
@admin_oficina_required
def proveedores():
    from models import ProveedorFactura, Proveedor, ProveedorSubFactura, ProgramacionPagoProveedor
    usuario = Usuarios.query.get(session.get("user_id"))
    notificaciones = Notificaciones.query.filter_by(
        id_usuario_destino=session["user_id"], leido=False
    ).order_by(Notificaciones.creado_en.desc()).all()
    frase = frase_del_dia()

    facturas = ProveedorFactura.query.order_by(ProveedorFactura.fecha_factura.desc()).all()
    
    # Calcular dinámicamente el valor_cancelado basado en las subfacturas
    for f in facturas:
        if f.subfacturas:
            f.valor_cancelado = sum(sf.valor for sf in f.subfacturas)

    lista_proveedores = Proveedor.query.order_by(Proveedor.nombre.asc()).all()

    deuda_por_proveedor = {}
    for factura in facturas:
        nombre = factura.nombre_proveedor
        deuda_por_proveedor[nombre] = deuda_por_proveedor.get(nombre, 0) + float(factura.total_adeudado)

    # Totales globales (usan los @property del modelo)
    total_valor_neto      = sum(float(f.valor_neto or 0) for f in facturas)
    total_iva             = sum(f.iva for f in facturas)
    total_valor_total     = sum(f.valor_total for f in facturas)
    total_retencion       = sum(f.retencion_pesos for f in facturas)
    total_cancelado       = sum(float(f.valor_cancelado or 0) for f in facturas)
    total_adeudado_global = sum(deuda_por_proveedor.values())

    pagos_programados = ProgramacionPagoProveedor.query.order_by(ProgramacionPagoProveedor.fecha_programada.asc()).all()

    return render_template(
        "proveedores.html",
        usuario=usuario,
        notificaciones=notificaciones,
        frase=frase,
        facturas=facturas,
        total_valor_neto=total_valor_neto,
        total_iva=total_iva,
        total_valor_total=total_valor_total,
        total_retencion=total_retencion,
        total_cancelado=total_cancelado,
        total_adeudado_global=total_adeudado_global,
        proveedores=lista_proveedores,
        deuda_por_proveedor=deuda_por_proveedor,
        pagos_programados=pagos_programados
    )

# ─── GET /dashboard/proveedores/<nombre_proveedor> ────────
@dashboard_bp.route("/dashboard/proveedores/<string:nombre_proveedor>")
@login_required
@admin_oficina_required
def facturas_proveedor(nombre_proveedor):
    from models import ProveedorFactura
    usuario = Usuarios.query.get(session.get("user_id"))
    notificaciones = Notificaciones.query.filter_by(
        id_usuario_destino=session["user_id"], leido=False
    ).order_by(Notificaciones.creado_en.desc()).all()
    frase = frase_del_dia()

    facturas = ProveedorFactura.query.filter_by(nombre_proveedor=nombre_proveedor).order_by(ProveedorFactura.fecha_factura.desc()).all()
    
    # Calcular dinámicamente el valor_cancelado basado en las subfacturas
    for f in facturas:
        if f.subfacturas:
            f.valor_cancelado = sum(sf.valor for sf in f.subfacturas)
            
    deuda_total = sum(f.total_adeudado for f in facturas)

    return render_template(
        "facturas_proveedor.html",
        usuario=usuario,
        notificaciones=notificaciones,
        frase=frase,
        facturas=facturas,
        nombre_proveedor=nombre_proveedor,
        deuda_total=deuda_total
    )

# ─── POST /dashboard/proveedores/crear ────────────────────
@dashboard_bp.route("/dashboard/proveedores/crear", methods=["POST"])
@login_required
@admin_oficina_required
def crear_proveedor():
    from models import Proveedor
    try:
        nombre = request.form.get("nombre", "").strip()
        nit = request.form.get("nit", "").strip()
        telefono = request.form.get("telefono", "").strip()

        if not nombre:
            flash("El nombre del proveedor es obligatorio.", "warning")
            return redirect(url_for("dashboard.proveedores"))

        existe = Proveedor.query.filter(Proveedor.nombre.ilike(nombre)).first()
        if existe:
            flash("Ya existe un proveedor con ese nombre.", "warning")
            return redirect(url_for("dashboard.proveedores"))

        nuevo = Proveedor(nombre=nombre, nit=nit, telefono=telefono)
        db.session.add(nuevo)
        db.session.commit()
        flash("Proveedor registrado correctamente.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error al registrar proveedor: {e}", "danger")

    return redirect(url_for("dashboard.proveedores"))


# ─── POST /dashboard/proveedores/nueva ────────────────────
@dashboard_bp.route("/dashboard/proveedores/nueva", methods=["POST"])
@login_required
@admin_oficina_required
def nueva_factura_proveedor():
    from models import ProveedorFactura
    from datetime import datetime as dt
    from supabase_client import supabase
    import uuid

    print("--- ARCHIVOS RECIBIDOS EN FLASK (NUEVA FACTURA) ---")
    print(request.files)

    def upload_file(file_field):
        f = request.files.get(file_field)
        if not f or f.filename == "":
            return None
        if supabase is None:
            flash("Supabase no configurado. Archivo no subido.", "warning")
            return None
        try:
            ext = f.filename.rsplit(".", 1)[-1].lower()
            filename = f"{uuid.uuid4().hex}.{ext}"
            path = f"proveedores/{filename}"
            data = f.read()
            supabase.storage.from_("tesoreria").upload(
                path, data,
                {"content-type": f.content_type, "upsert": "false"}
            )
            return supabase.storage.from_("tesoreria").get_public_url(path)
        except Exception as e:
            flash(f"Error subiendo archivo: {e}", "warning")
            return None

    try:
        fecha_factura     = dt.strptime(request.form["fecha_factura"], "%Y-%m-%d").date()
        fecha_vencimiento = dt.strptime(request.form["fecha_vencimiento"], "%Y-%m-%d").date()
        fecha_pago_raw    = request.form.get("fecha_pago", "").strip()
        fecha_pago        = dt.strptime(fecha_pago_raw, "%Y-%m-%d").date() if fecha_pago_raw else None

        def parse_float_safe(value, default=0.0):
            try:
                if value is None or str(value).strip() == "": return default
                return float(value)
            except (ValueError, TypeError):
                return default

        def parse_pct(value, default=0.0):
            try:
                if value is None or str(value).strip() == "": return default
                return float(str(value).replace(',', '.').strip())
            except (ValueError, TypeError):
                return default

        factura = ProveedorFactura(
            nombre_proveedor       = request.form["nombre_proveedor"].strip(),
            fecha_factura          = fecha_factura,
            plazo_dias             = int(request.form.get("plazo_dias") or 0),
            fecha_vencimiento      = fecha_vencimiento,
            valor_neto             = parse_float_safe(request.form.get("valor_neto")),
            porcentaje_iva         = parse_pct(request.form.get("porcentaje_iva"), 19.0),
            valor_cancelado        = parse_float_safe(request.form.get("valor_cancelado")),
            retencion              = parse_pct(request.form.get("retencion")),
            fecha_pago             = fecha_pago,
            orden_compra_url       = upload_file("orden_compra"),
            comprobante_compra_url = upload_file("comprobante_compra"),
            banco_pago_url         = upload_file("banco_pago"),
        )
        db.session.add(factura)
        db.session.commit()
        flash("Factura de proveedor registrada correctamente.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error al registrar la factura: {e}", "danger")

    return redirect(url_for("dashboard.proveedores"))


# ─── POST /dashboard/proveedores/<id>/editar ──────────────
@dashboard_bp.route("/dashboard/proveedores/<int:id>/editar", methods=["POST"])
@login_required
@admin_oficina_required
def editar_factura_proveedor(id):
    from models import ProveedorFactura
    from datetime import datetime as dt
    from supabase_client import supabase
    import uuid

    factura = ProveedorFactura.query.get_or_404(id)

    print(f"--- ARCHIVOS RECIBIDOS EN FLASK (EDITAR FACTURA {id}) ---")
    print(request.files)

    def upload_or_keep(file_field, current_url):
        f = request.files.get(file_field)
        if not f or f.filename == "":
            return current_url
        if supabase is None:
            return current_url
        try:
            ext = f.filename.rsplit(".", 1)[-1].lower()
            filename = f"{uuid.uuid4().hex}.{ext}"
            path = f"proveedores/{filename}"
            data = f.read()
            supabase.storage.from_("tesoreria").upload(
                path, data,
                {"content-type": f.content_type, "upsert": "false"}
            )
            return supabase.storage.from_("tesoreria").get_public_url(path)
        except Exception as e:
            flash(f"Error subiendo archivo: {e}", "warning")
            return current_url

    try:
        def parse_float_safe(value, default=0.0):
            try:
                if value is None or str(value).strip() == "": return default
                return float(value)
            except (ValueError, TypeError):
                return default

        def parse_pct(value, default=0.0):
            try:
                if value is None or str(value).strip() == "": return default
                return float(str(value).replace(',', '.').strip())
            except (ValueError, TypeError):
                return default

        fecha_pago_raw = request.form.get("fecha_pago", "").strip()
        factura.nombre_proveedor       = request.form["nombre_proveedor"].strip()
        factura.fecha_factura          = dt.strptime(request.form["fecha_factura"], "%Y-%m-%d").date()
        factura.plazo_dias             = int(request.form.get("plazo_dias") or 0)
        factura.fecha_vencimiento      = dt.strptime(request.form["fecha_vencimiento"], "%Y-%m-%d").date()
        factura.valor_neto             = parse_float_safe(request.form.get("valor_neto"))
        factura.porcentaje_iva         = parse_pct(request.form.get("porcentaje_iva"), 19.0)
        factura.valor_cancelado        = parse_float_safe(request.form.get("valor_cancelado"))
        factura.retencion              = parse_pct(request.form.get("retencion"))
        factura.fecha_pago             = dt.strptime(fecha_pago_raw, "%Y-%m-%d").date() if fecha_pago_raw else None
        
        # Procesar archivos e interceptar flag de eliminación
        if request.form.get("eliminar_orden") == "true":
            factura.orden_compra_url = None
        else:
            factura.orden_compra_url = upload_or_keep("orden_compra", factura.orden_compra_url)
            
        if request.form.get("eliminar_comprobante") == "true":
            factura.comprobante_compra_url = None
        else:
            factura.comprobante_compra_url = upload_or_keep("comprobante_compra", factura.comprobante_compra_url)
            
        if request.form.get("eliminar_soporte") == "true":
            factura.banco_pago_url = None
        else:
            factura.banco_pago_url = upload_or_keep("banco_pago", factura.banco_pago_url)

        db.session.commit()
        flash("Factura actualizada correctamente.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error al actualizar: {e}", "danger")

    return redirect(url_for("dashboard.proveedores"))


# ─── POST /dashboard/proveedores/<id>/eliminar ────────────
@dashboard_bp.route("/dashboard/proveedores/<int:id>/eliminar", methods=["POST"])
@login_required
@admin_oficina_required
def eliminar_factura_proveedor(id):
    from models import ProveedorFactura
    factura = ProveedorFactura.query.get_or_404(id)
    try:
        db.session.delete(factura)
        db.session.commit()
        flash("Factura eliminada correctamente.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error al eliminar: {e}", "danger")
    return redirect(url_for("dashboard.proveedores"))


# ─── CLIENTES ─────────────
@dashboard_bp.route("/dashboard/clientes")
@login_required
@admin_oficina_required
def clientes():
    return redirect(url_for('clientes.index'))

# -----------------------------
# DASHBOARD DE BODEGA
# -----------------------------
@dashboard_bp.route("/dashboard/bodega")
@login_required
@admin_bodega_required
def dashboard_bodega():
    frase = frase_del_dia()

    if "user_id" not in session:
        flash("Debes iniciar sesión primero", "warning")
        return redirect(url_for("usuarios.login"))

    usuario = Usuarios.query.get(session["user_id"])
    rol = session.get("rol")

    # Solo permitir acceso a BODEGA o ADMIN
    if rol not in ["BODEGA", "ADMIN"]:
        flash("No tienes permiso para acceder a esta sección", "danger")
        return redirect(url_for("dashboard.dashboard"))

    #OBTENER DATOS PARA BODEGA
    materiales = Materiales.query.all()
    proyectos = Proyectos.query.all()

    # Requisiciones a la Oficina de este bodeguero
    from models import RequisicionOficina
    mis_reqs_oficina = RequisicionOficina.query.filter_by(bodeguero_id=session['user_id']).order_by(RequisicionOficina.fecha_solicitud.desc()).all()

    # 1. Definimos la carga optimizada para no repetir código
    # Esto trae la solicitud + sus detalles + el nombre del material en una sola ráfaga a la DB
    query_optimizada = SolicitudMateriales.query.options(
        joinedload(SolicitudMateriales.detalles).joinedload(DetalleSolicitudMaterial.material)
    ).filter_by(visible_para_bodega=True)

    # 2. Obtenemos las listas filtradas usando la optimización
    pendientes = query_optimizada.filter_by(estado='PENDIENTE').all()    
    en_proceso = query_optimizada.filter_by(estado='EN_PROCESO').all()
    completados = query_optimizada.filter_by(estado='COMPLETADO').all()
    rechazados = query_optimizada.filter_by(estado='RECHAZADO').all()

    # Calcular estadísticas
    total_materiales = len(materiales)
    total_proyectos = len(proyectos)

    # Notificaciones (solo no leídas)
    notificaciones = (
        Notificaciones.query
        .filter_by(id_usuario_destino=session["user_id"], leido=False)
        .order_by(Notificaciones.creado_en.desc())
        .all()
    )

    return render_template(
        "dashboard_bodega.html",  
        usuario=usuario,
        frase=frase,
        total_materiales=total_materiales,
        total_proyectos=total_proyectos,

        #PASAR  SOLICITUDES A LA PLANTILLA
        pendientes=pendientes,
        en_proceso=en_proceso,
        completados=completados,
        rechazados=rechazados,
        notificaciones=notificaciones,
        mis_reqs_oficina=mis_reqs_oficina
    )





@dashboard_bp.route("/dashboard/notificaciones/historial")
@login_required
def historial_notificaciones():

    user_id = session.get("user_id")
    if not user_id:
        flash("Error: usuario no autenticado.", "danger")
        return redirect(url_for("usuarios.login"))

    notificaciones = (
        Notificaciones.query
        .filter_by(id_usuario_destino=user_id)
        .order_by(Notificaciones.creado_en.desc())
        .all()
    )

    return render_template(
        "notif_personal.html",
        notificaciones=notificaciones
    )


#AFECTA UNICAMENTE AL USUARIO LOGEADO
@dashboard_bp.route("/dashboard/notificaciones/marcar_todas_leidas")
@login_required
def marcar_todas_leidas():
    try:
        user_id = session.get("user_id")
        if not user_id:
            flash("Error: usuario no autenticado.", "danger")
            return redirect(url_for("usuarios.login"))

        # Marcar todas las notificaciones del usuario como leídas
        notificaciones_no_leidas = Notificaciones.query.filter_by(
            id_usuario_destino=user_id,
            leido=False
        ).all()
        
        for notif in notificaciones_no_leidas:
            notif.leido = True
        
        db.session.commit()
        flash("Todas las notificaciones han sido marcadas como leídas", "success")
        
    except Exception as e:
        db.session.rollback()
        flash(f"Error al marcar notificaciones: {str(e)}", "danger")
    
    return redirect(url_for('dashboard.dashboard'))  # Redirige al dashboard


# ─── POST /dashboard/proveedores/subfactura/crear ────────────────────
@dashboard_bp.route("/dashboard/proveedores/subfactura/crear", methods=["POST"])
@login_required
@admin_oficina_required
def crear_proveedor_subfactura():
    from models import ProveedorFactura, ProveedorSubFactura
    from datetime import datetime as dt
    from supabase_client import supabase
    import uuid

    def upload_file(file_field):
        f = request.files.get(file_field)
        if not f or f.filename == "":
            return None
        if supabase is None:
            return None
        try:
            ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'webp'}
            ext = f.filename.rsplit(".", 1)[-1].lower()
            if ext not in ALLOWED_EXTENSIONS:
                flash(f"Extensión .{ext} no permitida. Solo PDF e imágenes.", "danger")
                return None
            filename = f"{uuid.uuid4().hex}.{ext}"
            path = f"proveedores/{filename}"
            data = f.read()
            supabase.storage.from_("tesoreria").upload(
                path, data,
                {"content-type": f.content_type, "upsert": "false"}
            )
            return supabase.storage.from_("tesoreria").get_public_url(path)
        except Exception as e:
            return None

    try:
        factura_id = request.form.get("factura_id")
        factura_padre = ProveedorFactura.query.get(factura_id)
        if not factura_padre:
            flash("Factura de proveedor no encontrada.", "danger")
            return redirect(url_for("dashboard.proveedores"))

        numero = request.form.get("numero_subfactura", "")
        fecha_str = request.form.get("fecha_subfactura", "")
        fecha = dt.strptime(fecha_str, "%Y-%m-%d").date() if fecha_str else None
        concepto = request.form.get("concepto", "")
        
        # parse valor
        valor_raw = request.form.get("valor", "0")
        valor_limpio = str(valor_raw).replace('$', '').replace(' ', '')
        
        # Format CO: 1.641.589,48
        if ',' in valor_limpio and '.' in valor_limpio:
            valor_limpio = valor_limpio.replace('.', '').replace(',', '.')
        elif ',' in valor_limpio:
            valor_limpio = valor_limpio.replace(',', '.')
        elif '.' in valor_limpio:
            partes = valor_limpio.split('.')
            if len(partes) > 2 or (len(partes) == 2 and len(partes[1]) == 3):
                valor_limpio = valor_limpio.replace('.', '')
                
        try:
            valor = float(valor_limpio)
        except ValueError:
            valor = 0.0

        pdf_url = upload_file("pdf_subfactura")

        nueva_sub = ProveedorSubFactura(
            factura_id=factura_padre.id,
            numero_subfactura=numero,
            fecha=fecha,
            concepto=concepto,
            valor=valor,
            archivo_pdf_url=pdf_url
        )
        db.session.add(nueva_sub)
        db.session.commit()

        # Recalcular valor_cancelado
        total_sub = db.session.query(db.func.sum(ProveedorSubFactura.valor)).filter_by(factura_id=factura_padre.id).scalar() or 0.0
        factura_padre.valor_cancelado = total_sub
        db.session.commit()

        flash("Sub-factura registrada correctamente.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error al crear sub-factura: {e}", "danger")

    redirect_to = request.form.get("redirect_to")
    if redirect_to == "facturas_proveedor" and 'factura_padre' in locals() and factura_padre:
        return redirect(url_for("dashboard.facturas_proveedor", nombre_proveedor=factura_padre.nombre_proveedor))
    return redirect(url_for("dashboard.proveedores"))


# ─── POST /dashboard/proveedores/subfactura/eliminar/<id> ─────────
@dashboard_bp.route("/dashboard/proveedores/subfactura/eliminar/<int:id>", methods=["POST"])
@login_required
@admin_oficina_required
def eliminar_proveedor_subfactura(id):
    from models import ProveedorSubFactura
    try:
        sub = ProveedorSubFactura.query.get(id)
        if not sub:
            flash("Sub-factura no encontrada.", "danger")
            return redirect(url_for("dashboard.proveedores"))

        factura_padre = sub.factura_padre
        db.session.delete(sub)
        db.session.commit()

        # Recalcular valor_cancelado
        total_sub = db.session.query(db.func.sum(ProveedorSubFactura.valor)).filter_by(factura_id=factura_padre.id).scalar() or 0.0
        factura_padre.valor_cancelado = total_sub
        db.session.commit()

        flash("Sub-factura eliminada.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error al eliminar sub-factura: {e}", "danger")

    redirect_to = request.form.get("redirect_to")
    if redirect_to == "facturas_proveedor" and 'factura_padre' in locals() and factura_padre:
        return redirect(url_for("dashboard.facturas_proveedor", nombre_proveedor=factura_padre.nombre_proveedor))
    return redirect(url_for("dashboard.proveedores"))
