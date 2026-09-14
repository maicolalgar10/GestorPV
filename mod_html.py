with open('templates/trabajadores/tarjetas.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Botones
old_buttons = '''<td class="text-end">
                  <button class="btn btn-sm btn-outline-teal text-teal border" style="border-color: #0f766e; color: #0f766e;" title="Imprimir" disabled>
                    <i class="bi bi-printer"></i>
                  </button>
                </td>'''
new_buttons = '''<td class="text-end">
                  <button class="btn btn-sm btn-outline-teal text-teal border mb-1" style="border-color: #0f766e; color: #0f766e;" title="Imprimir" disabled>
                    <i class="bi bi-printer"></i>
                  </button>
                  <button class="btn btn-sm btn-warning mb-1" title="Programar Pago" onclick="abrirModalProgramarPago({{ t.id_tarjeta }}, '{{ t.nombre }}')">
                    <i class="bi bi-calendar-event"></i> Programar Pago
                  </button>
                </td>'''
content = content.replace(old_buttons, new_buttons)

# Modal Programar Pago
modal_code = '''
  <!-- Modal Programar Pago -->
  <div class="modal fade" id="modalProgramarPago" tabindex="-1" aria-labelledby="modalProgramarPagoLabel" aria-hidden="true">
    <div class="modal-dialog modal-dialog-centered">
      <div class="modal-content" style="border-radius: 16px;">
        <div class="modal-header border-0 pb-0">
          <h5 class="modal-title fw-bold" id="modalProgramarPagoLabel"><i class="bi bi-calendar-event text-warning"></i> Programar Pago para <span id="nombreTarjetaPago"></span></h5>
          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Cerrar"></button>
        </div>
        <form action="{{ url_for('trabajadores.programar_pago_tarjeta') }}" method="POST">
          <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
          <input type="hidden" name="tarjeta_id" id="inputTarjetaIdPago">
          <div class="modal-body pt-3">
            <div class="mb-3">
              <label class="form-label fw-semibold text-secondary small">Monto</label>
              <input type="number" step="any" name="monto" class="form-control" placeholder="Ej: 150000" required>
            </div>
            <div class="mb-3">
              <label class="form-label fw-semibold text-secondary small">Fecha Programada</label>
              <input type="date" name="fecha_programada" class="form-control" required>
            </div>
            <div class="mb-3">
              <label class="form-label fw-semibold text-secondary small">Concepto</label>
              <input type="text" name="concepto" class="form-control" placeholder="Ej: Pago quincena">
            </div>
            <div class="mb-3">
              <label class="form-label fw-semibold text-secondary small">Cuenta de Origen</label>
              <input type="text" name="cuenta_origen" class="form-control" placeholder="Escribe la cuenta de origen...">
            </div>
          </div>
          <div class="modal-footer border-0 pt-0">
            <button type="button" class="btn btn-light" data-bs-dismiss="modal" style="border-radius: 8px;">Cancelar</button>
            <button type="submit" class="btn btn-warning text-dark fw-bold" style="border-radius: 8px;">Programar</button>
          </div>
        </form>
      </div>
    </div>
  </div>
'''
if 'id="modalProgramarPago"' not in content:
    content = content.replace('<!-- Modal Nueva Tarjeta -->', modal_code + '\n  <!-- Modal Nueva Tarjeta -->')

# JS Function
js_code = '''
    function abrirModalProgramarPago(id, nombre) {
      document.getElementById("inputTarjetaIdPago").value = id;
      document.getElementById("nombreTarjetaPago").innerText = nombre;
      var myModal = new bootstrap.Modal(document.getElementById('modalProgramarPago'));
      myModal.show();
    }
'''
if 'abrirModalProgramarPago' not in content:
    content = content.replace('function filtrarTabla() {', js_code + '\n    function filtrarTabla() {')

with open('templates/trabajadores/tarjetas.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('tarjetas.html actualizado')
