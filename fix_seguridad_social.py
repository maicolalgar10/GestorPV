import os, re

p = 'templates/seguridad_social.html'
with open(p, 'r', encoding='utf-8') as f:
    c = f.read()

# 1. Replace the edit button
old_button = r'''<button type="button" class="btn btn-sm btn-outline-warning rounded-pill" title="Editar"[^>]*onclick="abrirModalEditar[^>]*>[\s\S]*?</button>'''
new_button = '''<button type="button" class="btn btn-sm btn-outline-warning rounded-pill" title="Editar" data-bs-toggle="modal" data-bs-target="#modalEditarPlanilla{{ p.id }}">
                  <i class="bi bi-pencil"></i>
                </button>'''
c = re.sub(old_button, new_button, c)

# 2. Add the Edit Modal immediately before </tr> (end of the for p in planillas loop)
edit_modal = '''
<!-- Modal Editar Planilla -->
<div class="modal fade" id="modalEditarPlanilla{{ p.id }}" tabindex="-1" style="text-align: left;">
  <div class="modal-dialog modal-dialog-centered modal-lg">
    <div class="modal-content border-0 shadow-lg" style="border-radius: 20px;">
      <form method="POST" action="{{ url_for('seguridad_social.editar_planilla', id=p.id) }}" enctype="multipart/form-data">
        <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
        <div class="modal-header border-0 bg-warning text-dark" style="border-radius: 20px 20px 0 0;">
          <h5 class="modal-title fw-bold"><i class="bi bi-pencil-square"></i> Editar Planilla de Seguridad Social</h5>
          <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body p-4 bg-light text-start">
          <div class="row g-3">
            <div class="col-md-6">
              <label class="form-label fw-semibold">Concepto / Descripción</label>
              <input type="text" name="concepto" class="form-control" value="{{ p.concepto }}" required>
            </div>
            <div class="col-md-6">
              <label class="form-label fw-semibold">Entidad / Tipo de Planilla</label>
              <select name="tipo_planilla_id" class="form-select" required>
                <option value="" disabled>Seleccione...</option>
                {% for entidad in entidades %}
                <option value="{{ entidad.id }}" {% if p.tipo_planilla_id == entidad.id %}selected{% endif %}>{{ entidad.nombre }}</option>
                {% endfor %}
              </select>
            </div>
            <div class="col-md-6">
              <label class="form-label fw-semibold">Valor</label>
              <div class="input-group">
                <span class="input-group-text">$</span>
                <input type="text" name="valor" class="form-control monto-input" value="{{ p.valor|formato_miles|replace('$ ', '') }}" required>
              </div>
            </div>
            <div class="col-md-6">
              <label class="form-label fw-semibold">Estado de Pago (Opcional)</label>
              <input type="text" name="estado_pago" class="form-control" value="{{ p.estado_pago }}">
            </div>
            <div class="col-md-6">
              <label class="form-label fw-semibold">Fecha de Vencimiento</label>
              <input type="date" name="fecha_vencimiento" class="form-control" value="{{ p.fecha_vencimiento.strftime('%Y-%m-%d') if p.fecha_vencimiento else '' }}">
            </div>
            <div class="col-md-6">
              <label class="form-label fw-semibold">Fecha de Pago (Opcional)</label>
              <input type="date" name="fecha_pago" class="form-control" value="{{ p.fecha_pago.strftime('%Y-%m-%d') if p.fecha_pago else '' }}">
            </div>
            <div class="col-md-6 mt-3">
              <label class="form-label fw-semibold">Soporte Declaración/Planilla (Opcional)</label>
              {% if p.soporte_declaracion_url %}
              <div class="mb-2"><a href="{{ p.soporte_declaracion_url }}" target="_blank">Ver actual</a></div>
              <div class="form-check mb-2">
                <input class="form-check-input" type="checkbox" name="eliminar_soporte_declaracion" value="true" id="eliminar_dec_{{ p.id }}">
                <label class="form-check-label text-danger" for="eliminar_dec_{{ p.id }}">Eliminar soporte actual</label>
              </div>
              {% endif %}
              <input type="file" name="soporte_declaracion" class="form-control" accept=".pdf,.png,.jpg,.jpeg,.webp">
            </div>
            <div class="col-md-6 mt-3">
              <label class="form-label fw-semibold">Soporte de Pago (Opcional)</label>
              {% if p.soporte_pago_url %}
              <div class="mb-2"><a href="{{ p.soporte_pago_url }}" target="_blank">Ver actual</a></div>
              <div class="form-check mb-2">
                <input class="form-check-input" type="checkbox" name="eliminar_soporte_pago" value="true" id="eliminar_pago_{{ p.id }}">
                <label class="form-check-label text-danger" for="eliminar_pago_{{ p.id }}">Eliminar soporte actual</label>
              </div>
              {% endif %}
              <input type="file" name="soporte_pago" class="form-control" accept=".pdf,.png,.jpg,.jpeg,.webp">
            </div>
          </div>
        </div>
        <div class="modal-footer border-0">
          <button type="button" class="btn btn-secondary rounded-pill" data-bs-dismiss="modal">Cancelar</button>
          <button type="submit" class="btn btn-warning rounded-pill fw-bold text-dark"><i class="bi bi-save"></i> Guardar Cambios</button>
        </div>
      </form>
    </div>
  </div>
</div>
              </td>
            </tr>'''

c = re.sub(r'              </td>\s*</tr>', edit_modal, c, count=1) # only replace the first occurrence in the loop

# 3. Fix standard formatting for view
c = c.replace('${{ "{:,.2f}".format(p.valor) }}', '{{ p.valor|formato_miles }}')
c = c.replace('${{ "{:,.2f}".format(total_valor|default(0)) }}', '{{ total_valor|default(0)|formato_miles }}')

# Write back
with open(p, 'w', encoding='utf-8') as f:
    f.write(c)

print('Updated', p)
