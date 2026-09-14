import os

def replace_in_file(filepath, replacements):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    for old, new in replacements:
        content = content.replace(old, new)
        
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

replace_in_file('templates/proyectos.html', [
    ('type="number" class="form-control" name="unidades_totales" min="1"', 'type="number" step="any" min="0" class="form-control" name="unidades_totales"'),
    ('type="number" class="form-control ms-3 cantidad-input"', 'type="number" step="any" min="0" class="form-control ms-3 cantidad-input"')
])

replace_in_file('templates/dashboard_trabajador.html', [
    ('type="number" name="unidades_avanzadas" class="form-control" min="1" required', 'type="number" step="any" min="0" name="unidades_avanzadas" class="form-control" placeholder="Ej: 12.5" required'),
    ('type="number" step="0.01"', 'type="number" step="any" min="0"'),
    ('type="number" name="cantidad[]" class="form-control" min="1"', 'type="number" step="any" min="0" name="cantidad[]" class="form-control"')
])

print("Reemplazo exitoso en HTMLs.")
