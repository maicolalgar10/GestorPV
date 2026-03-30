from .dashboard_controller import dashboard_bp
from .proyectos_controller import proyectos_bp
from .personal_controller import personal_bp
from .vehiculos_controller import vehiculos_bp
from .materiales_controller import materiales_bp
from .asistencia_controller import asistencia_bp
from .usuarios_controller import usuarios_bp
from .avances_controller import avances_bp
from .actividades_controller import actividades_bp
from .horarios_controller import horarios_bp
from .cotizaciones_controller import cotizaciones_bp
from .facturas_controller import facturas_bp

def register_controllers(app):
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(proyectos_bp)
    app.register_blueprint(personal_bp)
    app.register_blueprint(vehiculos_bp)
    app.register_blueprint(materiales_bp)
    app.register_blueprint(asistencia_bp)
    app.register_blueprint(usuarios_bp)
    app.register_blueprint(avances_bp)
    app.register_blueprint(actividades_bp)
    app.register_blueprint(horarios_bp)
    app.register_blueprint(cotizaciones_bp)
    app.register_blueprint(facturas_bp)
