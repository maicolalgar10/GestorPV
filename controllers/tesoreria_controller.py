from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from decorators import login_required, admin_oficina_required
from models import db, Contrato, Cotizacion, Movimientos, Bancos
from werkzeug.utils import secure_filename
from decimal import Decimal
import os
import threading
from datetime import datetime
import requests
from requests.auth import HTTPBasicAuth
import uuid
from supabase_client import supabase
from services.pluggy_service import PluggyService

tesoreria_bp = Blueprint("tesoreria", __name__, url_prefix="/tesoreria")

def allowed_support_file(filename):
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "pdf"}
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@tesoreria_bp.route("/contratos/desde-cotizacion/<int:id_cotizacion>", methods=["POST"])
@admin_oficina_required
def crear_contrato_desde_cotizacion(id_cotizacion):
    cotizacion = Cotizacion.query.get_or_404(id_cotizacion)

    if cotizacion.estado != "ACEPTADA":
        flash("Solo se puede formalizar contrato de una cotización aceptada", "danger")
        return redirect(request.referrer)

    if cotizacion.contrato:
        flash("Esta cotización ya tiene un contrato asociado", "warning")
        return redirect(request.referrer)

    try:
        valor_total = Decimal(request.form.get("valor_total", 0))
        anticipo_porcentaje = Decimal(request.form.get("anticipo_porcentaje", 0))
        retencion_garantia_porcentaje = Decimal(request.form.get("retencion_garantia_porcentaje", 0))
        banco_nombre = request.form.get("banco_nombre")

        if valor_total <= 0:
            flash("El valor total del contrato debe ser mayor a 0", "danger")
            return redirect(request.referrer)

        if anticipo_porcentaje < 0 or anticipo_porcentaje > 100:
            flash("El porcentaje de anticipo debe estar entre 0 y 100", "danger")
            return redirect(request.referrer)
            
        if retencion_garantia_porcentaje < 0 or retencion_garantia_porcentaje > 100:
            flash("El porcentaje de retención debe estar entre 0 y 100", "danger")
            return redirect(request.referrer)

        # CÁLCULO DEL ANTICIPO TEÓRICO
        valor_anticipo = (valor_total * anticipo_porcentaje) / Decimal("100")

        contrato = Contrato(
            cotizacion_id=cotizacion.id,
            cliente=cotizacion.cliente,
            proyecto=cotizacion.proyecto,
            valor_total=valor_total,
            estado="activo",
            total_sin_iva=0,
            anticipo_porcentaje=anticipo_porcentaje,
            valor_anticipo=valor_anticipo,
            retencion_garantia_porcentaje=retencion_garantia_porcentaje
        )

        db.session.add(contrato)
        db.session.flush() # Para obtener el ID del contrato

        # Crear el movimiento inicial de anticipo si aplica
        if valor_anticipo > 0:
            if not banco_nombre:
                flash("Debe proporcionar un nombre de banco para registrar el anticipo", "danger")
                db.session.rollback()
                return redirect(request.referrer)

            movimiento_anticipo = Movimientos(
                contrato_id=contrato.id,
                banco=banco_nombre,
                tipo='INGRESO',
                categoria='anticipo',
                valor_bruto=valor_anticipo,
                amortizacion_anticipo=0, # Un anticipo no se amortiza a sí mismo
                retencion_garantia=0, # Un anticipo normalmente no tiene retención (o se aplica luego en las actas)
                valor_neto=valor_anticipo,
                fecha_movimiento=datetime.utcnow().date(),
                numero_documento="Anticipo Inicial",
            )
            db.session.add(movimiento_anticipo)

        db.session.commit()

        flash("Contrato y configuración inicial guardados exitosamente ✅", "success")
        return redirect(url_for('tesoreria.ver_tesoreria'))

    except Exception as e:
        db.session.rollback()
        print("⚠️ Error al crear contrato:", e)
        flash("Hubo un error al generar el contrato", "danger")
        return redirect(request.referrer)

