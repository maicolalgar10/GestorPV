import os, re

templates_dir = 'templates'
for root, dirs, files in os.walk(templates_dir):
    for f in files:
        if not f.endswith('.html'): continue
        p = os.path.join(root, f)
        
        with open(p, 'r', encoding='utf-8') as file:
            c = file.read()
            
        c_orig = c
        
        # We find all <input type="number" ...> and check if name or id matches the money keywords,
        # or if it has money classes. If so, we replace type="number" with type="text".
        def replacer(match):
            input_tag = match.group(0)
            keywords = ['monto', 'valor', 'precio', 'costo', 'tarifa', 'saldo', 'currency-input', 'monto-input']
            if any(k in input_tag.lower() for k in keywords):
                return input_tag.replace('type="number"', 'type="text"').replace("type='number'", "type='text'")
            return input_tag
            
        c = re.sub(r'<input\s+[^>]*type=[\'"]number[\'"][^>]*>', replacer, c, flags=re.IGNORECASE)
        
        if c != c_orig:
            with open(p, 'w', encoding='utf-8') as file:
                file.write(c)
            print('Updated input types in', p)
