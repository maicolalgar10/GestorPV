from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session
from datetime import datetime as dt
import os
import uuid
import re
from werkzeug.utils import secure_filename

from models import db, Usuarios, Notificaciones, Contratista, ContratistaFactura, ContratosContratista, ProgramacionPagoContratista
from supabase_client import supabase
from decorators import login_required, admin_oficina_required
from frases import frase_del_dia

contratistas_bp = Blueprint("contratistas", __name__, url_prefix='/contratistas')

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'pdf', 'png', 'jpg', 'jpeg', 'webp'}

def limpiar_monto(val):
    if not val:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)

    texto = str(val).strip().replace('$', '').replace(' ', '')

    # Formato CO: 1.641.589,48
    if '.' in texto and ',' in texto:
        texto = texto.replace('.', '').replace(',', '.')
    elif ',' in texto:
        texto = texto.replace(',', '.')
    elif '.' in texto:
        # Si tiene puntos de miles (ej: 1.641.589)
        partes = texto.split('.')
        if len(partes) > 2 or (len(partes) == 2 and len(partes[1]) == 3):
            texto = texto.replace('.', '')

    try:
        return float(texto)
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

    try:
        lista_contratistas = Contratista.query.order_by(Contratista.nombre.asc()).all()
    except Exception as e:
        db.session.rollback()
        lista_contratistas = []
        flash(f"Error cargando contratistas: {str(e)}", "danger")

    try:
        lista_contratos = ContratosContratista.query.join(Contratista).order_by(Contratista.nombre.asc(), ContratosContratista.objeto.asc()).all()
    except Exception as e:
        db.session.rollback()
        lista_contratos = []
        flash(f"Error cargando contratos: {str(e)}", "danger")

    deuda_por_contratista = {c.id: 0.0 for c in lista_contratistas}
    totales_contratos = {}
    
    try:
        for contrato in lista_contratos:
            facturas_c = getattr(contrato, 'facturas', [])
            total_facturado = sum(float(getattr(f, 'valor_total', 0.0) or 0) for f in facturas_c)
            total_rete_garantia = sum(float(getattr(f, 'retegarantia_pesos', 0.0) or 0) for f in facturas_c)
            total_retenciones_ley = sum(float(getattr(f, 'retencion_pesos', 0.0) or 0) for f in facturas_c)
            total_pagos = sum(float(getattr(f, 'valor_cancelado', 0.0) or 0) for f in facturas_c)
            saldo_adeudado = float(getattr(contrato, 'valor_total', 0.0) or 0) - total_retenciones_ley - total_pagos
            
            totales_contratos[contrato.id] = {
                'valor_total_contrato': float(getattr(contrato, 'valor_total', 0.0) or 0),
                'total_facturado': total_facturado,
                'total_rete_garantia': total_rete_garantia,
                'total_retenciones_ley': total_retenciones_ley,
                'total_pagos': total_pagos,
                'saldo_adeudado': saldo_adeudado,
                'facturas': sorted(facturas_c, key=lambda f: getattr(f, 'fecha_factura', dt.today().date()), reverse=True) if facturas_c else []
            }

            if contrato.contratista_id in deuda_por_contratista:
                deuda_por_contratista[contrato.contratista_id] += saldo_adeudado
    except Exception as e:
        db.session.rollback()
        print(f"Error calculando totales contratos: {e}")
        # Continue gracefully

    try:
        pagos_programados = ProgramacionPagoContratista.query.order_by(ProgramacionPagoContratista.fecha_programada.asc()).all()
    except Exception as e:
        db.session.rollback()
        pagos_programados = []
        print(f"Error cargando pagos programados: {e}")

    return render_template(
        "contratistas.html",
        usuario=usuario,
        notificaciones=notificaciones,
        frase=frase,
        frase_del_dia=frase,
        contratistas=lista_contratistas,
        contratos=lista_contratos,
        totales_contratos=totales_contratos,
        deuda_por_contratista=deuda_por_contratista,
        pagos_programados=pagos_programados,
    )

@contratistas_bp.route("/programar_pago", methods=["POST"])
@login_required
@admin_oficina_required
def programar_pago():
    try:
        contratista_id = request.form.get("contratista_id")
        fecha_raw = request.form.get("fecha_programada")
        monto_raw = request.form.get("monto", "0")
        observacion = request.form.get("observacion", "").strip()

        fecha_programada = dt.strptime(fecha_raw, "%Y-%m-%d").date() if fecha_raw else None
        
        monto_limpio = str(monto_raw).replace('$', '').replace(' ', '')
        if ',' in monto_limpio and '.' in monto_limpio:
            monto_limpio = monto_limpio.replace('.', '').replace(',', '.')
        elif ',' in monto_limpio:
            monto_limpio = monto_limpio.replace(',', '.')
        elif '.' in monto_limpio:
            partes = monto_limpio.split('.')
            if len(partes[-1]) == 3:
                monto_limpio = monto_limpio.replace('.', '')
        monto = float(monto_limpio) if monto_limpio else 0.0

        if not contratista_id or not fecha_programada or monto <= 0:
            flash("Datos inválidos para programar el pago.", "danger")
            return redirect(url_for("contratistas.index"))

        nuevo_pago = ProgramacionPagoContratista(
            contratista_id=contratista_id,
            fecha_programada=fecha_programada,
            monto=monto,
            observacion=observacion,
            estado='Programado'
        )
        db.session.add(nuevo_pago)
        db.session.commit()
        flash("Pago programado correctamente.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error al programar el pago: {str(e)}", "danger")
    return redirect(url_for("contratistas.index"))

