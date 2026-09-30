import os
from pathlib import Path
from code_inspector import CodeInspector

def main():
    # Nos aseguramos de apuntar a la raíz del proyecto
    project_root = Path(__file__).parent.parent
    inspector = CodeInspector(project_root=str(project_root))
    
    # Probando sobre un archivo existente: controllers/avances_controller.py
    # Reemplaza la línea y columna según un símbolo real para que devuelva resultados
    target_file = project_root / "controllers" / "avances_controller.py"
    
    if not target_file.exists():
        print(f"El archivo {target_file} no existe. Por favor ajusta la ruta en el script.")
        return

    print(f"Buscando referencias en: {target_file.name}")
    
    try:
        # Se asume que en la línea 1, columna 0 o algo similar se define o importa algo
        # (Idealmente se probaría con la línea exacta de una clase o función)
        # Aquí hacemos una prueba dummy en la primera línea válida
        references = inspector.find_references(str(target_file), line=35, column=0)
        
        print(f"Se encontraron {len(references)} referencias en el proyecto:")
        for ref in references:
            print(f"- {ref['file_path']} (Línea {ref['line']}): {ref['code_line']}")
            
    except Exception as e:
        print(f"Ocurrió un error al ejecutar la inspección: {e}")

if __name__ == "__main__":
    main()
