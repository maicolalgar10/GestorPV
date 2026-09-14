import io
from fpdf import FPDF
from flask import send_file, Blueprint, render_template, session, redirect, url_for, flash, request
from models import db, Usuarios, Tarjeta, ProgramacionPagoTarjeta
from datetime import datetime
from decorators import login_required, admin_oficina_required

trabajadores_bp = Blueprint("trabajadores", __name__)

@trabajadores_bp.route("/oficina/trabajadores")
@login_required
@admin_oficina_required
def index():
    usuario = Usuarios.query.get(session["user_id"])
    return render_template("trabajadores/index.html", usuario=usuario)

@trabajadores_bp.route("/oficina/trabajadores/nomina")
@login_required
@admin_oficina_required
def nomina():
    usuario = Usuarios.query.get(session["user_id"])
    empleados = Usuarios.query.filter_by(rol="EMPLEADO").all()
    return render_template("trabajadores/nomina.html", usuario=usuario, empleados=empleados)

@trabajadores_bp.route("/oficina/trabajadores/tarjetas")
@login_required
@admin_oficina_required
def tarjetas():
    usuario = Usuarios.query.get(session["user_id"])
    tarjetas_lista = Tarjeta.query.all()
    pagos_programados = ProgramacionPagoTarjeta.query.filter(ProgramacionPagoTarjeta.estado != 'REALIZADO').order_by(ProgramacionPagoTarjeta.fecha_programada.asc()).all()
    historial_pagos = ProgramacionPagoTarjeta.query.filter_by(estado='REALIZADO').order_by(ProgramacionPagoTarjeta.fecha_programada.desc()).all()
    return render_template("trabajadores/tarjetas.html", usuario=usuario, tarjetas=tarjetas_lista, pagos_programados=pagos_programados, historial_pagos=historial_pagos)

@trabajadores_bp.route("/oficina/trabajadores/tarjetas/crear", methods=["POST"])
@login_required
@admin_oficina_required
def crear_tarjeta():
    try:
        nombre = request.form.get("nombre")
        numero = request.form.get("numero")
        
        if nombre and numero:
            nueva_tarjeta = Tarjeta(nombre=nombre, numero=numero)
            db.session.add(nueva_tarjeta)
            db.session.commit()
            flash("Tarjeta creada correctamente", "success")
        else:
            flash("Nombre y número son obligatorios", "warning")
            
    except Exception as e:
        db.session.rollback()
        flash(f"Error al crear la tarjeta: {str(e)}", "danger")
        
    return redirect(url_for("trabajadores.tarjetas"))

@trabajadores_bp.route("/oficina/trabajadores/tarjetas/editar", methods=["POST"])
@login_required
@admin_oficina_required
def editar_tarjeta():
    try:
        id_tarjeta = request.form.get("id_tarjeta")
        nombre = request.form.get("nombre")
        numero = request.form.get("numero")
        
        tarjeta = Tarjeta.query.get_or_404(id_tarjeta)
        
        if nombre and numero:
            tarjeta.nombre = nombre
            tarjeta.numero = numero
            db.session.commit()
            flash("Tarjeta actualizada con éxito", "success")
        else:
            flash("Nombre y número son obligatorios", "warning")
            
    except Exception as e:
        db.session.rollback()
        flash(f"Error al actualizar la tarjeta: {str(e)}", "danger")
        
    return redirect(url_for("trabajadores.tarjetas"))

@trabajadores_bp.route("/oficina/trabajadores/tarjetas/programar-pago", methods=["POST"])
@login_required
@admin_oficina_required
def programar_pago_tarjeta():
    try:
        tarjeta_id = request.form.get("tarjeta_id")
        monto = request.form.get("monto")
        fecha_str = request.form.get("fecha_programada")
        concepto = request.form.get("concepto")
        cuenta_origen = request.form.get("cuenta_origen")
        
        if not (tarjeta_id and monto and fecha_str):
            flash("Todos los campos obligatorios deben ser completados.", "warning")
            return redirect(url_for("trabajadores.tarjetas"))
            
        fecha_prog = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        
        nuevo_pago = ProgramacionPagoTarjeta(
            tarjeta_id=int(tarjeta_id),
            monto=float(monto),
            fecha_programada=fecha_prog,
            concepto=concepto,
            cuenta_origen=cuenta_origen
        )
        
        db.session.add(nuevo_pago)
        db.session.commit()
        flash("Pago programado correctamente", "success")
        
    except Exception as e:
        db.session.rollback()
        flash(f"Error al programar el pago: {str(e)}", "danger")
        
    return redirect(url_for("trabajadores.tarjetas"))