@contratistas_bp.route("/programacion/cambiar_estado/<int:id>", methods=["POST"])
@login_required
@admin_oficina_required
def cambiar_estado(id):
    pago = ProgramacionPagoContratista.query.get_or_404(id)
    try:
        nuevo_estado = request.form.get("estado")
        if nuevo_estado in ['Programado', 'Realizado', 'Cancelado']:
            pago.estado = nuevo_estado
            db.session.commit()
            flash("Estado del pago actualizado.", "success")
        else:
            flash("Estado inválido.", "danger")
    except Exception as e:
        db.session.rollback()
        flash(f"Error al cambiar el estado: {str(e)}", "danger")
    return redirect(url_for("contratistas.index"))

@contratistas_bp.route("/programacion_pago/editar/<int:id>", methods=["POST"])
@login_required
@admin_oficina_required
def editar_programacion(id):
    pago = ProgramacionPagoContratista.query.get_or_404(id)
    try:
        fecha_raw = request.form.get("fecha_programada")
        monto_raw = request.form.get("monto", "0")
        observacion = request.form.get("observacion", "").strip()

        fecha_programada = dt.strptime(fecha_raw, "%Y-%m-%d").date() if fecha_raw else None

        monto_limpio = str(monto_raw).replace('$', '').replace(' ', '')
        if ',' in monto_limpio and '.' in monto_limpio:
            monto_limpio = monto_limpio.replace('.', '').replace(',', '.')
        elif ',' in monto_limpio:
            monto_limpio = monto_limpio.replace(',', '.')
        elif '.' in monto_limpio:
            partes = monto_limpio.split('.')
            if len(partes[-1]) == 3:
                monto_limpio = monto_limpio.replace('.', '')
        monto = float(monto_limpio) if monto_limpio else 0.0

        if not fecha_programada or monto <= 0:
            flash("Datos inválidos para editar la programación.", "danger")
            return redirect(url_for("contratistas.index"))

        pago.fecha_programada = fecha_programada
        pago.monto = monto
        pago.observacion = observacion
        db.session.commit()
        flash("Programación de pago actualizada correctamente.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error al editar la programación: {str(e)}", "danger")
    return redirect(url_for("contratistas.index"))

@contratistas_bp.route("/programacion/eliminar/<int:id>", methods=["POST"])
@login_required
@admin_oficina_required
def eliminar_programacion(id):
    pago = ProgramacionPagoContratista.query.get_or_404(id)
    try:
        db.session.delete(pago)
        db.session.commit()
        flash("Programación de pago eliminada.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error al eliminar la programación: {str(e)}", "danger")
    return redirect(url_for("contratistas.index"))


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
        valor_total = limpiar_monto(request.form.get('valor_total'))
        
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


