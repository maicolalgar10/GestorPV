import re

html_to_insert = """

<!-- Modal Contratista Sub-facturas -->
<div class="modal fade modal-dark" id="modalContratistaSubFacturas" tabindex="-1">
  <div class="modal-dialog modal-dialog-centered modal-xl">
    <div class="modal-content">
      <div class="modal-header border-bottom-0 pb-0">
        <div>
          <h5 class="modal-title" id="tituloModalSubFacturasContratista"><i class="bi bi-list-ul me-2"></i>Desglose de Sub-facturas</h5>
          <p class="text-muted small mb-0" id="subtituloModalSubFacturasContratista"></p>
        </div>
        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
      </div>
      <div class="modal-body pt-2">
        <!-- Tarjetas de métricas -->
        <div class="row g-3 mb-4">
          <div class="col-md-4">
            <div class="metric-card h-100" style="background:#232338; border:1px solid #3f3f5c; border-radius:12px; padding:15px;">
              <h6 class="text-secondary small fw-semibold mb-1">VALOR ORIGINAL FACTURA (CON IVA)</h6>
              <h3 class="mb-0 text-white fw-bold" id="metric-valor-original-contratista">$0</h3>
            </div>
          </div>
          <div class="col-md-4">
            <div class="metric-card h-100" style="background:#232338; border:1px solid #3f3f5c; border-radius:12px; padding:15px;">
              <h6 class="text-secondary small fw-semibold mb-1">TOTAL SUBFACTURADO (CANCELADO)</h6>
              <h3 class="mb-0 text-success fw-bold" id="metric-total-subfacturado-contratista">$0</h3>
            </div>
          </div>
          <div class="col-md-4">
            <div class="metric-card h-100" style="background:#232338; border:1px solid #3f3f5c; border-radius:12px; padding:15px;">
              <h6 class="text-secondary small fw-semibold mb-1">SALDO RESTANTE (TOTAL ADEUDADO)</h6>
              <h3 class="mb-0 text-warning fw-bold" id="metric-saldo-restante-contratista">$0</h3>
            </div>
          </div>
        </div>

        <div class="row g-4">
          <!-- Columna Izquierda: Lista de Sub-facturas -->
          <div class="col-lg-7">
            <div class="d-flex justify-content-between align-items-center mb-3">
              <h6 class="text-white mb-0">Historial de Sub-facturas</h6>
            </div>
            <div class="table-responsive" style="max-height: 400px; overflow-y: auto;">
              <table class="table table-hover table-dark align-middle">
                <thead>
                  <tr>
                    <th style="background:#232338;">Número</th>
                    <th style="background:#232338;">Fecha</th>
                    <th style="background:#232338;">Concepto</th>
                    <th style="background:#232338;" class="text-end">Valor</th>
                    <th style="background:#232338;" class="text-center">Acciones</th>
                  </tr>
                </thead>
                <tbody id="tablaContratistaSubFacturasBody">
                  <!-- JS llena esta tabla -->
                </tbody>
              </table>
            </div>
          </div>
          
          <!-- Columna Derecha: Formulario Nueva Sub-factura -->
          <div class="col-lg-5">
            <div class="p-3" style="background:#1d1d2b; border:1px solid #3f3f5c; border-radius:12px;">
              <h6 class="text-white mb-3 border-bottom border-secondary pb-2">Registrar Nueva Sub-factura / Pago</h6>
              <form method="POST" action="{{ url_for('contratistas.crear_contratista_subfactura') }}" enctype="multipart/form-data" onsubmit="limpiarMontoSubFacturaContratista(event)">
                <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
                <input type="hidden" name="factura_padre_id" id="hidden_factura_id_sub_contratista">
                
                <div class="mb-3">
                  <label class="form-label text-secondary small">Número de Sub-factura / Soporte</label>
                  <input type="text" class="form-control" name="numero_subfactura" placeholder="Ej: 001-A">
                </div>
                
                <div class="row g-2 mb-3">
                  <div class="col-6">
                    <label class="form-label text-secondary small">Fecha</label>
                    <input type="date" class="form-control" name="fecha_subfactura" required>
                  </div>
                  <div class="col-6">
                    <label class="form-label text-secondary small">Valor ($) *</label>
                    <input type="text" class="form-control" name="valor" id="inputValorSubFacturaContratista" placeholder="$ 0" required oninput="formatCurrencyInput(this)">
                  </div>
                </div>
                
                <div class="mb-3">
                  <label class="form-label text-secondary small">Concepto</label>
                  <input type="text" class="form-control" name="concepto" placeholder="Descripción breve...">
                </div>
                
                <div class="mb-4">
                  <label class="form-label text-secondary small">Archivo (PDF o Imagen, Opcional)</label>
                  <input type="file" class="form-control" name="pdf_subfactura" accept=".pdf, .png, .jpg, .jpeg, .webp, application/pdf, image/*">
                </div>
                
                <button type="submit" class="btn btn-primary w-100 fw-bold"><i class="bi bi-plus-circle me-2"></i>Registrar Sub-factura</button>
              </form>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>

"""

