from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import DateTime
from datetime import datetime

db = SQLAlchemy()


# ===========================================
# 1. Usuarios y Roles (Login general)
# ===========================================
class Usuarios(db.Model):
    __tablename__ = "usuarios"

    id_usuario = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)  # hashed
    rol = db.Column(db.Enum('ADMIN', 'ENCARGADO', 'EMPLEADO', name='rol_usuario_enum'), nullable=False)
    foto_perfil = db.Column(db.String(200), nullable=True, default="default.png")

    debe_cambiar_contrasena = db.Column(db.Boolean, default=True)  # 👈 nuevo campo
    reset_token = db.Column(db.String(100), nullable=True)  # 👈 nuevo campo



    # Relaciones
    avances = db.relationship("Avances", back_populates="usuario", cascade="all, delete-orphan")
    notificaciones = db.relationship("Notificaciones", back_populates="destinatario", cascade="all, delete-orphan")

    # Relación uno a uno con Personal
    personal_id = db.Column(db.Integer, db.ForeignKey("personal.id", ondelete="SET NULL"), nullable=True)
    personal_data = db.relationship("Personal", back_populates="usuario_data")



# ===========================================
# 2. Personal operativo (distinto al login)
# ===========================================
class Personal(db.Model):
    __tablename__ = "personal"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(100), nullable=False)
    rol = db.Column(db.Enum('Ingeniero', 'Trabajador', 'Supervisor', name='rol_personal_enum'), nullable=False)
    activo = db.Column(db.Boolean, default=True)
    costo_diario = db.Column(db.Numeric(10, 2), nullable=False)
    contacto = db.Column(db.String(50), nullable=True, unique=True)

    # Relaciones
    proyectos = db.relationship("ProyectoPersonal", back_populates="personal", cascade="all, delete-orphan")
    asistencias = db.relationship("Asistencia", back_populates="personal", cascade="all, delete-orphan")
    horarios = db.relationship("Horario", back_populates="personal", cascade="all, delete-orphan")

    # Relación uno a uno con Usuarios
    usuario_data = db.relationship(
        "Usuarios",
        back_populates="personal_data",
        uselist=False)

    ##materiales = db.relationship("MaterialesProyecto", back_populates="responsable", cascade="all, delete-orphan")



    # ===========================================
    # 3. Proyectos
    # ===========================================
class Proyectos(db.Model):
    __tablename__ = "proyectos"

    id_proyecto = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(150), nullable=False)
    lugar = db.Column(db.String(150), nullable=False)
    responsable_id = db.Column(db.Integer, db.ForeignKey("personal.id", ondelete='RESTRICT', onupdate='CASCADE'), nullable=True)
    descripcion = db.Column(db.Text)

    fecha_inicio = db.Column(db.Date, nullable=False)   
    fecha_fin = db.Column(db.Date, nullable=False)
    estado = db.Column(db.Enum('EN_PROGRESO', 'FINALIZADO', 'PENDIENTE', 'ATRASADO', name='estado_proyecto_enum'), default="PENDIENTE")

    # 🔹 Nuevo campo: fecha real en la que se terminó el proyecto
    fecha_fin_real = db.Column(db.Date, nullable=True)

        # Relaciones
    responsable = db.relationship("Personal", foreign_keys=[responsable_id])
    actividades = db.relationship("Actividades", back_populates="proyecto", cascade="all, delete-orphan")
    vehiculos = db.relationship("VehiculoProyecto", back_populates="proyecto", cascade="all, delete-orphan")
    materiales = db.relationship("MaterialesProyecto", back_populates="proyecto", cascade="all, delete-orphan")
    asistencias = db.relationship("Asistencia", back_populates="proyecto", cascade="all, delete-orphan")
    personal_asignado = db.relationship("ProyectoPersonal", back_populates="proyecto", cascade="all, delete-orphan")
    ubicaciones = db.relationship("ProyectoUbicacion", back_populates="proyecto", cascade="all, delete-orphan")
    horarios = db.relationship("Horario", back_populates="proyecto", cascade="all, delete-orphan")


    # ===========================================
    # 3.1 ProyectoUbicacion (avance por ciudad/zona)
    # ===========================================
