import re

p = 'templates/seguridad_social.html'
with open(p, 'r', encoding='utf-8') as f:
    c = f.read()

# Replace inputs in Create modal
old_inputs = r'<input type="hidden" name="valor" id="valor_hidden" required>\s*<input type="text" id="valor_visual" class="form-control" required oninput="formatearMoneda\(this, \'valor_hidden\'\)">'
new_input = r'<input type="text" name="valor" class="form-control monto-input" required>'
c = re.sub(old_inputs, new_input, c)

# Remove the formatearMoneda function completely
js_func = r'function formatearMoneda[^}]+\}[^}]+\}'
c = re.sub(js_func, '', c)

with open(p, 'w', encoding='utf-8') as f:
    f.write(c)

print('Updated seguridad_social.html')
