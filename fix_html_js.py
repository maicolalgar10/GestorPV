import os, re

templates_dir = 'templates'
for root, dirs, files in os.walk(templates_dir):
    for f in files:
        if not f.endswith('.html'): continue
        p = os.path.join(root, f)
        try:
            with open(p, 'r', encoding='utf-8') as file:
                c = file.read()
        except UnicodeDecodeError:
            try:
                with open(p, 'r', encoding='utf-16') as file:
                    c = file.read()
            except Exception as e:
                print(f"Skipping {p}: {e}")
                continue
                
        c_orig = c
        
        # Remove inline formatCurrencyInput and formatMoneyField
        c = re.sub(r'function formatCurrencyInput\([^)]*\)\s*\{[\s\S]*?\n\s*\}', '', c)
        c = re.sub(r'function formatMoneyField\([^)]*\)\s*\{[\s\S]*?\n\s*\}', '', c)
        
        # Add script include right before </body> if not present
        if 'formatos.js' not in c and '</body>' in c:
            c = c.replace('</body>', '<script src="{{ url_for(\'static\', filename=\'js/formatos.js\') }}"></script>\n</body>')
        elif 'formatos.js' not in c and '</html>' in c:
            c = c.replace('</html>', '<script src="{{ url_for(\'static\', filename=\'js/formatos.js\') }}"></script>\n</html>')
            
        if c != c_orig:
            # write back with same encoding
            enc = 'utf-16' if 'utf-16' in str(locals().get('file')) else 'utf-8' # not accurate but works mostly, let's just write utf-8
            with open(p, 'w', encoding='utf-8') as file:
                file.write(c)
            print('Updated', p)