class ProyectoUbicacion(db.Model):
    __tablename__ = 'proyecto_ubicacion'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    proyecto_id = db.Column(
            db.Integer,
            db.ForeignKey('proyectos.id_proyecto', ondelete='CASCADE', onupdate='CASCADE'),
            nullable=False
        )
    nombre = db.Column(db.String(120), nullable=False)   # Ej: Bogotá
    direccion = db.Column(db.String(200))                # Opcional: dirección exacta
    fecha_inicio = db.Column(db.Date, nullable=False)
    fecha_fin = db.Column(db.Date, nullable=True)
    estado = db.Column(
            db.Enum('Planeado', 'En ejecución', 'Finalizado', name='estado_ubicacion_enum'),
            default='Planeado',
            nullable=False
        )
    progreso = db.Column(db.Integer, default=0)  # % de avance

    proyecto = db.relationship('Proyectos', back_populates='ubicaciones')

    actividades = db.relationship("Actividades", back_populates="ubicacion", cascade="all, delete-orphan")


    __table_args__ = (
            db.UniqueConstraint('proyecto_id', 'nombre', name='uix_proyecto_ubicacion_nombre'),
        )


    # ===========================================
    # 4. Actividades
    # ===========================================
class Actividades(db.Model):
    __tablename__ = "actividades"

    id_actividad = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_proyecto = db.Column(db.Integer, db.ForeignKey("proyectos.id_proyecto", ondelete="CASCADE"), nullable=False)
    id_ubicacion = db.Column(db.Integer, db.ForeignKey("proyecto_ubicacion.id", ondelete="CASCADE"), nullable=True)

    nombre = db.Column(db.String(150), nullable=False)
    descripcion = db.Column(db.Text)
    unidades_totales = db.Column(db.Integer, nullable=True)

        # Relaciones
    proyecto = db.relationship("Proyectos", back_populates="actividades")
    ubicacion = db.relationship("ProyectoUbicacion", back_populates="actividades")
    avances = db.relationship("Avances", back_populates="actividad", cascade="all, delete-orphan")


    # ===========================================
    # 5. Avances
    # ===========================================
class Avances(db.Model):
    __tablename__ = "avances"

    id_avance = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_actividad = db.Column(db.Integer, db.ForeignKey("actividades.id_actividad", ondelete="CASCADE"), nullable=False)
    id_usuario = db.Column(db.Integer, db.ForeignKey("usuarios.id_usuario"), nullable=False)
    fecha = db.Column(db.Date, default=datetime.utcnow)
    unidades_avanzadas = db.Column(db.Integer, nullable=True)
    mensaje = db.Column(db.Text)

        # Relaciones
    actividad = db.relationship("Actividades", back_populates="avances")
    usuario = db.relationship("Usuarios", back_populates="avances")
    evidencias = db.relationship("Evidencias", back_populates="avance", cascade="all, delete-orphan")


# ===========================================
# 6. Evidencias
# ===========================================
class Evidencias(db.Model):
    __tablename__ = "evidencias"

    id_evidencia = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_avance = db.Column(db.Integer, db.ForeignKey("avances.id_avance", ondelete="CASCADE"), nullable=False)
    ruta_archivo = db.Column(db.String(255), nullable=False)
    tipo = db.Column(db.String(50), nullable=False)
    subido_en = db.Column(db.DateTime, default=datetime.utcnow)

    # Relaciones
    avance = db.relationship("Avances", back_populates="evidencias")


# ===========================================
# 7. Notificaciones
# ===========================================
class Notificaciones(db.Model):
    __tablename__ = "notificaciones"

    id_notificacion = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_usuario_destino = db.Column(db.Integer, db.ForeignKey("usuarios.id_usuario"), nullable=False)
    mensaje = db.Column(db.Text, nullable=False)
    leido = db.Column(db.Boolean, default=False)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)
    id_horario = db.Column(db.Integer, db.ForeignKey("horarios.id", ondelete="CASCADE"), nullable=True) 

    # Relaciones
    destinatario = db.relationship("Usuarios", back_populates="notificaciones")


