import re

with open('templates/trabajadores/tarjetas.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Añadir botones en el card-header de pagos programados
old_header = '''        <div>
          <button class="btn btn-sm btn-outline-primary rounded-circle"><i class="bi bi-chevron-down"></i></button>
        </div>'''
new_header = '''        <div>
          <button type="button" class="btn btn-sm btn-outline-secondary me-2" data-bs-toggle="modal" data-bs-target="#modalHistorialPagosTarjetas" onclick="event.stopPropagation();">
            <i class="bi bi-clock-history"></i> Historial de Pagos
          </button>
          <a href="{{ url_for('trabajadores.exportar_pdf_tarjetas') }}" class="btn btn-sm btn-outline-danger me-2" target="_blank" onclick="event.stopPropagation();">
            <i class="bi bi-file-earmark-pdf"></i> Exportar PDF
          </a>
          <button class="btn btn-sm btn-outline-primary rounded-circle"><i class="bi bi-chevron-down"></i></button>
        </div>'''
content = content.replace(old_header, new_header)

# 2. Modificar la columna de acciones de la tabla de Próximos Pagos
old_actions = '''                  <td class="text-end">
                    <form action="{{ url_for('trabajadores.eliminar_pago_tarjeta', id=pago.id) }}" method="POST" class="d-inline" onsubmit="return confirm('¿Estás seguro de eliminar este pago programado?');">
                      <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
                      <button type="submit" class="btn btn-sm btn-outline-danger rounded-circle" title="Eliminar Pago">
                        <i class="bi bi-trash"></i>
                      </button>
                    </form>
                  </td>'''
new_actions = '''                  <td class="text-end">
                    <form action="{{ url_for('trabajadores.marcar_pagado_tarjeta', id=pago.id) }}" method="POST" class="d-inline">
                      <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
                      <button type="submit" class="btn btn-sm btn-success rounded-circle me-1" title="Marcar como Pagado">
                        <i class="bi bi-check-lg"></i>
                      </button>
                    </form>
                    <form action="{{ url_for('trabajadores.eliminar_pago_tarjeta', id=pago.id) }}" method="POST" class="d-inline" onsubmit="return confirm('¿Estás seguro de eliminar este pago programado?');">
                      <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
                      <button type="submit" class="btn btn-sm btn-outline-danger rounded-circle" title="Eliminar Pago">
                        <i class="bi bi-trash"></i>
                      </button>
                    </form>
                  </td>'''
content = content.replace(old_actions, new_actions)

# 3. Agregar el Modal de Historial
modal_historial = '''
  <!-- Modal Historial de Pagos Tarjetas -->
  <div class="modal fade" id="modalHistorialPagosTarjetas" tabindex="-1" aria-labelledby="modalHistorialPagosTarjetasLabel" aria-hidden="true">
    <div class="modal-dialog modal-xl modal-dialog-centered modal-dialog-scrollable">
      <div class="modal-content" style="border-radius: 16px;">
        <div class="modal-header border-0 pb-0">
          <h5 class="modal-title fw-bold" id="modalHistorialPagosTarjetasLabel">
            <i class="bi bi-clock-history text-secondary"></i> Historial de Pagos Realizados
          </h5>
          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Cerrar"></button>
        </div>
        <div class="modal-body pt-3">
          <div class="table-responsive">
            <table class="table table-hover table-custom mb-0">
              <thead class="table-light">
                <tr>
                  <th>FECHA PROGRAMADA</th>
                  <th>TARJETA</th>
                  <th>MONTO PAGADO</th>
                  <th>CUENTA ORIGEN</th>
                  <th>OBSERVACIÓN / CONCEPTO</th>
                  <th>ESTADO</th>
                </tr>
              </thead>
              <tbody>
                {% for pago in historial_pagos %}
                <tr>
                  <td class="fw-semibold text-muted">{{ pago.fecha_programada.strftime('%d/%m/%Y') }}</td>
                  <td>
                    <div class="d-flex align-items-center gap-2">
                      <i class="bi bi-person-vcard text-secondary"></i>
                      <span>{{ pago.tarjeta.nombre }}</span>
                    </div>
                  </td>
                  <td class="fw-bold text-success">$ {{ "%.2f"|format(pago.monto) }}</td>
                  <td>{{ pago.cuenta_origen if pago.cuenta_origen else '<span class="text-muted fst-italic">No definida</span>'|safe }}</td>
                  <td class="text-muted small">{{ pago.concepto if pago.concepto else '-' }}</td>
                  <td>
                    <span class="badge bg-success rounded-pill px-3 py-2"><i class="bi bi-check-circle me-1"></i> Realizado</span>
                  </td>
                </tr>
                {% else %}
                <tr>
                  <td colspan="6" class="text-center py-4 text-muted">
                    <i class="bi bi-inbox fs-4 d-block mb-2 text-secondary"></i>
                    No hay pagos registrados en el historial.
                  </td>
                </tr>
                {% endfor %}
              </tbody>
            </table>
          </div>
        </div>
        <div class="modal-footer border-0 pt-0">
          <button type="button" class="btn btn-secondary" data-bs-dismiss="modal" style="border-radius: 8px;">Cerrar</button>
        </div>
      </div>
    </div>
  </div>
'''

if 'modalHistorialPagosTarjetas' not in content:
    content = content.replace('<!-- Modal Programar Pago -->', modal_historial + '\n  <!-- Modal Programar Pago -->')

with open('templates/trabajadores/tarjetas.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('tarjetas.html actualizado correctamente.')
