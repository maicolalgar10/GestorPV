from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session
from datetime import datetime
import os
import uuid

from models import db, Clientes, ReporteClientes, Usuarios
from supabase_client import supabase

clientes_bp = Blueprint('clientes', __name__, url_prefix='/clientes')

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'pdf', 'png', 'jpg', 'jpeg', 'webp'}

def subir_archivo_supabase(file_obj, carpeta="clientes"):
    """Sube un archivo a Supabase Storage y retorna la URL pública."""
    if not file_obj or file_obj.filename == '':
        return None
        
    if allowed_file(file_obj.filename):
        ext = file_obj.filename.rsplit('.', 1)[1].lower()
        filename = f"{uuid.uuid4().hex}_{file_obj.filename}"
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
            print(f"Error al subir archivo a Supabase: {e}")
            return None
    return None

@clientes_bp.route('/', methods=['GET'])
def index():
    if 'user_id' not in session:
        return redirect(url_for('usuarios.login'))
        
    usuario = Usuarios.query.get(session['user_id'])
    
    # Obtener clientes y sus reportes ordenados
    clientes_lista = Clientes.query.order_by(Clientes.nombre_cliente).all()
    reportes_lista = ReporteClientes.query.order_by(ReporteClientes.created_at.desc()).all()
    
    return render_template(
        'clientes.html',
        usuario=usuario,
        clientes=clientes_lista,
        reportes=reportes_lista,
        frase="El éxito en los negocios requiere entrenamiento y disciplina y mucho trabajo duro."
    )

@clientes_bp.route('/crear_reporte', methods=['POST'])
def crear_reporte():
    if 'user_id' not in session:
        return redirect(url_for('usuarios.login'))

    try:
        cliente_id = request.form.get('cliente_id')
        valor_contrato = float(request.form.get('valor_contrato', 0))
        valor_factura = float(request.form.get('valor_factura', 0))
        porcentaje_rete_garantia = float(request.form.get('porcentaje_rete_garantia', 0))
        retencion_ley = float(request.form.get('retencion_ley', 0))
        pago_realizado = float(request.form.get('pago_realizado', 0))
        fecha_pago_str = request.form.get('fecha_pago')
        
        fecha_pago = datetime.strptime(fecha_pago_str, '%Y-%m-%d').date() if fecha_pago_str else None

        # Archivos
        contrato_pdf = request.files.get('contrato_pdf')
        actas_pdf = request.files.get('actas_pdf')
        factura_pdf = request.files.get('factura_pdf')
        comprobante_pago = request.files.get('comprobante_pago')

        url_contrato = subir_archivo_supabase(contrato_pdf)
        url_actas = subir_archivo_supabase(actas_pdf)
        url_factura = subir_archivo_supabase(factura_pdf)
        url_comprobante = subir_archivo_supabase(comprobante_pago)

        nuevo_reporte = ReporteClientes(
            cliente_id=cliente_id,
            valor_contrato=valor_contrato,
            contrato_pdf_url=url_contrato,
            actas_pdf_url=url_actas,
            valor_factura=valor_factura,
            factura_pdf_url=url_factura,
            porcentaje_rete_garantia=porcentaje_rete_garantia,
            retencion_ley=retencion_ley,
            pago_realizado=pago_realizado,
            fecha_pago=fecha_pago,
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

@clientes_bp.route('/crear', methods=['POST'])
def crear_cliente():
    if 'user_id' not in session:
        return redirect(url_for('usuarios.login'))

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