# ===========================================
# 8. Vehiculos
# ===========================================
# models.py
class Vehiculos(db.Model):
    __tablename__ = "vehiculos"

    id_vehiculo = db.Column(db.Integer, primary_key=True, autoincrement=True)
    placa = db.Column(db.String(20), unique=True, nullable=False)
    marca = db.Column(db.String(100), nullable=False)
    modelo = db.Column(db.String(100), nullable=False)
    documentos_al_dia = db.Column(db.Boolean, default=True)
    soat_vencimiento = db.Column(db.Date, nullable=False)
    tecno_vencimiento = db.Column(db.Date, nullable=False)
    estado = db.Column(db.Enum('Disponible', 'En uso', 'Mantenimiento', name='estado_vehiculo_enum'), default='Disponible')

    updated_at = db.Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 🔸 Asignación actual del vehículo
    proyecto_actual_id = db.Column(db.Integer, db.ForeignKey("proyectos.id_proyecto"), nullable=True)
    ubicacion_actual = db.Column(db.String(100), nullable=True)

    # Relaciones
    # 👇 Asegúrate de que esta línea ESTÉ en la clase Vehiculos
    movimientos = db.relationship("MovimientoVehiculo", back_populates="vehiculo", cascade="all, delete-orphan")

    usos = db.relationship("VehiculoProyecto", back_populates="vehiculo", cascade="all, delete-orphan")
    mantenimientos = db.relationship("MantenimientoVehiculo", back_populates="vehiculo", cascade="all, delete-orphan")

    # Relación con Proyecto actual
    proyecto_actual = db.relationship("Proyectos", foreign_keys=[proyecto_actual_id])


class VehiculoProyecto(db.Model):
    __tablename__ = "vehiculo_proyecto"

    id_vp = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_vehiculo = db.Column(db.Integer, db.ForeignKey("vehiculos.id_vehiculo"), nullable=False)
    id_proyecto = db.Column(db.Integer, db.ForeignKey("proyectos.id_proyecto"), nullable=False)
    fecha = db.Column(db.Date, default=datetime.utcnow)
    hora = db.Column(db.Time, nullable=True)
    observacion = db.Column(db.Text)

    vehiculo = db.relationship("Vehiculos", back_populates="usos")
    proyecto = db.relationship("Proyectos", back_populates="vehiculos")


class MovimientoVehiculo(db.Model):
    __tablename__ = "movimiento_vehiculo"

    id_movimiento = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_vehiculo = db.Column(db.Integer, db.ForeignKey("vehiculos.id_vehiculo", ondelete="CASCADE"), nullable=False)
    id_usuario = db.Column(db.Integer, db.ForeignKey("usuarios.id_usuario", ondelete="SET NULL"), nullable=True)  # Quién hizo el cambio
    fecha_hora = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    proyecto_anterior_id = db.Column(db.Integer, db.ForeignKey("proyectos.id_proyecto"), nullable=True)  # De dónde vino
    proyecto_nuevo_id = db.Column(db.Integer, db.ForeignKey("proyectos.id_proyecto"), nullable=True)  # A dónde va
    ubicacion_anterior = db.Column(db.String(100), nullable=True)  # Desde dónde
    ubicacion_nueva = db.Column(db.String(100), nullable=True)  # Hacia dónde
    motivo = db.Column(db.Text, nullable=True)  # Por qué se hizo el cambio

    vehiculo = db.relationship("Vehiculos", back_populates="movimientos")
    usuario = db.relationship("Usuarios", foreign_keys=[id_usuario])
    proyecto_anterior = db.relationship("Proyectos", foreign_keys=[proyecto_anterior_id])
    proyecto_nuevo = db.relationship("Proyectos", foreign_keys=[proyecto_nuevo_id])



# ===========================================
# 8.1 MantenimientoVehiculo
# ===========================================
class MantenimientoVehiculo(db.Model):
    __tablename__ = "mantenimiento_vehiculo"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    vehiculo_id = db.Column(
        db.Integer,
        db.ForeignKey("vehiculos.id_vehiculo", ondelete="CASCADE"),
        nullable=False
    )
    fecha = db.Column(db.Date, nullable=False)
    tipo = db.Column(db.String(100))       # Preventivo, Correctivo, etc.
    observaciones = db.Column(db.Text)
    proximo = db.Column(db.Date, nullable=True)

    vehiculo = db.relationship("Vehiculos", back_populates="mantenimientos")


