from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session
from datetime import datetime
import os
import uuid
import re
from werkzeug.utils import secure_filename

from models import db, Clientes, ReporteClientes, Usuarios, Contrato, ContratosClientes, ClienteSubFactura
from supabase_client import supabase
from decorators import login_required, admin_oficina_required

clientes_bp = Blueprint('clientes', __name__, url_prefix='/clientes')

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

def limpiar_porcentaje(val):
    if not val:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    texto_limpio = str(val).replace('%', '').replace(' ', '').replace(',', '.')
    try:
        return float(texto_limpio)
    except ValueError:
        return 0.0

def subir_archivo_supabase(file_obj, carpeta="clientes"):
    """Sube un archivo a Supabase Storage y retorna la URL pública."""
    if not file_obj or file_obj.filename == '':
        return None
        
    if allowed_file(file_obj.filename):
        # 1. Sanitizar el nombre del archivo
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

@clientes_bp.route('/', methods=['GET'])
@login_required
@admin_oficina_required
def index():
    usuario = Usuarios.query.get(session['user_id'])
    
    # 1. Traer todos los contratos de clientes existentes
    contratos_lista = ContratosClientes.query.all()
    
    # 2. Traer todos los reportes (o podemos usar la relación de contratos en la vista)
    reportes_lista = ReporteClientes.query.all()
    
    # También necesitamos los clientes por si el usuario quiere crear un Contrato desde ahí
    clientes_lista = Clientes.query.all()
    
    # 3. Pasarle las listas a la plantilla HTML
    return render_template(
        'clientes.html',
        usuario=usuario,
        contratos=contratos_lista,
        clientes=clientes_lista,
        reportes=reportes_lista,
        frase="El éxito en los negocios requiere entrenamiento y disciplina y mucho trabajo duro."
    )

@clientes_bp.route('/crear_reporte', methods=['POST'])
@login_required
@admin_oficina_required
def crear_reporte():
    try:
        contrato_cliente_id = request.form.get('contrato_cliente_id')
        valor_factura = limpiar_monto(request.form.get('valor_factura'))
        amortizacion = limpiar_monto(request.form.get('amortizacion'))
        porcentaje_rete_garantia = limpiar_porcentaje(request.form.get('porcentaje_rete_garantia'))
        retencion_ley = limpiar_monto(request.form.get('retencion_ley'))
        pago_realizado = limpiar_monto(request.form.get('pago_realizado'))
        fecha_pago_str = request.form.get('fecha_pago')
        fecha_factura_str = request.form.get('fecha_factura')
        
        fecha_pago = datetime.strptime(fecha_pago_str, '%Y-%m-%d').date() if fecha_pago_str else None
        fecha_factura = datetime.strptime(fecha_factura_str, '%Y-%m-%d').date() if fecha_factura_str else None

        # Archivos
        actas_pdf = request.files.get('actas_pdf')
        factura_pdf = request.files.get('factura_pdf')
        comprobante_pago = request.files.get('comprobante_pago')

        print(f"--- DEBUG CREAR REPORTE ---")
        print(f"Archivo acta recibido: {actas_pdf}")
        print(f"Archivo factura recibido: {factura_pdf}")
        print(f"Archivo comprobante recibido: {comprobante_pago}")

        url_actas = subir_archivo_supabase(actas_pdf)
        url_factura = subir_archivo_supabase(factura_pdf)
        url_comprobante = subir_archivo_supabase(comprobante_pago)

        nuevo_reporte = ReporteClientes(
            contrato_cliente_id=contrato_cliente_id,
            actas_pdf_url=url_actas,
            valor_factura=valor_factura,
            amortizacion=amortizacion,
            factura_pdf_url=url_factura,
            porcentaje_rete_garantia=porcentaje_rete_garantia,
            retencion_ley=retencion_ley,
            pago_realizado=pago_realizado,
            fecha_pago=fecha_pago,
            fecha_factura=fecha_factura,
            comprobante_pago_url=url_comprobante
        )

        db.session.add(nuevo_reporte)
        db.session.commit()
        
        flash('Reporte creado exitosamente.', 'success')
    except Exception as e:
        db.session.rollback()
        print(f"Error al crear reporte: {e}")
        flash('Error al crear el reporte. Verifica los datos.', 'danger')

    return redirect(url_for('clientes.index'))

