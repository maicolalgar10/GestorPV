import os, re
for f in ['templates/trabajadores/historial_tarjetas.html', 'templates/trabajadores/tarjetas.html']:
    with open(f, 'r', encoding='utf-8') as file:
        c = file.read()
    c = re.sub(r'\$\s*\{\{\s*[\"\']%\.2f[\"\']\|format\(([^)]+)\)\s*\}\}', r'{{ \1|formato_miles }}', c)
    with open(f, 'w', encoding='utf-8') as file:
        file.write(c)
    print('Updated', f)
