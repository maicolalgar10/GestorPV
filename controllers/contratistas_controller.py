from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session
from datetime import datetime as dt
import os
import uuid
import re
from werkzeug.utils import secure_filename

from models import db, Usuarios, Notificaciones, Contratista, ContratistaFactura
from supabase_client import supabase
from decorators import login_required, admin_oficina_required
from frases import frase_del_dia

contratistas_bp = Blueprint("contratistas", __name__, url_prefix='/contratistas')

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'pdf', 'png', 'jpg', 'jpeg', 'webp'}

def parse_float_safe(value):
    if not value:
        return 0.0
    try:
        val_str = str(value).replace('$', '').replace(' ', '').strip()
        if ',' in val_str:
            val_str = val_str.replace('.', '')
            val_str = val_str.replace(',', '.')
        elif val_str.count('.') > 1:
            val_str = val_str.replace('.', '')
        return float(val_str)
    except ValueError:
        return 0.0

def subir_archivo_supabase(file_obj, carpeta="contratistas"):
    """Sube un archivo a Supabase Storage y retorna la URL pública."""
    if not file_obj or file_obj.filename == '':
        return None
        
    if allowed_file(file_obj.filename):
        nombre_seguro = secure_filename(file_obj.filename)
        nombre_seguro = re.sub(r'[^a-zA-Z0-9._-]', '_', nombre_seguro)
        
        filename = f"{uuid.uuid4().hex}_{nombre_seguro}"
        path = f"{carpeta}/{filename}"
        
        file_bytes = file_obj.read()
        try:
            supabase.storage.from_("tesoreria").upload(
                path,
                file_bytes,
                {"content-type": file_obj.content_type}
            )
            return supabase.storage.from_("tesoreria").get_public_url(path)
        except Exception as e:
            print(f"!!! ERROR CRÍTICO EN SUPABASE STORAGE: {str(e)}")
            return None
    return None

# ─── GET /contratistas ───────────────────────────
@contratistas_bp.route("/", methods=['GET'])
@login_required
@admin_oficina_required
def index():
    usuario = Usuarios.query.get(session.get("user_id"))
    notificaciones = Notificaciones.query.filter_by(
        id_usuario_destino=session["user_id"], leido=False
    ).order_by(Notificaciones.creado_en.desc()).all()
    frase = frase_del_dia()

    lista_contratistas = Contratista.query.order_by(Contratista.nombre.asc()).all()
    facturas = ContratistaFactura.query.order_by(ContratistaFactura.fecha_factura.desc()).all()

    facturas_por_contratista = {c.nombre: [] for c in lista_contratistas}
    for f in facturas:
        if f.nombre_contratista in facturas_por_contratista:
            facturas_por_contratista[f.nombre_contratista].append(f)
        else:
            facturas_por_contratista[f.nombre_contratista] = [f]

    totales_contratistas = {}
    for contratista in lista_contratistas:
        facturas_c = facturas_por_contratista.get(contratista.nombre, [])
        total_facturado = sum(float(f.valor_total) for f in facturas_c)
        total_rete_garantia = sum(float(f.retencion_pesos) for f in facturas_c)
        total_pagos = sum(float(f.valor_cancelado) for f in facturas_c)
        saldo_adeudado = sum(float(f.total_adeudado) for f in facturas_c)
        
        # Calcular el valor total de los contratos de este contratista
        valor_total_contrato = sum(float(contrato.valor_total) for contrato in contratista.contratos)
        
        totales_contratistas[contratista.nombre] = {
            'valor_total_contrato': valor_total_contrato,
            'total_facturado': total_facturado,
            'total_rete_garantia': total_rete_garantia,
            'total_retenciones_ley': 0.0,
            'total_pagos': total_pagos,
            'saldo_adeudado': saldo_adeudado,
            'facturas': facturas_c
        }

    return render_template(
        "contratistas.html",
        usuario=usuario,
        notificaciones=notificaciones,
        frase=frase,
        frase_del_dia=frase,
        contratistas=lista_contratistas,
        totales_contratistas=totales_contratistas,
    )