@clientes_bp.route('/editar_reporte/<int:reporte_id>', methods=['POST'])
@login_required
@admin_oficina_required
def editar_reporte(reporte_id):
    try:
        reporte = ReporteClientes.query.get(reporte_id)
        if not reporte:
            flash('Reporte no encontrado.', 'danger')
            return redirect(url_for('clientes.index'))

        reporte.valor_factura = limpiar_monto(request.form.get('valor_factura'))
        reporte.amortizacion = limpiar_monto(request.form.get('amortizacion'))
        reporte.porcentaje_rete_garantia = limpiar_porcentaje(request.form.get('porcentaje_rete_garantia'))
        reporte.retencion_ley = limpiar_monto(request.form.get('retencion_ley'))
        reporte.pago_realizado = limpiar_monto(request.form.get('pago_realizado'))
        
        fecha_pago_str = request.form.get('fecha_pago')
        if fecha_pago_str:
            reporte.fecha_pago = datetime.strptime(fecha_pago_str, '%Y-%m-%d').date()

        fecha_factura_str = request.form.get('fecha_factura')
        if fecha_factura_str:
            reporte.fecha_factura = datetime.strptime(fecha_factura_str, '%Y-%m-%d').date()

        # Archivos (solo se actualizan si se subió uno nuevo)
        nuevo_archivo_acta = request.files.get('actas_pdf')
        print(f"--- DEBUG EDITAR REPORTE ---")
        print(f"Archivo acta recibido: {nuevo_archivo_acta}")
        
        if nuevo_archivo_acta and nuevo_archivo_acta.filename != '':
            url_acta = subir_archivo_supabase(nuevo_archivo_acta)
            if url_acta:
                reporte.actas_pdf_url = url_acta

        nuevo_archivo_factura = request.files.get('factura_pdf')
        if nuevo_archivo_factura and nuevo_archivo_factura.filename != '':
            url_factura = subir_archivo_supabase(nuevo_archivo_factura)
            if url_factura:
                reporte.factura_pdf_url = url_factura

        nuevo_archivo_comprobante = request.files.get('comprobante_pago')
        if nuevo_archivo_comprobante and nuevo_archivo_comprobante.filename != '':
            url_comprobante = subir_archivo_supabase(nuevo_archivo_comprobante)
            if url_comprobante:
                reporte.comprobante_pago_url = url_comprobante

        db.session.commit()
        flash('Reporte actualizado exitosamente.', 'success')
    except Exception as e:
        db.session.rollback()
        print(f"Error al actualizar reporte: {e}")
        flash('Error al actualizar el reporte.', 'danger')

    return redirect(url_for('clientes.index'))

@clientes_bp.route('/reportes/eliminar/<string:id>', methods=['POST', 'DELETE'])
@login_required
@admin_oficina_required
def eliminar_reporte(id):
    try:
        reporte = ReporteClientes.query.get(id)
        if reporte:
            db.session.delete(reporte)
            db.session.commit()
            flash('Factura eliminada exitosamente.', 'success')
        else:
            flash('No se encontró la factura a eliminar.', 'warning')
    except Exception as e:
        db.session.rollback()
        print(f"Error al eliminar factura: {e}")
        flash('Ocurrió un error al intentar eliminar la factura.', 'danger')
        
    return redirect(url_for('clientes.index'))

@clientes_bp.route('/crear', methods=['POST'])
@login_required
@admin_oficina_required
def crear_cliente():
    try:
        nombre_cliente = request.form.get('nombre_cliente')
        nit = request.form.get('nit')
        contacto = request.form.get('contacto')

        if not nombre_cliente:
            flash('El nombre del cliente es obligatorio.', 'warning')
            return redirect(url_for('clientes.index'))

        nuevo_cliente = Clientes(
            nombre_cliente=nombre_cliente,
            nit=nit,
            contacto=contacto
        )

        db.session.add(nuevo_cliente)
        db.session.commit()
        
        flash('Cliente registrado exitosamente.', 'success')
        return redirect(url_for('clientes.index'))
    except Exception as e:
        db.session.rollback()
        print(f"Error al crear cliente: {str(e)}")
        return f"Error interno: {str(e)}", 500

@clientes_bp.route('/crear_contrato_cliente', methods=['POST'])
@login_required
@admin_oficina_required
def crear_contrato_cliente():
    try:
        cliente_id = request.form.get('cliente_id')
        proyecto_nombre = request.form.get('nombre_proyecto')
        valor_total = limpiar_monto(request.form.get('valor_total'))
        porcentaje_retegarantia = limpiar_monto(request.form.get('porcentaje_retegarantia'))
        
        # Archivo PDF del contrato (si lo hay)
        contrato_pdf = request.files.get('contrato_pdf')
        url_contrato = subir_archivo_supabase(contrato_pdf) if contrato_pdf else None
        
        cliente = Clientes.query.get(cliente_id)
        if not cliente:
            flash("Cliente no encontrado", "danger")
            return redirect(url_for('clientes.index'))

        nuevo_contrato_cliente = ContratosClientes(
            cliente_id=cliente.id,
            nombre_proyecto=proyecto_nombre,
            valor_total=valor_total,
            porcentaje_retegarantia=porcentaje_retegarantia,
            archivo_pdf=url_contrato
        )

        db.session.add(nuevo_contrato_cliente)
        db.session.commit()
        flash('Contrato (Proyecto) creado exitosamente.', 'success')
    except Exception as e:
        db.session.rollback()
        print(f"Error al crear contrato cliente: {e}")
        flash(f'Error al crear contrato: {e}', 'danger')

    return redirect(url_for('clientes.index'))

