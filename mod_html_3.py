import os

# 1. Actualizar tarjetas.html
tarjetas_path = 'templates/trabajadores/tarjetas.html'
with open(tarjetas_path, 'r', encoding='utf-8') as f:
    content_t = f.read()

# El link original que inyecté en el paso anterior era url_for('trabajadores.exportar_pdf_tarjetas')
# Y ya tenía el onclick="event.stopPropagation();"
old_t_link = "href=\"{{ url_for('trabajadores.exportar_pdf_tarjetas') }}\""
new_t_link = "href=\"{{ url_for('dashboard.exportar_pdf_pagos_consolidados') }}\""
if old_t_link in content_t:
    content_t = content_t.replace(old_t_link, new_t_link)

with open(tarjetas_path, 'w', encoding='utf-8') as f:
    f.write(content_t)


# 2. Actualizar proveedores.html
prov_path = 'templates/proveedores.html'
with open(prov_path, 'r', encoding='utf-8') as f:
    content_p = f.read()

old_p_link = "href=\"{{ url_for('proveedores.generar_pdf_programacion') }}\" class=\"btn btn-sm btn-danger\" target=\"_blank\" title=\"Exportar PDF\""
new_p_link = "href=\"{{ url_for('dashboard.exportar_pdf_pagos_consolidados') }}\" class=\"btn btn-sm btn-danger\" target=\"_blank\" title=\"Exportar PDF\" onclick=\"event.stopPropagation();\""

if old_p_link in content_p:
    content_p = content_p.replace(old_p_link, new_p_link)
    
with open(prov_path, 'w', encoding='utf-8') as f:
    f.write(content_p)

print('Plantillas actualizadas.')