@tesoreria_bp.route("/contratos/editar/<int:id_contrato>", methods=["POST"])
@admin_oficina_required
def editar_contrato(id_contrato):
    contrato = Contrato.query.get_or_404(id_contrato)
    
    try:
        nuevo_valor_total = Decimal(request.form.get("valor_total", contrato.valor_total))
        nuevo_anticipo_porc = Decimal(request.form.get("anticipo_porcentaje", contrato.anticipo_porcentaje))
        nueva_retencion_porc = Decimal(request.form.get("retencion_garantia_porcentaje", contrato.retencion_garantia_porcentaje))

        if nuevo_valor_total <= 0:
            flash("El valor total del contrato debe ser mayor a 0", "danger")
            return redirect(request.referrer)

        if nuevo_anticipo_porc < 0 or nuevo_anticipo_porc > 100:
            flash("El porcentaje de anticipo debe estar entre 0 y 100", "danger")
            return redirect(request.referrer)
            
        if nueva_retencion_porc < 0 or nueva_retencion_porc > 100:
            flash("El porcentaje de retención debe estar entre 0 y 100", "danger")
            return redirect(request.referrer)

        # Recalcular anticipo
        nuevo_valor_anticipo = (nuevo_valor_total * nuevo_anticipo_porc) / Decimal("100")
        diferencia_anticipo = nuevo_valor_anticipo - (contrato.valor_anticipo or Decimal("0"))

        # Actualizar contrato
        contrato.valor_total = nuevo_valor_total
        contrato.anticipo_porcentaje = nuevo_anticipo_porc
        contrato.retencion_garantia_porcentaje = nueva_retencion_porc
        contrato.valor_anticipo = nuevo_valor_anticipo

        # Sincronizar Tesorería (Movimientos)
        movimiento_anticipo = Movimientos.query.filter_by(contrato_id=contrato.id, categoria='anticipo').first()
        
        if movimiento_anticipo:
            movimiento_anticipo.valor_bruto = nuevo_valor_anticipo
            movimiento_anticipo.valor_neto = nuevo_valor_anticipo

        db.session.commit()
        flash("Contrato y Tesorería actualizados exitosamente ✅", "success")
    except Exception as e:
        db.session.rollback()
        print("⚠️ Error al editar contrato:", e)
        flash("Hubo un error al actualizar el contrato", "danger")
        
    return redirect(request.referrer)

@tesoreria_bp.route("/")
@admin_oficina_required
def ver_tesoreria():
    contratos = Contrato.query.order_by(Contrato.id.desc()).all()
    bancos = Bancos.query.all()
    movimientos = Movimientos.query.order_by(Movimientos.fecha_movimiento.desc()).all()

    colors = ['#00D4AA', '#4F8EF7', '#F7C94F', '#A3E635', '#B47AE5', '#FF6B6B']
    contratos_list = []
    for i, c in enumerate(contratos):
        ingresos = [m for m in c.movimientos if m.tipo == 'INGRESO' and m.categoria in ['acta', 'anticipo']]
        facturado_bruto = sum((m.valor_bruto or 0) for m in ingresos)
        retencion_total = sum((m.retencion_garantia or 0) for m in ingresos)
        amortizacion_total = sum((m.amortizacion_anticipo or 0) for m in ingresos)
        
        contratos_list.append({
            "id": str(c.id),
            "name": c.proyecto or 'General',
            "client": c.cliente or 'N/A',
            "value": float(c.valor_total or 0),
            "received": float(facturado_bruto),
            "pending": float((c.valor_total or 0) - facturado_bruto),
            "status": c.estado,
            "advance": round((float(facturado_bruto) / float(c.valor_total)) * 100) if c.valor_total and float(c.valor_total) > 0 else 0,
            "color": colors[i % len(colors)],
            "amortizacion_acumulada": float(amortizacion_total),
            "retencion_acumulada": float(retencion_total),
            "porcentaje_anticipo": float(c.anticipo_porcentaje or 0),
            "porcentaje_retencion": float(c.retencion_garantia_porcentaje or 0)
        })

    movimientos_list = []
    for m in movimientos:
        movimientos_list.append({
            "id": m.id,
            "date": m.fecha_movimiento.strftime('%Y-%m-%d') if m.fecha_movimiento else '',
            "concept": m.numero_documento or 'Movimiento',
            "contract": str(m.contrato_id) if m.contrato_id else 'GENERAL',
            "type": m.tipo.lower(),
            "amount": float(m.valor_neto or 0) if m.tipo == 'INGRESO' else float(-(m.valor_neto or 0)),
            "bank": m.banco or 'N/A',
            "category": m.categoria,
            "archivo_soporte": m.archivo_soporte
        })

    bancos_list = []
    for b in bancos:
        bancos_list.append({
            "id": b.id,
            "name": b.nombre_banco,
            "balance": float(b.saldo_actual or 0),
            "account": b.numero_cuenta,
            "color": b.color or '#004481',
            "pluggy_item_id": b.pluggy_item_id
        })

    return render_template("tesoreria.html", 
                           contratos_json=contratos_list, 
                           movimientos_json=movimientos_list, 
                           bancos_json=bancos_list)