@clientes_bp.route('/editar/<int:cliente_id>', methods=['POST'])
@login_required
@admin_oficina_required
def editar_cliente(cliente_id):
    try:
        cliente = Clientes.query.get(cliente_id)
        if not cliente:
            flash('Cliente no encontrado.', 'danger')
            return redirect(url_for('clientes.index'))

        cliente.nombre_cliente = request.form.get('nombre_cliente')
        cliente.nit = request.form.get('nit')
        cliente.contacto = request.form.get('contacto')

        db.session.commit()
        flash('Cliente actualizado exitosamente.', 'success')
    except Exception as e:
        db.session.rollback()
        print(f"Error al actualizar cliente: {e}")
        flash('Error al actualizar cliente.', 'danger')

    return redirect(url_for('clientes.index'))

@clientes_bp.route('/editar_contrato_cliente/<int:contrato_id>', methods=['POST'])
@login_required
@admin_oficina_required
def editar_contrato_cliente(contrato_id):
    try:
        contrato = ContratosClientes.query.get(contrato_id)
        if not contrato:
            flash("Contrato no encontrado", "danger")
            return redirect(url_for('clientes.index'))

        contrato.nombre_proyecto = request.form.get('nombre_proyecto')
        contrato.valor_total = limpiar_monto(request.form.get('valor_total'))
        contrato.porcentaje_retegarantia = limpiar_monto(request.form.get('porcentaje_retegarantia'))
        
        # Archivo PDF del contrato (si lo hay)
        nuevo_contrato_pdf = request.files.get('contrato_pdf')
        if nuevo_contrato_pdf and nuevo_contrato_pdf.filename != '':
            url_contrato = subir_archivo_supabase(nuevo_contrato_pdf)
            if url_contrato:
                contrato.archivo_pdf = url_contrato

        db.session.commit()
        flash('Contrato actualizado exitosamente.', 'success')
    except Exception as e:
        db.session.rollback()
        print(f"Error al actualizar contrato cliente: {e}")
        flash(f'Error al actualizar contrato: {e}', 'danger')

    return redirect(url_for('clientes.index'))


@clientes_bp.route('/subfactura/crear', methods=['POST'])
@login_required
@admin_oficina_required
def crear_subfactura():
    try:
        factura_id = request.form.get('factura_id')
        factura_padre = ReporteClientes.query.get(factura_id)
        if not factura_padre:
            flash('Factura principal no encontrada.', 'danger')
            return redirect(url_for('clientes.index'))

        numero = request.form.get('numero_subfactura', '')
        fecha_str = request.form.get('fecha_subfactura', '')
        fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date() if fecha_str else None
        concepto = request.form.get('concepto', '')
        valor = limpiar_monto(request.form.get('valor', 0))

        pdf = request.files.get('pdf_subfactura')
        url_pdf = None
        if pdf and pdf.filename:
            url_pdf = subir_archivo_supabase(pdf)

        nueva_sub = ClienteSubFactura(
            factura_id=factura_padre.id,
            numero_subfactura=numero,
            fecha=fecha,
            concepto=concepto,
            valor=valor,
            archivo_pdf_url=url_pdf
        )
        db.session.add(nueva_sub)
        db.session.commit()
        
        # Recalcular valor_factura de la factura padre
        factura_padre.valor_factura = sum(sf.valor for sf in factura_padre.subfacturas)
        db.session.commit()

        flash('Sub-factura registrada correctamente.', 'success')
    except Exception as e:
        db.session.rollback()
        print(f"Error al crear subfactura: {e}")
        flash('Error al crear sub-factura.', 'danger')

    return redirect(url_for('clientes.index'))


@clientes_bp.route('/subfactura/eliminar/<int:id>', methods=['POST'])
@login_required
@admin_oficina_required
def eliminar_subfactura(id):
    try:
        subfactura = ClienteSubFactura.query.get(id)
        if not subfactura:
            flash('Sub-factura no encontrada.', 'danger')
            return redirect(url_for('clientes.index'))

        factura_padre = subfactura.factura_padre
        db.session.delete(subfactura)
        db.session.commit()
        
        # Recalcular valor_factura de la factura padre
        if factura_padre.subfacturas:
            factura_padre.valor_factura = sum(sf.valor for sf in factura_padre.subfacturas)
        else:
            factura_padre.valor_factura = 0.0
        db.session.commit()

        flash('Sub-factura eliminada.', 'success')
    except Exception as e:
        db.session.rollback()
        print(f"Error al eliminar subfactura: {e}")
        flash('Error al eliminar sub-factura.', 'danger')

    return redirect(url_for('clientes.index'))
