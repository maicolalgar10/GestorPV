import re

for tpl in ['templates/historial_pagos_proveedores.html', 'templates/trabajadores/historial_tarjetas.html']:
    with open(tpl, 'r', encoding='utf-8') as f:
        c = f.read()

    # Find the Saldo Inicial input group and insert the textarea right after it
    saldo_match = re.search(r'(<input [^>]*name="saldo_inicial"[^>]*>[\s\S]*?</div>)', c)
    if saldo_match:
        textarea_html = '''
          <div class="mt-3">
            <label class="form-label fw-semibold text-muted small">Comentario / Observaciones (Opcional)</label>
            <textarea name="comentario" id="comentarioPDF" class="form-control" rows="2" placeholder="Ingrese un comentario u observación adicional para el reporte..."></textarea>
          </div>'''
        
        # Ensure we don't insert it twice
        if 'name="comentario"' not in c:
            c = c[:saldo_match.end()] + textarea_html + c[saldo_match.end():]
            
            with open(tpl, 'w', encoding='utf-8') as f:
                f.write(c)
            print(f'Updated {tpl}')
    else:
        print(f'Could not find saldo_inicial in {tpl}')