@tesoreria_bp.route("/bancos")
@admin_oficina_required
def ver_bancos():
    bancos = Bancos.query.all()
    bancos_list = []
    for b in bancos:
        bancos_list.append({
            "id": b.id,
            "name": b.nombre_banco,
            "balance": float(b.saldo_actual or 0),
            "account": b.numero_cuenta,
            "color": b.color or '#004481',
            "pluggy_item_id": b.pluggy_item_id
        })
    return render_template("bancos.html", bancos_json=bancos_list, contratos_json=[], movimientos_json=[])

@tesoreria_bp.route("/movimiento/registrar", methods=["POST"])
@admin_oficina_required
def registrar_movimiento():
    # Este endpoint recibe un movimiento general. Puede o no tener contrato
    contrato_id_raw = request.form.get("contrato_id")
    banco_nombre = request.form.get("banco_nombre")
    
    try:
        contrato = Contrato.query.get(int(contrato_id_raw)) if contrato_id_raw else None
        
        tipo = request.form.get("tipo") # INGRESO o EGRESO
        if tipo:
            tipo = tipo.upper()
        categoria = request.form.get("categoria") # acta, nomina, anticipo...
        valor_bruto = Decimal(request.form.get("valor_bruto", 0))
        fecha_str = request.form.get("fecha_movimiento")
        numero = request.form.get("numero_documento")
        archivo = request.files.get("archivo_soporte")

        if valor_bruto <= 0:
            flash("El valor bruto debe ser mayor a 0", "danger")
            return redirect(request.referrer)

        # Lógica de Amortización para Actas
        amortizacion = Decimal("0")
        retencion = Decimal("0")
        
        if categoria == "acta" and contrato and tipo == "INGRESO":
            amortizacion = (valor_bruto * contrato.anticipo_porcentaje) / Decimal("100")
            retencion = (valor_bruto * contrato.retencion_garantia_porcentaje) / Decimal("100")
            
        valor_neto = valor_bruto - amortizacion - retencion
        
        # Subida de archivo
        nombre_archivo = None
        if archivo and archivo.filename:
            if not allowed_support_file(archivo.filename):
                flash("Tipo de archivo de soporte no permitido por razones de seguridad.", "danger")
                return redirect(request.referrer)

            original_filename = secure_filename(archivo.filename)
            ext = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else 'pdf'
            filename = f"movimiento_{categoria}_{numero}_{uuid.uuid4().hex}.{ext}"
            
            file_bytes = archivo.read()
            
            if supabase:
                # Subir a Supabase
                supabase.storage.from_("tesoreria").upload(
                    path=filename, 
                    file=file_bytes, 
                    file_options={"content-type": archivo.content_type}
                )
                nombre_archivo = supabase.storage.from_("tesoreria").get_public_url(filename)
            else:
                upload_path = os.path.join("static", "uploads", "tesoreria")
                os.makedirs(upload_path, exist_ok=True)
                with open(os.path.join(upload_path, filename), "wb") as f:
                    f.write(file_bytes)
                nombre_archivo = filename
            
        nuevo_movimiento = Movimientos(
            contrato_id=contrato.id if contrato else None,
            banco=banco_nombre,
            tipo=tipo,
            categoria=categoria,
            valor_bruto=valor_bruto,
            amortizacion_anticipo=amortizacion,
            retencion_garantia=retencion,
            valor_neto=valor_neto,
            fecha_movimiento=datetime.strptime(fecha_str, "%Y-%m-%d").date(),
            numero_documento=numero,
            archivo_soporte=nombre_archivo
        )
        
        db.session.add(nuevo_movimiento)
            
        db.session.commit()
        flash("Movimiento registrado correctamente ✅", "success")
        
    except Exception as e:
        db.session.rollback()
        print("⚠️ Error:", e)
        flash("Error al registrar movimiento", "danger")

    return redirect(request.referrer)

