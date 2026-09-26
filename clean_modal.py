import os, re

p = 'templates/seguridad_social.html'
with open(p, 'r', encoding='utf-8') as f:
    c = f.read()

# Remove the old global modalEditarPlanilla
old_global_modal = r'<!-- Modal Editar Planilla -->\s*<div class="modal fade" id="modalEditarPlanilla" tabindex="-1">[\s\S]*?</form>\s*</div>\s*</div>\s*</div>'
c = re.sub(old_global_modal, '', c)

# Remove the JS function abrirModalEditar
js_func = r'function abrirModalEditar\([^)]*\)\s*\{[\s\S]*?modal\.show\(\);\s*\}'
c = re.sub(js_func, '', c)

with open(p, 'w', encoding='utf-8') as f:
    f.write(c)

print('Cleaned up old modal and JS')