# ─── POST /contratistas/crear ────────────────────
@contratistas_bp.route("/crear", methods=["POST"])
@login_required
@admin_oficina_required
def crear_contratista():
    try:
        nombre = request.form.get("nombre", "").strip()
        nit = request.form.get("nit", "").strip()
        telefono = request.form.get("telefono", "").strip()
        especialidad = request.form.get("especialidad", "").strip()
        estado = request.form.get("estado", "Activo")

        if not nombre:
            flash("El nombre/razón social es obligatorio.", "warning")
            return redirect(url_for("contratistas.index"))

        existe = Contratista.query.filter(Contratista.nombre.ilike(nombre)).first()
        if existe:
            flash("Ya existe un contratista con ese nombre.", "warning")
            return redirect(url_for("contratistas.index"))

        nuevo = Contratista(
            nombre=nombre, 
            nit=nit, 
            telefono=telefono,
            especialidad=especialidad,
            estado=estado
        )
        db.session.add(nuevo)
        db.session.commit()
        flash("Contratista registrado correctamente.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error al registrar contratista: {e}", "danger")

    return redirect(url_for("contratistas.index"))


# ─── POST /contratistas/editar/<int:id> ────────────────────
@contratistas_bp.route("/editar/<int:id>", methods=["POST"])
@login_required
@admin_oficina_required
def editar_contratista(id):
    try:
        contratista = Contratista.query.get(id)
        if not contratista:
            flash('Contratista no encontrado.', 'danger')
            return redirect(url_for('contratistas.index'))

        contratista.nombre = request.form.get("nombre", "").strip()
        contratista.nit = request.form.get("nit", "").strip()
        contratista.telefono = request.form.get("telefono", "").strip()
        contratista.especialidad = request.form.get("especialidad", "").strip()
        contratista.estado = request.form.get("estado", "Activo")

        db.session.commit()
        flash('Contratista actualizado exitosamente.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al actualizar contratista: {e}', 'danger')

    return redirect(url_for("contratistas.index"))


# ─── POST /contratistas/crear_contrato ────────────────────
@contratistas_bp.route("/crear_contrato", methods=["POST"])
@login_required
@admin_oficina_required
def crear_contrato_contratista():
    from models import ContratosContratista
    try:
        contratista_id = request.form.get('contratista_id')
        numero_contrato = request.form.get('numero_contrato')
        objeto = request.form.get('objeto')
        valor_total = parse_float_safe(request.form.get('valor_total'))
        
        fecha_inicio_str = request.form.get('fecha_inicio')
        fecha_fin_str = request.form.get('fecha_fin')
        fecha_inicio = dt.strptime(fecha_inicio_str, '%Y-%m-%d').date() if fecha_inicio_str else None
        fecha_fin = dt.strptime(fecha_fin_str, '%Y-%m-%d').date() if fecha_fin_str else None

        contrato_pdf = request.files.get('contrato_pdf')
        url_contrato = subir_archivo_supabase(contrato_pdf) if contrato_pdf else None
        
        contratista = Contratista.query.get(contratista_id)
        if not contratista:
            flash("Contratista no encontrado", "danger")
            return redirect(url_for('contratistas.index'))

        nuevo_contrato = ContratosContratista(
            contratista_id=contratista.id,
            numero_contrato=numero_contrato,
            objeto=objeto,
            valor_total=valor_total,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            archivo_pdf=url_contrato
        )

        db.session.add(nuevo_contrato)
        db.session.commit()
        flash('Contrato registrado exitosamente.', 'success')
    except Exception as e:
        db.session.rollback()
        print(f"Error al crear contrato contratista: {e}")
        flash(f'Error al registrar el contrato: {e}', 'danger')

    return redirect(url_for('contratistas.index'))