# ─── POST /contratistas/editar_contrato/<id> ─────────────
@contratistas_bp.route("/editar_contrato/<int:id>", methods=["POST"])
@login_required
@admin_oficina_required
def editar_contrato(id):
    try:
        contrato = ContratosContratista.query.get_or_404(id)
        
        contrato.numero_contrato = request.form.get('numero_contrato', contrato.numero_contrato)
        contrato.objeto = request.form.get('objeto', contrato.objeto)
        
        val_total_str = request.form.get('valor_total')
        if val_total_str:
            contrato.valor_total = limpiar_monto(val_total_str)
            
        f_inicio = request.form.get('fecha_inicio')
        if f_inicio:
            contrato.fecha_inicio = dt.strptime(f_inicio, '%Y-%m-%d').date()
            
        f_fin = request.form.get('fecha_fin')
        if f_fin:
            contrato.fecha_fin = dt.strptime(f_fin, '%Y-%m-%d').date()
            
        contrato_pdf = request.files.get('contrato_pdf')
        if contrato_pdf and contrato_pdf.filename:
            url_contrato = subir_archivo_supabase(contrato_pdf)
            if url_contrato:
                contrato.archivo_pdf = url_contrato
                
        db.session.commit()
        flash("Contrato actualizado exitosamente.", "success")
    except Exception as e:
        db.session.rollback()
        print(f"Error al editar contrato: {e}")
        flash(f"Error al editar el contrato: {e}", "danger")
        
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

        def parse_pct(val, default=0.0):
            if val is None or str(val).strip() == "": return default
            try:
                return float(str(val).replace(',', '.').strip())
            except ValueError:
                return default

        factura = ContratistaFactura(
            nombre_contratista       = request.form.get("nombre_contratista", "").strip(),
            contrato_id              = request.form.get("contrato_id"),
            fecha_factura          = fecha_factura,
            plazo_dias             = int(request.form.get("plazo_dias") or 0),
            fecha_vencimiento      = fecha_vencimiento,
            valor_neto             = limpiar_monto(request.form.get("valor_neto")),
                        porcentaje_iva         = parse_pct(request.form.get("porcentaje_iva")),
            valor_cancelado        = limpiar_monto(request.form.get("valor_cancelado")),
            retencion              = parse_pct(request.form.get("retencion")),
            porcentaje_retegarantia= parse_pct(request.form.get("retegarantia")),
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
            
        if "contrato_id" in request.form:
            factura.contrato_id = request.form.get("contrato_id")
            
        fecha_factura_str = request.form.get("fecha_factura")
        if fecha_factura_str:
            factura.fecha_factura = dt.strptime(fecha_factura_str, "%Y-%m-%d").date()
            
        factura.plazo_dias = int(request.form.get("plazo_dias") or 0)
        
        fecha_vencimiento_str = request.form.get("fecha_vencimiento")
        if fecha_vencimiento_str:
            factura.fecha_vencimiento = dt.strptime(fecha_vencimiento_str, "%Y-%m-%d").date()
            
        def parse_pct(val, default=0.0):
            if val is None or str(val).strip() == "": return default
            try:
                return float(str(val).replace(',', '.').strip())
            except ValueError:
                return default

        factura.valor_neto = limpiar_monto(request.form.get("valor_neto"))
        factura.porcentaje_iva = parse_pct(request.form.get("porcentaje_iva"))
        factura.valor_cancelado = limpiar_monto(request.form.get("valor_cancelado"))
        factura.retencion = parse_pct(request.form.get("retencion"))
        factura.porcentaje_retegarantia = parse_pct(request.form.get("retegarantia"))
        
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
    return redirect(request.form.get("redirect_to") or url_for("contratistas.index"))


# ─── POST /contratistas/subfactura/crear ──────────────────────
@contratistas_bp.route("/subfactura/crear", methods=["POST"])
@login_required
@admin_oficina_required
def crear_contratista_subfactura():
    from models import ContratistaFactura, ContratistaSubFactura
    from datetime import datetime as dt
    try:
        factura_padre_id = request.form.get("factura_padre_id")
        factura_padre = ContratistaFactura.query.get_or_404(factura_padre_id)

        numero = request.form.get("numero_subfactura", "").strip()
        fecha_str = request.form.get("fecha_subfactura")
        fecha = dt.strptime(fecha_str, "%Y-%m-%d").date() if fecha_str else None
        concepto = request.form.get("concepto", "").strip()
        
        valor_limpio = limpiar_monto(request.form.get("valor"))
        try:
            valor = float(valor_limpio)
        except ValueError:
            valor = 0.0

        pdf_subfactura = request.files.get("pdf_subfactura")
        pdf_url = subir_archivo_supabase(pdf_subfactura)

        nueva_sub = ContratistaSubFactura(
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
        total_sub = db.session.query(db.func.sum(ContratistaSubFactura.valor)).filter_by(factura_id=factura_padre.id).scalar() or 0.0
        factura_padre.valor_cancelado = total_sub
        db.session.commit()

        flash("Sub-factura registrada correctamente.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error al crear sub-factura: {e}", "danger")

    redirect_to = request.form.get("redirect_to")
    if redirect_to == "facturas_contratista" and 'factura_padre' in locals() and factura_padre:
        return redirect(url_for("contratistas.facturas_contratista", nombre_contratista=factura_padre.nombre_contratista))
    return redirect(url_for("contratistas.index"))


# ─── POST /contratistas/subfactura/eliminar/<id> ──────────────
@contratistas_bp.route("/subfactura/eliminar/<int:id>", methods=["POST"])
@login_required
@admin_oficina_required
def eliminar_contratista_subfactura(id):
    from models import ContratistaSubFactura
    try:
        sub = ContratistaSubFactura.query.get(id)
        if not sub:
            flash("Sub-factura no encontrada.", "danger")
            return redirect(url_for("contratistas.index"))

        factura_padre = sub.factura_padre
        db.session.delete(sub)
        db.session.commit()

        # Recalcular valor_cancelado
        total_sub = db.session.query(db.func.sum(ContratistaSubFactura.valor)).filter_by(factura_id=factura_padre.id).scalar() or 0.0
        factura_padre.valor_cancelado = total_sub
        db.session.commit()

        flash("Sub-factura eliminada.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error al eliminar sub-factura: {e}", "danger")

    redirect_to = request.form.get("redirect_to")
    if redirect_to == "facturas_contratista" and 'factura_padre' in locals() and factura_padre:
        return redirect(url_for("contratistas.facturas_contratista", nombre_contratista=factura_padre.nombre_contratista))
    return redirect(url_for("contratistas.index"))
