import os, re
d = 'controllers'
for f in os.listdir(d):
    if not f.endswith('_controller.py'): continue
    p = os.path.join(d, f)
    with open(p, 'r', encoding='utf-8') as file:
        c = file.read()
    
    c_orig = c
    if 'from helpers import clean_amount' not in c:
        c = re.sub(r'^(import|from)', r'from helpers import clean_amount\n\1', c, count=1, flags=re.MULTILINE)
    
    # Replace direct float/Decimal calls on specific fields
    c = re.sub(r'(?:Decimal|float)\(\s*(request\.form\.get\([\'\"](?:monto|valor|valor_total|valor_neto|valor_cancelado)[\'\"](?:,\s*[^)]+)?\))\s*\)', r'clean_amount(\1)', c)
    
    # Replace assignment without cast
    c = re.sub(r'=\s*request\.form\.get\([\'\"](monto|valor|valor_total|valor_neto|valor_cancelado)[\'\"](?:,\s*[\'\"]0[\'\"])?\)', r'= clean_amount(request.form.get("\1"))', c)
    
    # Update limpiar_monto if it exists
    c = re.sub(r'def limpiar_monto\(.*?\):[\s\S]*?(?=\n\S)', 'def limpiar_monto(val):\n    return clean_amount(val)', c)

    # Update parse_float_safe if it exists
    c = re.sub(r'([ \t]*)def parse_float_safe\(val(?:ue)?(?:,\s*default=0\.0)?\):[\s\S]*?(?=\n\1\S)', r'\1def parse_float_safe(val, default=0.0):\n\1    return clean_amount(val)', c)
    
    if c != c_orig:
        with open(p, 'w', encoding='utf-8') as file:
            file.write(c)
        print('Updated', f)