@tesoreria_bp.route("/bancos/crear", methods=["POST"])
@admin_oficina_required
def crear_banco():
    nombre_banco = request.form.get("nombre_banco")
    numero_cuenta = request.form.get("numero_cuenta")
    saldo_inicial = Decimal(request.form.get("saldo_inicial", 0))
    color = request.form.get("color", "#004481")

    if not nombre_banco or not numero_cuenta:
        flash("El nombre del banco y número de cuenta son obligatorios", "danger")
        return redirect(request.referrer)

    try:
        nuevo_banco = Bancos(
            nombre_banco=nombre_banco,
            numero_cuenta=numero_cuenta,
            saldo_actual=saldo_inicial,
            color=color
        )
        db.session.add(nuevo_banco)
        db.session.flush() # Para obtener el ID del banco

        if saldo_inicial > 0:
            movimiento_inicial = Movimientos(
                contrato_id=None,
                banco=nuevo_banco.nombre_banco,
                tipo='INGRESO',
                categoria='saldo_inicial',
                valor_bruto=saldo_inicial,
                amortizacion_anticipo=0,
                retencion_garantia=0,
                valor_neto=saldo_inicial,
                fecha_movimiento=datetime.utcnow().date(),
                numero_documento="SALDO INICIAL",
                archivo_soporte=None
            )
            db.session.add(movimiento_inicial)

        db.session.commit()
        flash("Banco registrado exitosamente ✅", "success")

    except Exception as e:
        db.session.rollback()
        print("⚠️ Error al crear banco:", e)
        flash("Hubo un error al registrar el banco", "danger")

    return redirect(request.referrer)

