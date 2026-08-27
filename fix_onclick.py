import re

with open('templates/contratistas.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the onclick for abrirModalEditarFactura
pattern = r'(onclick="abrirModalEditarFactura\([^,]+,\s*[^,]+,\s*[^,]+,\s*[^,]+,\s*[^,]+,\s*[^,]+),\s*([^,]+,\s*[^,]+,\s*[^,]+,\s*[^,]+,\s*[^)]+\)")'

def repl(m):
    return m.group(1) + ", '{{ (r.porcentaje_retegarantia or 0)|int }}', " + m.group(2)

content = re.sub(pattern, repl, content)

with open('templates/contratistas.html', 'w', encoding='utf-8') as f:
    f.write(content)

print('Updated templates/contratistas.html')
