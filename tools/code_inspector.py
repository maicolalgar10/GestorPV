import jedi
from pathlib import Path
from typing import List, Dict, Any

class CodeInspector:
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root).resolve()

    def find_definition(self, file_path: str, line: int, column: int) -> List[Dict[str, Any]]:
        """Encuentra dónde está definida la función, clase o variable."""
        script = jedi.Script(path=file_path)
        definitions = script.goto(line=line, column=column)
        return [
            {
                "module_path": str(d.module_path),
                "line": d.line,
                "column": d.column,
                "name": d.name,
                "type": d.type,
            }
            for d in definitions
            if d.module_path
        ]

    def find_references(self, file_path: str, line: int, column: int) -> List[Dict[str, Any]]:
        """Encuentra en qué partes del proyecto se utiliza el símbolo especificado."""
        script = jedi.Script(path=file_path)
        references = script.get_references(line=line, column=column)
        
        results = []
        for ref in references:
            if ref.module_path and self.project_root in Path(ref.module_path).resolve().parents or Path(ref.module_path).resolve() == self.project_root:
                results.append({
                    "file_path": str(ref.module_path),
                    "line": ref.line,
                    "column": ref.column,
                    "code_line": ref.get_line_code().strip(),
                    "is_definition": ref.is_definition()
                })
        return results