@tesoreria_bp.route("/api/resumen")
@admin_oficina_required
def api_tesoreria_resumen():
    try:
        # Sumar saldos de todos los bancos
        bancos = Bancos.query.all()
        saldo_consolidado = sum(b.saldo_actual for b in bancos)
        
        # Contratos Activos
        contratos = Contrato.query.filter_by(estado="activo").all()
        total_facturado_bruto = Decimal("0")
        total_contratos_valor = Decimal("0")
        
        for c in contratos:
            total_contratos_valor += c.valor_total
            # Sumar lo ya ejecutado/facturado (actas aprobadas/pagadas)
            ingresos_contrato = sum(
                m.valor_bruto for m in c.movimientos if m.tipo == "INGRESO" and m.categoria in ["acta", "anticipo"]
            )
            total_facturado_bruto += ingresos_contrato
            
        pendiente_facturar = total_contratos_valor - total_facturado_bruto
        
        return jsonify({
            "status": "success",
            "data": {
                "saldo_consolidado": str(saldo_consolidado),
                "contratos_activos_valor_total": str(total_contratos_valor),
                "total_facturado_bruto": str(total_facturado_bruto),
                "pendiente_facturar": str(pendiente_facturar)
            }
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@tesoreria_bp.route("/api/bancos/<int:id_banco>/sincronizar_en_vivo", methods=["GET"])
@admin_oficina_required
def sincronizar_banco_en_vivo(id_banco):
    banco = Bancos.query.get_or_404(id_banco)
    
    # Verificamos si el banco tiene un pluggy_item_id
    if not banco.pluggy_item_id:
        return jsonify({
            "status": "error",
            "code": "MISSING_LINK",
            "message": "Este banco aún no está vinculado con Pluggy. Por favor, inicie el proceso de vinculación."
        }), 400

    try:
        pluggy = PluggyService()
        item_id = banco.pluggy_item_id

        # 1. Obtener Cuentas
        accounts_data = pluggy.get_accounts(item_id)
        
        if not accounts_data:
            return jsonify({
                "status": "sin_datos",
                "saldo_real": float(banco.saldo_actual or 0),
                "transacciones_bancarias": []
            }), 200
            
        cuenta = accounts_data[0]
        # Saldo en Pluggy
        saldo_real_banco = cuenta.get("balance", float(banco.saldo_actual or 0))

        # Actualizar numero_cuenta si está vacío
        if not banco.numero_cuenta or banco.numero_cuenta == "":
            numero = cuenta.get("number") or ""
            if numero:
                banco.numero_cuenta = numero
                db.session.commit()

        # 2. Obtener Transacciones
        from datetime import timedelta
        date_from = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d")
        
        transactions_data = pluggy.get_transactions(cuenta.get("id"), date_from=date_from)
        
        transacciones_reales = []
        for tx in transactions_data:
            transacciones_reales.append({
                "id": tx.get("id"),
                "amount": tx.get("amount"),
                "type": tx.get("type"), # 'CREDIT' o 'DEBIT' en Pluggy
                "status": tx.get("status"), # 'POSTED' o 'PENDING'
                "description": tx.get("description", "Sin descripción"),
                "value_date": tx.get("date"),
                "category": tx.get("category", "OTHER")
            })

        return jsonify({
            "status": "success",
            "data": {
                "saldo_real": saldo_real_banco,
                "ultima_sync": datetime.utcnow().isoformat(),
                "transacciones_bancarias": transacciones_reales
            }
        }), 200

    except Exception as e:
        print(f"⚠️ Error en sincronización Pluggy: {e}")
        return jsonify({
            "status": "error",
            "message": f"Error al sincronizar con Pluggy: {str(e)}"
        }), 500

@tesoreria_bp.route("/api/bancos/<int:id_banco>/vincular", methods=["POST"])
@admin_oficina_required
def vincular_banco_pluggy(id_banco):
    banco = Bancos.query.get_or_404(id_banco)
    
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "No se enviaron datos JSON"}), 400
        
    item_id = data.get("item_id")
    connector_id = data.get("connector_id")
    
    if not item_id:
        return jsonify({"status": "error", "message": "El item_id es requerido"}), 400
        
    try:
        banco.pluggy_item_id = item_id
        if connector_id:
            banco.pluggy_connector_id = connector_id
            
        db.session.commit()
        
        return jsonify({
            "status": "success",
            "message": "Banco vinculado correctamente a Pluggy",
            "item_id": item_id
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"⚠️ Error al vincular banco: {e}")
        return jsonify({
            "status": "error",
            "message": "Error interno al guardar la vinculación"
        }), 500

@tesoreria_bp.route("/api/bancos/vincular_nuevo", methods=["POST"])
@admin_oficina_required
def vincular_banco_nuevo_pluggy():
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "No se enviaron datos JSON"}), 400
        
    item_id = data.get("item_id")
    connector_id = data.get("connector_id")
    
    if not item_id or not connector_id:
        return jsonify({"status": "error", "message": "El item_id y connector_id son requeridos"}), 400
        
    try:
        nuevo_banco = Bancos(
            nombre_banco=connector_id,
            numero_cuenta="",
            saldo_actual=0,
            color="#00D4AA",
            pluggy_item_id=item_id,
            pluggy_connector_id=connector_id
        )
        db.session.add(nuevo_banco)
        db.session.commit()
        
        return jsonify({
            "status": "success",
            "message": "Banco vinculado y creado correctamente desde Pluggy",
            "banco_id": nuevo_banco.id
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"⚠️ Error al crear banco vía Pluggy: {e}")
        return jsonify({
            "status": "error",
            "message": "Error interno al guardar la vinculación"
        }), 500

@tesoreria_bp.route("/api/bancos/<int:id_banco>", methods=["DELETE"])
@admin_oficina_required
def eliminar_banco(id_banco):
    banco = Bancos.query.get_or_404(id_banco)
    
    try:
        # 1. Eliminar item en Pluggy si existe
        if banco.pluggy_item_id:
            try:
                pluggy = PluggyService()
                pluggy.delete_item(banco.pluggy_item_id)
            except Exception as e:
                print(f"⚠️ Aviso: no se pudo eliminar el item en Pluggy: {e}")
        
        # 2. Eliminar de BD (Cascade elimina movimientos automáticamente)
        db.session.delete(banco)
        db.session.commit()
        
        return jsonify({
            "status": "success",
            "message": "Banco y movimientos eliminados correctamente."
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"⚠️ Error al eliminar banco: {e}")
        return jsonify({
            "status": "error",
            "message": "Error interno al eliminar el banco"
        }), 500

@tesoreria_bp.route("/api/pluggy/token", methods=["POST"])
@admin_oficina_required
def obtener_token_pluggy():
    try:
        pluggy = PluggyService()
        token = pluggy.create_connect_token()
        
        return jsonify({
            "status": "success",
            "access_token": token
        }), 200
        
    except Exception as e:
        print(f"⚠️ Error al obtener connect token de Pluggy: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

def _process_pluggy_webhook(app_context, data):
    """
    Procesa el webhook en segundo plano usando el contexto de la aplicación.
    Solo actualiza el saldo del banco (Visor financiero independiente).
    """
    with app_context:
        try:
            event = data.get("event")
            item_id = data.get("itemId")
            
            if event == "item/updated" and item_id:
                # Buscar el banco asociado a este item_id
                banco = Bancos.query.filter_by(pluggy_item_id=item_id).first()
                if banco:
                    pluggy = PluggyService()
                    accounts_data = pluggy.get_accounts(item_id)
                    if accounts_data:
                        cuenta = accounts_data[0]
                        nuevo_saldo = cuenta.get("balance", float(banco.saldo_actual or 0))
                        
                        banco.saldo_actual = nuevo_saldo
                        db.session.commit()
                        print(f"✅ [WEBHOOK] Saldo actualizado para banco {banco.nombre_banco}: {nuevo_saldo}")
                    else:
                        print(f"⚠️ [WEBHOOK] No se encontraron cuentas para el item_id {item_id}")
                else:
                    print(f"ℹ️ [WEBHOOK] No existe banco registrado con item_id {item_id}")
            else:
                print(f"ℹ️ [WEBHOOK] Evento ignorado o sin item_id: {event}")
        except Exception as e:
            print(f"❌ [WEBHOOK] Error procesando evento en segundo plano: {e}")

@tesoreria_bp.route("/api/webhooks/pluggy", methods=["POST"])
def webhook_pluggy():
    """
    Recibe notificaciones de Pluggy, retorna 200 OK inmediatamente
    y delega el procesamiento a un hilo en background.
    """
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "Payload inválido"}), 400

    print(f"📥 [WEBHOOK RECIBIDO] Event: {data.get('event')}, ItemId: {data.get('itemId')}")

    # Extraer el contexto actual de la aplicación de Flask para pasarlo al hilo
    app_context = current_app._get_current_object().app_context()
    
    # Lanzar el procesamiento en segundo plano
    thread = threading.Thread(target=_process_pluggy_webhook, args=(app_context, data))
    thread.start()

    return jsonify({"status": "received"}), 200
