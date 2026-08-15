with open('controllers/contratistas_controller.py', 'a', encoding='utf-8') as f:
    f.write('''

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
''')
