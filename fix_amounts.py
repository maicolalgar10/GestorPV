import os
import re

controllers_dir = 'controllers'
for file in os.listdir(controllers_dir):
    if not file.endswith('_controller.py'): continue
    path = os.path.join(controllers_dir, file)
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Import clean_amount
    if 'from helpers import clean_amount' not in content:
        # Find the first import and add it before
        content = re.sub(r'^(import|from)', r'from helpers import clean_amount\n\1', content, count=1, flags=re.MULTILINE)

    # Replace local definitions of parse_float_safe and limpiar_monto
    content = re.sub(r'[ \t]*def limpiar_monto\(.*?\):[\s\S]*?(?=\n[ \t]*\S|\n\n\n|$)', '', content)
    content = re.sub(r'[ \t]*def parse_float_safe\(.*?\):[\s\S]*?(?=\n[ \t]*\S|\n\n\n|$)', '', content)

    # Replace calls to them
    content = content.replace('parse_float_safe', 'clean_amount')
    content = content.replace('limpiar_monto', 'clean_amount')
    content = content.replace('parse_float', 'clean_amount')

    # Replace Decimal(request.form.get(...)) or float(request.form.get(...))
    content = re.sub(r'(?:Decimal|float)\(\s*(request\.form\.get\([^\)]+\))\s*\)', r'clean_amount(\1)', content)
    
    # Also replace direct assignment of raw string for monto/valor
    # e.g. monto = request.form.get("monto") -> monto = clean_amount(request.form.get("monto"))
    content = re.sub(r'=\s*request\.form\.get\([\'"](monto|valor|valor_total|valor_neto|valor_cancelado)[\'"](?:,\s*[\'"]0[\'"])?\)', r'= clean_amount(request.form.get("\1"))', content)
    
    if content != original_content:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated {file}")

print("Done")
