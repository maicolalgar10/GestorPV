# Reglas de Comportamiento del Agente

REGLA OBLIGATORIA: Antes de renombrar, eliminar o modificar la firma de cualquier función, modelo de SQLAlchemy o vista de Flask, debes ejecutar `CodeInspector.find_references()` (desde `tools/code_inspector.py`) para listar todos los archivos que consumen ese símbolo. Limita tus ediciones estrictamente a los archivos retornados por esta consulta.