# ─── POST /contratistas/crear_factura ────────────────────
@contratistas_bp.route("/crear_factura", methods=["POST"])
@login_required
@admin_oficina_required
def crear_factura():
    try:
        fecha_factura_str = request.form.get("fecha_factura")
        fecha_vencimiento_str = request.form.get("fecha_vencimiento")
        fecha_pago_str = request.form.get("fecha_pago")

        fecha_factura = dt.strptime(fecha_factura_str, "%Y-%m-%d").date() if fecha_factura_str else None
        fecha_vencimiento = dt.strptime(fecha_vencimiento_str, "%Y-%m-%d").date() if fecha_vencimiento_str else None
        fecha_pago = dt.strptime(fecha_pago_str, "%Y-%m-%d").date() if fecha_pago_str else None

        # Archivos
        orden_compra_pdf = request.files.get("orden_compra_pdf")
        factura_pdf = request.files.get("factura_pdf")
        comprobante_pago = request.files.get("comprobante_pago")

        url_orden = subir_archivo_supabase(orden_compra_pdf)
        url_factura = subir_archivo_supabase(factura_pdf)
        url_pago = subir_archivo_supabase(comprobante_pago)

        factura = ContratistaFactura(
            nombre_contratista       = request.form.get("nombre_contratista", "").strip(),
            fecha_factura          = fecha_factura,
            plazo_dias             = int(request.form.get("plazo_dias") or 0),
            fecha_vencimiento      = fecha_vencimiento,
            valor_neto             = parse_float_safe(request.form.get("valor_neto")),
            porcentaje_iva         = parse_float_safe(request.form.get("porcentaje_iva")),
            valor_cancelado        = parse_float_safe(request.form.get("valor_cancelado")),
            retencion              = parse_float_safe(request.form.get("retencion")),
            fecha_pago             = fecha_pago,
            orden_compra_url       = url_orden,
            comprobante_compra_url = url_factura,
            banco_pago_url         = url_pago,
        )
        db.session.add(factura)
        db.session.commit()
        flash("Factura/Reporte registrada correctamente.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error al registrar la factura: {e}", "danger")

    return redirect(url_for("contratistas.index"))


# ─── POST /contratistas/editar_factura/<int:id> ──────────────
@contratistas_bp.route("/editar_factura/<int:id>", methods=["POST"])
@login_required
@admin_oficina_required
def editar_factura(id):
    factura = ContratistaFactura.query.get_or_404(id)

    try:
        fecha_pago_str = request.form.get("fecha_pago", "").strip()
        if "nombre_contratista" in request.form:
            factura.nombre_contratista = request.form.get("nombre_contratista").strip()
            
        fecha_factura_str = request.form.get("fecha_factura")
        if fecha_factura_str:
            factura.fecha_factura = dt.strptime(fecha_factura_str, "%Y-%m-%d").date()
            
        factura.plazo_dias = int(request.form.get("plazo_dias") or 0)
        
        fecha_vencimiento_str = request.form.get("fecha_vencimiento")
        if fecha_vencimiento_str:
            factura.fecha_vencimiento = dt.strptime(fecha_vencimiento_str, "%Y-%m-%d").date()
            
        factura.valor_neto = parse_float_safe(request.form.get("valor_neto"))
        factura.porcentaje_iva = parse_float_safe(request.form.get("porcentaje_iva"))
        factura.valor_cancelado = parse_float_safe(request.form.get("valor_cancelado"))
        factura.retencion = parse_float_safe(request.form.get("retencion"))
        
        if fecha_pago_str:
            factura.fecha_pago = dt.strptime(fecha_pago_str, "%Y-%m-%d").date()
        else:
            factura.fecha_pago = None
        
        # Archivos
        nuevo_archivo_oc = request.files.get("orden_compra_pdf")
        if nuevo_archivo_oc and nuevo_archivo_oc.filename != '':
            url_oc = subir_archivo_supabase(nuevo_archivo_oc)
            if url_oc:
                factura.orden_compra_url = url_oc

        nuevo_archivo_factura = request.files.get("factura_pdf")
        if nuevo_archivo_factura and nuevo_archivo_factura.filename != '':
            url_factura = subir_archivo_supabase(nuevo_archivo_factura)
            if url_factura:
                factura.comprobante_compra_url = url_factura

        nuevo_archivo_comprobante = request.files.get("comprobante_pago")
        if nuevo_archivo_comprobante and nuevo_archivo_comprobante.filename != '':
            url_comprobante = subir_archivo_supabase(nuevo_archivo_comprobante)
            if url_comprobante:
                factura.banco_pago_url = url_comprobante

        db.session.commit()
        flash("Factura actualizada correctamente.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error al actualizar: {e}", "danger")

    return redirect(url_for("contratistas.index"))


# ─── POST /contratistas/eliminar_factura/<int:id> ────────────
@contratistas_bp.route("/eliminar_factura/<int:id>", methods=["POST"])
@login_required
@admin_oficina_required
def eliminar_factura(id):
    factura = ContratistaFactura.query.get_or_404(id)
    try:
        db.session.delete(factura)
        db.session.commit()
        flash("Factura eliminada correctamente.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error al eliminar: {e}", "danger")
    return redirect(url_for("contratistas.index"))