@trabajadores_bp.route("/oficina/trabajadores/tarjetas/eliminar-pago/<int:id>", methods=["POST"])
@login_required
@admin_oficina_required
def eliminar_pago_tarjeta(id):
    try:
        pago = ProgramacionPagoTarjeta.query.get_or_404(id)
        db.session.delete(pago)
        db.session.commit()
        flash("Pago programado eliminado correctamente", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error al eliminar el pago: {str(e)}", "danger")
        
    return redirect(url_for("trabajadores.tarjetas"))

@trabajadores_bp.route("/oficina/trabajadores/tarjetas/marcar-pagado/<int:id>", methods=["POST"])
@login_required
@admin_oficina_required
def marcar_pagado_tarjeta(id):
    try:
        pago = ProgramacionPagoTarjeta.query.get_or_404(id)
        pago.estado = 'REALIZADO'
        db.session.commit()
        flash("Pago marcado como REALIZADO correctamente", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error al marcar el pago: {str(e)}", "danger")
    return redirect(url_for("trabajadores.tarjetas"))

@trabajadores_bp.route("/oficina/trabajadores/tarjetas/exportar-pdf")
@login_required
@admin_oficina_required
def exportar_pdf_tarjetas():
    pagos = ProgramacionPagoTarjeta.query.order_by(ProgramacionPagoTarjeta.fecha_programada.asc()).all()
    
    pdf = FPDF(orientation='L', format="A4")
    pdf.add_page()
    pdf.set_margins(15, 15, 15)
    pdf.set_font("Helvetica", style="B", size=16)
    pdf.cell(0, 10, "REPORTE DE PROGRAMACION DE PAGOS - TARJETAS", align="C")
    pdf.ln(15)
    
    pdf.set_font("Helvetica", style="B", size=10)
    pdf.set_fill_color(220, 220, 220)
    pdf.cell(30, 10, "FECHA", border=1, fill=True, align="C")
    pdf.cell(50, 10, "TARJETA", border=1, fill=True, align="C")
    pdf.cell(35, 10, "MONTO", border=1, fill=True, align="C")
    pdf.cell(50, 10, "CUENTA ORIGEN", border=1, fill=True, align="C")
    pdf.cell(70, 10, "CONCEPTO", border=1, fill=True, align="C")
    pdf.cell(30, 10, "ESTADO", border=1, fill=True, align="C")
    pdf.ln(10)
    
    pdf.set_font("Helvetica", size=9)
    for p in pagos:
        tarjeta_nombre = p.tarjeta.nombre if p.tarjeta and p.tarjeta.nombre else 'Desconocida'
        # Truncar textos largos
        t_n = (tarjeta_nombre[:20] + '..') if len(tarjeta_nombre) > 20 else tarjeta_nombre
        c_o = (p.cuenta_origen[:20] + '..') if p.cuenta_origen and len(p.cuenta_origen) > 20 else str(p.cuenta_origen)
        con = (p.concepto[:35] + '..') if p.concepto and len(p.concepto) > 35 else str(p.concepto)
        
        pdf.cell(30, 8, p.fecha_programada.strftime('%d/%m/%Y'), border=1, align="C")
        pdf.cell(50, 8, t_n, border=1)
        pdf.cell(35, 8, f"$ {p.monto:,.2f}", border=1, align="R")
        pdf.cell(50, 8, c_o, border=1)
        pdf.cell(70, 8, con, border=1)
        pdf.cell(30, 8, str(p.estado), border=1, align="C")
        pdf.ln(8)
        
    pdf.ln(10)
    pdf.set_font("Helvetica", style="I", size=8)
    pdf.cell(0, 5, "Documento generado automaticamente.", align="L")
    
    byte_string = pdf.output()
    return send_file(
        io.BytesIO(byte_string),
        download_name="Reporte_Pagos_Tarjetas.pdf",
        mimetype="application/pdf"
    )
