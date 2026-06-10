import re
import os

templates_dir = r'c:\Users\maico\OneDrive - Universidad Santo Tomás\Escritorio\PruebasCorseing\UltimaActualizacionGomezGordito2.0\templates'
modificados = []

for root, dirs, files in os.walk(templates_dir):
    for file in files:
        if file.endswith('.html'):
            path = os.path.join(root, file)
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()

            parts = re.split(r'(<form\b[^>]*>)', content, flags=re.IGNORECASE)
            
            new_content = parts[0]
            modified = False
            for i in range(1, len(parts), 2):
                form_tag = parts[i]
                form_body = parts[i+1] if i+1 < len(parts) else ''
                
                if re.search(r'method=[\"\']POST[\"\']', form_tag, re.IGNORECASE):
                    form_content = form_body.split('</form>')[0] if '</form>' in form_body else form_body
                    if 'csrf_token' not in form_content:
                        form_tag = form_tag + '\n    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">'
                        modified = True
                
                new_content += form_tag + form_body
                
            if modified:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                modificados.append(file)

print('Archivos modificados:')
for m in modificados:
    print('- ' + m)
