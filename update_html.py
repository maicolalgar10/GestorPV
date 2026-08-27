import re

with open('templates/contratistas.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add retegarantia to modalCrearFactura
crear_repl = '''                <div class="col-md-3">
                  <label>% Retención</label>
                  <div class="input-group">
                    <input type="text" name="retencion" id="retencion" class="form-control pct-input"
                      value="0" data-raw-value="0" oninput="formatPercentField(this); calcularFactura()">
                    <span class="input-group-text" style="background:#2d2d3f;border-color:#3f3f5c;color:#94a3b8;">%</span>
                  </div>
                </div>
                <div class="col-md-3">
                  <label>% ReteGarantía</label>
                  <div class="input-group">
                    <input type="text" name="retegarantia" id="retegarantia" class="form-control pct-input"
                      value="0" data-raw-value="0" oninput="formatPercentField(this); calcularFactura()">
                    <span class="input-group-text" style="background:#2d2d3f;border-color:#3f3f5c;color:#94a3b8;">%</span>
                  </div>
                </div>'''

content = re.sub(
    r'<div class="col-md-3">\s*<label>% Retención</label>\s*<div class="input-group">\s*<input type="text" name="retencion" id="retencion" class="form-control pct-input"\s*value="0" data-raw-value="0" oninput="formatPercentField\(this\); calcularFactura\(\)">\s*<span class="input-group-text"[^>]*>%</span>\s*</div>\s*</div>',
    crear_repl,
    content,
    count=1
)

# 2. Add retegarantia to modalEditarFactura
editar_repl = '''                <div class="col-md-3">
                  <label>% Retención</label>
                  <div class="input-group">
                    <input type="text" name="retencion" id="edit_retencion" class="form-control pct-input"
                      value="0" data-raw-value="0" oninput="formatPercentField(this); calcularFacturaEdit()">
                    <span class="input-group-text" style="background:#2d2d3f;border-color:#3f3f5c;color:#94a3b8;">%</span>
                  </div>
                </div>
                <div class="col-md-3">
                  <label>% ReteGarantía</label>
                  <div class="input-group">
                    <input type="text" name="retegarantia" id="edit_retegarantia" class="form-control pct-input"
                      value="0" data-raw-value="0" oninput="formatPercentField(this); calcularFacturaEdit()">
                    <span class="input-group-text" style="background:#2d2d3f;border-color:#3f3f5c;color:#94a3b8;">%</span>
                  </div>
                </div>'''

content = re.sub(
    r'<div class="col-md-3">\s*<label>% Retención</label>\s*<div class="input-group">\s*<input type="text" name="retencion" id="edit_retencion" class="form-control pct-input"\s*value="0" data-raw-value="0" oninput="formatPercentField\(this\); calcularFacturaEdit\(\)">\s*<span class="input-group-text"[^>]*>%</span>\s*</div>\s*</div>',
    editar_repl,
    content,
    count=1
)

# 3. Add to calc_box in modalCrearFactura (Total Retegarantía)
calc_crear_repl = '''                <div class="calc-box bg-dark">
                  <div class="calc-label text-warning">Total ReteGarantía</div>
                  <div class="calc-val text-warning" id="calc_retegarantia_factura"> $0 </div>
                </div>
                <div class="calc-box bg-dark">'''

content = re.sub(
    r'<div class="calc-box bg-dark">\s*<div class="calc-label text-warning">Total Retención Ley</div>',
    calc_crear_repl + '\n                  <div class="calc-label text-warning">Total Retención Ley</div>',
    content,
    count=1
)

# 4. Add to calc_box in modalEditarFactura (Total Retegarantía)
calc_editar_repl = '''                <div class="calc-box bg-dark">
                  <div class="calc-label text-warning">Total ReteGarantía</div>
                  <div class="calc-val text-warning" id="calc_retegarantia_factura_edit"> $0 </div>
                </div>
                <div class="calc-box bg-dark">'''

content = re.sub(
    r'<div class="calc-box bg-dark">\s*<div class="calc-label text-warning">Total Retención Ley</div>',
    calc_editar_repl + '\n                  <div class="calc-label text-warning">Total Retención Ley</div>',
    content,
    count=1
)

# 5. JS changes: calcularFactura
js_calc_repl = '''    function calcularFactura() {
      const bruto = parseRawValue('valor_neto');
      const iva_pct = parseRawValue('porcentaje_iva');
      const ret_pct = parseRawValue('retencion');
      const retegarantia_pct = parseRawValue('retegarantia');
      const pago = parseRawValue('valor_cancelado');

      const val_iva = bruto * (iva_pct / 100);
      const val_ret = bruto * (ret_pct / 100);
      const val_retegarantia = bruto * (retegarantia_pct / 100);
      const total = bruto - val_ret;
      const adeudado = total - pago;

      let el_retegarantia = document.getElementById('calc_retegarantia_factura');
      if(el_retegarantia) el_retegarantia.innerText = '$' + new Intl.NumberFormat('es-CO').format(val_retegarantia);
      document.getElementById('calc_retencion_factura').innerText = '$' + new Intl.NumberFormat('es-CO').format(val_ret);
      document.getElementById('calc_total_factura').innerText = '$' + new Intl.NumberFormat('es-CO').format(total);
      document.getElementById('calc_adeudado_factura').innerText = '$' + new Intl.NumberFormat('es-CO').format(adeudado);
    }'''

content = re.sub(
    r'function calcularFactura\(\) \{.*?\n    \}',
    js_calc_repl,
    content,
    flags=re.DOTALL,
    count=1
)

# 6. JS changes: calcularFacturaEdit
js_calce_repl = '''    function calcularFacturaEdit() {
      const bruto = parseRawValue('edit_valor_neto');
      const iva_pct = parseRawValue('edit_porcentaje_iva');
      const ret_pct = parseRawValue('edit_retencion');
      const retegarantia_pct = parseRawValue('edit_retegarantia');
      const pago = parseRawValue('edit_valor_cancelado');

      const val_iva = bruto * (iva_pct / 100);
      const val_ret = bruto * (ret_pct / 100);
      const val_retegarantia = bruto * (retegarantia_pct / 100);
      const total = bruto - val_ret;
      const adeudado = total - pago;

      let el_retegarantia = document.getElementById('calc_retegarantia_factura_edit');
      if(el_retegarantia) el_retegarantia.innerText = '$' + new Intl.NumberFormat('es-CO').format(val_retegarantia);
      document.getElementById('calc_retencion_factura_edit').innerText = '$' + new Intl.NumberFormat('es-CO').format(val_ret);
      document.getElementById('calc_total_factura_edit').innerText = '$' + new Intl.NumberFormat('es-CO').format(total);
      document.getElementById('calc_adeudado_factura_edit').innerText = '$' + new Intl.NumberFormat('es-CO').format(adeudado);
    }'''

content = re.sub(
    r'function calcularFacturaEdit\(\) \{.*?\n    \}',
    js_calce_repl,
    content,
    flags=re.DOTALL,
    count=1
)

# 7. JS changes: prepararModalCrearFactura
js_preparar_repl = '''      document.getElementById('retencion').setAttribute('data-raw-value', '0');
      let rg = document.getElementById('retegarantia');
      if(rg){ rg.setAttribute('data-raw-value', '0'); rg.value='0'; }'''

content = re.sub(
    r"document\.getElementById\('retencion'\)\.setAttribute\('data-raw-value', '0'\);",
    js_preparar_repl,
    content,
    count=1
)

# 8. Update btn in html: onclick="abrirModalEditarFactura(..., '{{ (r.retencion or 0)|int }}', '{{ (r.porcentaje_retegarantia or 0)|int }}', ...)"
# We need to change the arguments for abrirModalEditarFactura to include retegarantia
html_btn_repl = r"onclick=\"abrirModalEditarFactura('\1', '\2', '\3', '\4', '\5', '\6', '{{ (r.porcentaje_retegarantia or 0)|int }}', '\7', '\8', '\9', '\10', '\11')\""
content = re.sub(
    r"onclick=\"abrirModalEditarFactura\('([^']+)',\s*'([^']+)',\s*'([^']+)',\s*'([^']+)',\s*'([^']+)',\s*'([^']+)',\s*'([^']+)',\s*'([^']*)',\s*'([^']*)',\s*'([^']*)',\s*'([^']+)'\)\"",
    html_btn_repl,
    content
)

# 9. Update JS for abrirModalEditarFactura signature
js_abrir_repl = r"function abrirModalEditarFactura(id, nombre, contratoId, valor_neto, iva_pct, ret, retegarantia, pago, f_pago, f_factura, f_venc, plazo) {"
content = re.sub(
    r"function abrirModalEditarFactura\(id, nombre, contratoId, valor_neto, iva_pct, ret, pago, f_pago, f_factura, f_venc, plazo\) \{",
    js_abrir_repl,
    content,
    count=1
)

# 10. Update JS for abrirModalEditarFactura to set retegarantia value
js_abrir_set_repl = '''      let r = document.getElementById('edit_retencion');
      r.setAttribute('data-raw-value', ret);
      r.value = ret;

      let rg = document.getElementById('edit_retegarantia');
      if(rg) {
        rg.setAttribute('data-raw-value', retegarantia);
        rg.value = retegarantia;
      }'''

content = re.sub(
    r"      let r = document\.getElementById\('edit_retencion'\);\s*r\.setAttribute\('data-raw-value', ret\);\s*r\.value = ret;",
    js_abrir_set_repl,
    content,
    count=1
)

with open('templates/contratistas.html', 'w', encoding='utf-8') as f:
    f.write(content)

print('Updated templates/contratistas.html')
