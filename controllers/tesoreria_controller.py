from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from decorators import login_required, admin_oficina_required
from models import db, Contrato, Cotizacion, Movimientos, Bancos
from werkzeug.utils import secure_filename
from decimal import Decimal
import os
from datetime import datetime
import requests
from requests.auth import HTTPBasicAuth
import uuid
from supabase_client import supabase

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
        banco_id = request.form.get("banco_id")

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
            if not banco_id:
                flash("Debe seleccionar un banco para registrar el anticipo", "danger")
                db.session.rollback()
                return redirect(request.referrer)

            banco = Bancos.query.get(banco_id)
            if not banco:
                flash("El banco seleccionado no existe", "danger")
                db.session.rollback()
                return redirect(request.referrer)

            movimiento_anticipo = Movimientos(
                contrato_id=contrato.id,
                banco_id=banco.id,
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
            
            # Actualizar saldo del banco
            banco.saldo_actual = (banco.saldo_actual or 0) + valor_anticipo

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
            
            # Actualizar Banco
            if movimiento_anticipo.banco:
                if movimiento_anticipo.tipo == 'INGRESO':
                    movimiento_anticipo.banco.saldo_actual = (movimiento_anticipo.banco.saldo_actual or Decimal("0")) + diferencia_anticipo
                elif movimiento_anticipo.tipo == 'EGRESO':
                    movimiento_anticipo.banco.saldo_actual = (movimiento_anticipo.banco.saldo_actual or Decimal("0")) - diferencia_anticipo

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
            "bank": m.banco.nombre_banco if m.banco else 'N/A',
            "banco_id": m.banco_id,
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
            "belvo_link_id": b.belvo_link_id
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
            "belvo_link_id": b.belvo_link_id
        })
    return render_template("bancos.html", bancos_json=bancos_list)