js_to_insert = """
function limpiarMontoSubFacturaContratista(event) {
  let inputVal = document.getElementById('inputValorSubFacturaContratista');
  if (inputVal && inputVal.value) {
    inputVal.value = inputVal.value.replace(/\D/g, '');
  }
}

function abrirModalContratistaSubFacturas(facturaId, nombreContratista, valorNeto, valorCancelado, totalAdeudado, subfacturas) {
  document.getElementById('hidden_factura_id_sub_contratista').value = facturaId;
  document.getElementById('tituloModalSubFacturasContratista').innerHTML = `<i class="bi bi-list-ul me-2"></i>Sub-facturas de: ${nombreContratista}`;
  document.getElementById('subtituloModalSubFacturasContratista').innerText = `ID Factura Principal: #${facturaId}`;

  let baseOriginal = totalAdeudado + valorCancelado;

  document.getElementById('metric-valor-original-contratista').innerText = '$' + new Intl.NumberFormat('es-CO').format(baseOriginal);
  document.getElementById('metric-total-subfacturado-contratista').innerText = '$' + new Intl.NumberFormat('es-CO').format(valorCancelado);
  document.getElementById('metric-saldo-restante-contratista').innerText = '$' + new Intl.NumberFormat('es-CO').format(totalAdeudado);

  const tbody = document.getElementById('tablaContratistaSubFacturasBody');
  tbody.innerHTML = '';

  if (subfacturas.length === 0) {
    tbody.innerHTML = `<tr><td colspan="5" class="text-center text-muted py-4">No hay sub-facturas registradas</td></tr>`;
  } else {
    subfacturas.forEach(sf => {
      let tr = document.createElement('tr');
      
      let pdfBtn = sf.pdf_url ? `<a href="${sf.pdf_url}" target="_blank" class="btn btn-sm btn-outline-info rounded-pill px-2 me-1" title="Ver PDF"><i class="bi bi-file-earmark-pdf"></i></a>` : '';
      let delBtn = `
        <form method="POST" action="/contratistas/subfactura/eliminar/${sf.id}" class="d-inline" onsubmit="return confirm('¿Eliminar esta sub-factura?');">
          <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
          <button class="btn btn-sm btn-outline-danger rounded-pill px-2" title="Eliminar"><i class="bi bi-trash"></i></button>
        </form>
      `;

      tr.innerHTML = `
        <td class="fw-semibold text-white">${sf.numero}</td>
        <td class="small text-white">${sf.fecha}</td>
        <td class="small text-white">${sf.concepto}</td>
        <td class="text-end fw-semibold text-success">$${new Intl.NumberFormat('es-CO').format(sf.valor)}</td>
        <td class="text-center">${pdfBtn}${delBtn}</td>
      `;
      tbody.appendChild(tr);
    });
  }

  document.getElementById('inputValorSubFacturaContratista').value = '';
  new bootstrap.Modal(document.getElementById('modalContratistaSubFacturas')).show();
}
"""

def append_to_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Insert HTML before </body> or <script src
    if '<script src=' in content:
        content = content.replace('<script src=', html_to_insert + '\n<script src=', 1)
    else:
        content = content.replace('</body>', html_to_insert + '\n</body>')

    # Insert JS right before </script>\n</body>
    content = content.replace('</script>\n</body>', js_to_insert + '\n</script>\n</body>')
    # Or in the case of contratistas.html which might have </script>\n</html> or something similar
    if js_to_insert not in content:
        content = content.replace('</script>\n</body>', js_to_insert + '\n</script>\n</body>')

    # Wait, some files might not have </script>\n</body> exactly.
    # We can just append JS to the end of the last <script> block.
    # Let's find the last </script> tag.
    if js_to_insert not in content:
        last_script_end = content.rfind('</script>')
        if last_script_end != -1:
            content = content[:last_script_end] + js_to_insert + '\n</script>' + content[last_script_end + 9:]

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

append_to_file('templates/contratistas.html')
append_to_file('templates/facturas_contratista.html')

print("Exito")