# ===========================================
# 9. Materiales
# ===========================================
class Materiales(db.Model):
    __tablename__ = "materiales"

    id_material = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(100), nullable=False)
    unidad = db.Column(db.String(20), nullable=False)
    cantidad = db.Column(db.Integer, default=0, nullable=False)       # Stock actual
    stock_minimo = db.Column(db.Integer, default=0, nullable=False)


class MaterialesProyecto(db.Model):
    __tablename__ = "materiales_proyecto"

    id_mp = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_material = db.Column(db.Integer, db.ForeignKey("materiales.id_material"), nullable=False)
    id_proyecto = db.Column(db.Integer, db.ForeignKey("proyectos.id_proyecto"), nullable=False)
    ##responsable_id = db.Column(db.Integer, db.ForeignKey("personal.id"), nullable=True)

    cantidad = db.Column(db.Integer, nullable=False)
    estado = db.Column(db.Enum('PENDIENTE', 'EN_PROCESO', 'LISTO', name='estado_material_enum'), default="PENDIENTE")
    fecha_entrega = db.Column(db.Date, nullable=True)
    usado_en = db.Column(db.DateTime, default=datetime.utcnow)

    proyecto = db.relationship("Proyectos", back_populates="materiales")
    ##responsable = db.relationship("Personal", back_populates="materiales")
    material = db.relationship("Materiales")


# ===========================================
# 10. Asistencia
# ===========================================
class Asistencia(db.Model):
    __tablename__ = "asistencia"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    personal_id = db.Column(db.Integer, db.ForeignKey("personal.id", ondelete="CASCADE"), nullable=False)
    proyecto_id = db.Column(db.Integer, db.ForeignKey("proyectos.id_proyecto", ondelete="CASCADE"), nullable=False)
    fecha = db.Column(db.Date, nullable=False)
    trabajo_manana = db.Column(db.Boolean, default=False)
    trabajo_tarde = db.Column(db.Boolean, default=False)
    horas_trabajadas = db.Column(db.Integer, default=0)  # Ej: 8, 6, 4
    motivo = db.Column(db.String(200), nullable=True)   # Ej: "permiso médico"

    personal = db.relationship("Personal", back_populates="asistencias")
    proyecto = db.relationship("Proyectos", back_populates="asistencias")


# ===========================================
# 11. ProyectoPersonal (N:N entre proyecto y personal)
# ===========================================
class ProyectoPersonal(db.Model):
    __tablename__ = "proyecto_personal"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    proyecto_id = db.Column(db.Integer, db.ForeignKey("proyectos.id_proyecto", ondelete="CASCADE"), nullable=False)
    personal_id = db.Column(db.Integer, db.ForeignKey("personal.id", ondelete="CASCADE"), nullable=False)

    proyecto = db.relationship("Proyectos", back_populates="personal_asignado")
    personal = db.relationship("Personal", back_populates="proyectos")
    


# ===========================================
# 12. Horarios
# ===========================================
class Horario(db.Model):
    __tablename__ = "horarios"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # Relaciones
    personal_id = db.Column(db.Integer, db.ForeignKey("personal.id", ondelete="CASCADE"), nullable=False)
    proyecto_id = db.Column(db.Integer, db.ForeignKey("proyectos.id_proyecto", ondelete="CASCADE"), nullable=False)

    # Campos principales
    fecha = db.Column(db.Date, nullable=False, default=datetime.utcnow)  # Fecha del registro
    hora_entrada = db.Column(db.Time, nullable=False)  # Solo hora de entrada

    # Opcional
    observacion = db.Column(db.String(200), nullable=True)  # Ej: "Retraso por tráfico", etc.

    # Relaciones inversas
    personal = db.relationship("Personal", back_populates="horarios")
    proyecto = db.relationship("Proyectos", back_populates="horarios")