@tesoreria_bp.route("/movimiento/registrar", methods=["POST"])
@admin_oficina_required
def registrar_movimiento():
    # Este endpoint recibe un movimiento general. Puede o no tener contrato
    contrato_id_raw = request.form.get("contrato_id")
    banco_id_raw = request.form.get("banco_id")
    
    try:
        banco = Bancos.query.get_or_404(int(banco_id_raw))
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
            banco_id=banco.id,
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
        
        # Actualizar Saldo Bancario
        if tipo == "INGRESO":
            banco.saldo_actual = (banco.saldo_actual or Decimal("0")) + valor_neto
        elif tipo == "EGRESO":
            banco.saldo_actual = (banco.saldo_actual or Decimal("0")) - valor_neto
            
        db.session.commit()
        flash("Movimiento registrado y saldo actualizado ✅", "success")
        
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
                banco_id=nuevo_banco.id,
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
    
    # Verificamos si el banco tiene un belvo_link_id
    if not banco.belvo_link_id:
        return jsonify({
            "status": "error",
            "code": "MISSING_LINK",
            "message": "Este banco aún no está vinculado con Belvo. Por favor, inicie el proceso de vinculación."
        }), 400

    try:
        # Configuración de credenciales de Belvo
        belvo_secret_id = os.environ.get("BELVO_SECRET_ID")
        belvo_secret_password = os.environ.get("BELVO_SECRET_PASSWORD")
        belvo_env = os.environ.get("BELVO_ENVIRONMENT", "sandbox")
        
        if not belvo_secret_id or not belvo_secret_password:
            raise Exception("Las credenciales de Belvo no están configuradas en el servidor.")
            
        base_url = f"https://{belvo_env}.belvo.com"
        
        auth = HTTPBasicAuth(belvo_secret_id, belvo_secret_password)
        link_id = banco.belvo_link_id

        # 1. Obtener Cuentas (para el saldo actual)
        accounts_url = f"{base_url}/api/accounts/?link={link_id}"
        response_accounts = requests.get(accounts_url, auth=auth)
        
        if response_accounts.status_code in [401, 404]:
            return jsonify({
                "status": "sin_datos",
                "saldo_real": float(banco.saldo_actual or 0),
                "transacciones_bancarias": []
            }), 200
        elif response_accounts.status_code != 200:
            raise Exception(f"Error al obtener cuentas de Belvo: {response_accounts.text}")
            
        accounts_data = response_accounts.json().get("results", [])
        
        if not accounts_data:
            return jsonify({
                "status": "sin_datos",
                "saldo_real": float(banco.saldo_actual or 0),
                "transacciones_bancarias": []
            }), 200
            
        # Tomamos la primera cuenta por defecto
        cuenta_belvo = accounts_data[0]
        saldo_real_banco = cuenta_belvo.get("balance", {}).get("current", float(banco.saldo_actual or 0))

        # Actualizar numero_cuenta si está vacío (creado desde Belvo)
        if not banco.numero_cuenta or banco.numero_cuenta == "":
            numero_belvo = cuenta_belvo.get("number") or cuenta_belvo.get("internal_identification") or ""
            if numero_belvo:
                banco.numero_cuenta = numero_belvo
                db.session.commit()

        # 2. Obtener Transacciones
        # Por defecto, traemos los últimos 30 días
        from datetime import timedelta
        date_from = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d")
        
        transactions_url = f"{base_url}/api/transactions/?link={link_id}&date_from={date_from}"
        response_transactions = requests.get(transactions_url, auth=auth)
        
        if response_transactions.status_code != 200:
            raise Exception(f"Error al obtener transacciones de Belvo: {response_transactions.text}")
            
        transactions_data = response_transactions.json().get("results", [])
        
        transacciones_reales = []
        for tx in transactions_data:
            transacciones_reales.append({
                "id": tx.get("id"),
                "amount": tx.get("amount"),
                "type": tx.get("type"), # 'INFLOW' or 'OUTFLOW'
                "status": tx.get("status"), # 'PROCESSED', 'PENDING'
                "description": tx.get("description", "Sin descripción"),
                "value_date": tx.get("value_date"),
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
        print(f"⚠️ Error en sincronización Belvo: {e}")
        return jsonify({
            "status": "error",
            "message": f"Error al sincronizar con Belvo: {str(e)}"
        }), 500

@tesoreria_bp.route("/api/bancos/<int:id_banco>/vincular", methods=["POST"])
@admin_oficina_required
def vincular_banco_belvo(id_banco):
    banco = Bancos.query.get_or_404(id_banco)
    
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "No se enviaron datos JSON"}), 400
        
    link_id = data.get("link_id")
    institucion = data.get("institution")
    
    if not link_id:
        return jsonify({"status": "error", "message": "El link_id es requerido"}), 400
        
    try:
        banco.belvo_link_id = link_id
        if institucion:
            banco.belvo_institution = institucion
            
        db.session.commit()
        
        return jsonify({
            "status": "success",
            "message": "Banco vinculado correctamente a Belvo",
            "link_id": link_id
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
def vincular_banco_nuevo():
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "No se enviaron datos JSON"}), 400
        
    link_id = data.get("link_id")
    institucion = data.get("institution")
    
    if not link_id or not institucion:
        return jsonify({"status": "error", "message": "El link_id y institution son requeridos"}), 400
        
    try:
        nuevo_banco = Bancos(
            nombre_banco=institucion,
            numero_cuenta="",
            saldo_actual=0,
            color="#00D4AA",
            belvo_link_id=link_id,
            belvo_institution=institucion
        )
        db.session.add(nuevo_banco)
        db.session.commit()
        
        return jsonify({
            "status": "success",
            "message": "Banco vinculado y creado correctamente desde Belvo",
            "banco_id": nuevo_banco.id
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"⚠️ Error al crear banco vía Belvo: {e}")
        return jsonify({
            "status": "error",
            "message": "Error interno al guardar la vinculación"
        }), 500

@tesoreria_bp.route("/api/bancos/<int:id_banco>", methods=["DELETE"])
@admin_oficina_required
def eliminar_banco(id_banco):
    banco = Bancos.query.get_or_404(id_banco)
    
    try:
        # 1. Eliminar link en Belvo si existe
        if banco.belvo_link_id:
            belvo_secret_id = os.environ.get("BELVO_SECRET_ID")
            belvo_secret_password = os.environ.get("BELVO_SECRET_PASSWORD")
            belvo_env = os.environ.get("BELVO_ENVIRONMENT", "sandbox")
            base_url = f"https://{belvo_env}.belvo.com"
            
            import requests
            from requests.auth import HTTPBasicAuth
            
            url = f"{base_url}/api/links/{banco.belvo_link_id}/"
            resp = requests.delete(url, auth=HTTPBasicAuth(belvo_secret_id, belvo_secret_password))
            
            if resp.status_code not in (204, 200, 404):
                print(f"⚠️ Aviso: no se pudo eliminar el link en Belvo: {resp.status_code} - {resp.text}")
        
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

@tesoreria_bp.route("/api/belvo/token", methods=["POST"])
@admin_oficina_required
def obtener_token_belvo():
    try:
        belvo_secret_id = os.environ.get("BELVO_SECRET_ID")
        belvo_secret_password = os.environ.get("BELVO_SECRET_PASSWORD")
        belvo_env = os.environ.get("BELVO_ENVIRONMENT", "sandbox")
        
        if not belvo_secret_id or not belvo_secret_password:
            return jsonify({"status": "error", "message": "Credenciales de Belvo faltantes"}), 500
            
        base_url = f"https://{belvo_env}.belvo.com"
        token_url = f"{base_url}/api/token/"
        
        # Payload requerido por Belvo para generar el token del Widget
        payload = {
            "id": belvo_secret_id,
            "password": belvo_secret_password,
            "scopes": "read_institutions,write_links,read_links"
        }
        
        response = requests.post(token_url, json=payload)
        
        if response.status_code != 200 and response.status_code != 201:
            raise Exception(f"Fallo al obtener token: {response.text}")
            
        data = response.json()
        return jsonify({
            "status": "success",
            "access_token": data.get("access", "")
        }), 200
        
    except Exception as e:
        print(f"⚠️ Error al obtener widget token de Belvo: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
