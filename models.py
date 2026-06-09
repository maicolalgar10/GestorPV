from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import DateTime
from datetime import datetime
import enum
from sqlalchemy import func
from sqlalchemy.orm import object_session

db = SQLAlchemy()


# ===========================================
# 1. Usuarios y Roles (Login general)
# ===========================================
class Usuarios(db.Model):
    __tablename__ = "usuarios"

    id_usuario = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=False, nullable=False)
    password = db.Column(db.String(255), nullable=False)  # hashed
    rol = db.Column(db.Enum('ADMIN', 'BODEGA', 'EMPLEADO', 'OFICINA', name='rol_usuario_enum'), nullable=False)
    foto_perfil = db.Column(db.String(200), nullable=True, default="default.png")

    debe_cambiar_contrasena = db.Column(db.Boolean, default=True)  # 👈 nuevo campo
    reset_token = db.Column(db.String(100), nullable=True)  # 👈 nuevo campo

    # Relaciones
    avances = db.relationship("Avances", back_populates="usuario", passive_deletes=True)
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
    rol = db.Column(db.Enum('Ingeniero', 'Trabajador', 'Bodeguero', 'Administrativo', 'Otra', name='rol_personal_enum'), nullable=False)
    rol_personalizado = db.Column(db.String(100), nullable=True)

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
    
    asignaciones_diarias = db.relationship("AsignacionDiaria", back_populates="personal", cascade="all, delete-orphan")



# ===========================================
# 3. Proyectos
# ===========================================
class Proyectos(db.Model):
    __tablename__ = "proyectos"

    id_proyecto = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(150), nullable=False, index=True)  #  ÍNDICE
    lugar = db.Column(db.String(150), nullable=False)
    responsable_id = db.Column(db.Integer, db.ForeignKey("personal.id", ondelete='SET NULL', onupdate='CASCADE'), nullable=True, index=True)  #  ÍNDICE
    descripcion = db.Column(db.Text)

    fecha_inicio = db.Column(db.Date, nullable=False, index=True)   #  ÍNDICE
    fecha_fin = db.Column(db.Date, nullable=False, index=True)      #  ÍNDICE

    # Estado del Proyecto
    estado = db.Column(db.Enum('EN_PROGRESO', 'FINALIZADO', 'PENDIENTE', 'ATRASADO', name='estado_proyecto_enum'), default="PENDIENTE", index=True)  #  ÍNDICE

    #  Nuevo campo: fecha real en la que se terminó el proyecto
    fecha_fin_real = db.Column(db.Date, nullable=True)

    #  Campo para ocultar proyectos en vez de eliminarlos
    visible = db.Column(db.Boolean, default=True)  # Nuevo campo

    # Relaciones
    responsable = db.relationship("Personal", foreign_keys=[responsable_id])
    actividades = db.relationship("Actividades", back_populates="proyecto", cascade="all, delete-orphan")
    vehiculos = db.relationship("VehiculoProyecto", back_populates="proyecto", cascade="all, delete-orphan")
    materiales = db.relationship("MaterialesProyecto", back_populates="proyecto", cascade="all, delete-orphan")
    asistencias = db.relationship("Asistencia", back_populates="proyecto", cascade="all, delete-orphan")
    personal_asignado = db.relationship("ProyectoPersonal", back_populates="proyecto", cascade="all, delete-orphan")
    ubicaciones = db.relationship("ProyectoUbicacion", back_populates="proyecto", cascade="all, delete-orphan")
    horarios = db.relationship("Horario", back_populates="proyecto", cascade="all, delete-orphan")
    asignaciones_diarias = db.relationship("AsignacionDiaria", back_populates="proyecto", cascade="all, delete-orphan")

    # ===========================================
    # Lógica de Progreso (La "Solución de Oro")
    # ===========================================
    @property
    def progreso_general(self):
        """Calcula el progreso ponderado del proyecto combinando Python y SQL eficiente"""
        session = object_session(self)
        if session is None:
            return 0

        # 1. Total unidades (desde Python para evitar duplicados de Joins)
        total_unidades = sum((a.unidades_totales or 0) for a in self.actividades)

        if total_unidades == 0:
            return 0

        # 2. Total avanzado (Una sola consulta SQL agregada)
        avanzado = (
            session.query(func.sum(Avances.unidades_avanzadas))
            .join(Actividades)
            .filter(Actividades.id_proyecto == self.id_proyecto)
            .scalar()
        ) or 0

        return round((avanzado / total_unidades) * 100, 1)


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
    id_proyecto = db.Column(db.Integer, db.ForeignKey("proyectos.id_proyecto", ondelete="CASCADE"), nullable=False, index=True)  # ✅ ÍNDICE
    id_ubicacion = db.Column(db.Integer, db.ForeignKey("proyecto_ubicacion.id", ondelete="CASCADE"), nullable=True)

    nombre = db.Column(db.String(150), nullable=False)
    descripcion = db.Column(db.Text)
    unidades_totales = db.Column(db.Integer, nullable=True)

    # Relaciones
    proyecto = db.relationship("Proyectos", back_populates="actividades")
    ubicacion = db.relationship("ProyectoUbicacion", back_populates="actividades")
    avances = db.relationship("Avances", back_populates="actividad", cascade="all, delete-orphan")

    
    @property
    def unidades_avanzadas(self):
        """Calcula la suma de todas las unidades reportadas para esta actividad."""
        from models import Avances
        session = object_session(self)
        if session is None: return 0
        
        total = session.query(func.sum(Avances.unidades_avanzadas))\
                       .filter(Avances.id_actividad == self.id_actividad)\
                       .scalar()
        return total or 0

    @property
    def porcentaje_progreso(self):
        """Calcula el porcentaje de esta actividad individual."""
        if not self.unidades_totales or self.unidades_totales == 0:
            return 0
        porcentaje = (self.unidades_avanzadas / self.unidades_totales) * 100
        return min(round(porcentaje, 1), 100) # Evita que pase del 100%

# ===========================================
# 5. Avances
# ===========================================
class Avances(db.Model):
    __tablename__ = "avances"

    id_avance = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_actividad = db.Column(db.Integer, db.ForeignKey("actividades.id_actividad", ondelete="CASCADE"), nullable=False)
    id_usuario = db.Column(db.Integer, db.ForeignKey("usuarios.id_usuario", ondelete="SET NULL"), nullable=True)
    fecha = db.Column(db.Date, default=datetime.utcnow)
    unidades_avanzadas = db.Column(db.Integer, nullable=True)
    mensaje = db.Column(db.Text)

    trayecto = db.Column(db.String(100))
    calzada = db.Column(db.String(100))
    carril = db.Column(db.String(100))
    ubicacion_pr = db.Column(db.String(100))
    tipo = db.Column(db.String(100))
    elemento = db.Column(db.String(100))
    area_elemento = db.Column(db.Float)
    area_total = db.Column(db.Float)

    # Relaciones
    actividad = db.relationship("Actividades", back_populates="avances")
    usuario = db.relationship("Usuarios", back_populates="avances")
    evidencias = db.relationship("Evidencias", back_populates="avance", cascade="all, delete-orphan")
    materiales_usados = db.relationship("AvanceMaterial", back_populates="avance", cascade="all, delete-orphan")

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

    #  Asignación actual del vehículo
    proyecto_actual_id = db.Column(db.Integer, db.ForeignKey("proyectos.id_proyecto"), nullable=True)
    ubicacion_actual = db.Column(db.String(100), nullable=True)

    # Relaciones
    movimientos = db.relationship("MovimientoVehiculo", back_populates="vehiculo", cascade="all, delete-orphan")
    usos = db.relationship("VehiculoProyecto", back_populates="vehiculo", cascade="all, delete-orphan")
    mantenimientos = db.relationship("MantenimientoVehiculo", back_populates="vehiculo", cascade="all, delete-orphan")

    # Relación con Proyecto actual
    proyecto_actual = db.relationship("Proyectos", foreign_keys=[proyecto_actual_id])


class VehiculoProyecto(db.Model):
    __tablename__ = "vehiculo_proyecto"

    id_vp = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_vehiculo = db.Column(db.Integer, db.ForeignKey("vehiculos.id_vehiculo"), nullable=False, index=True)  # ✅ ÍNDICE
    id_proyecto = db.Column(db.Integer, db.ForeignKey("proyectos.id_proyecto"), nullable=False, index=True)  # ✅ ÍNDICE
    fecha = db.Column(db.Date, default=datetime.utcnow)
    hora = db.Column(db.Time, nullable=True)
    observacion = db.Column(db.Text)
    nombre_proyecto_eliminado = db.Column(db.String(150), nullable=True)  # Nuevo campo

    vehiculo = db.relationship("Vehiculos", back_populates="usos")
    proyecto = db.relationship("Proyectos", back_populates="vehiculos")

    # Índice compuesto
    __table_args__ = (
        db.Index('idx_vehiculo_proyecto_proyecto_vehiculo', 'id_proyecto', 'id_vehiculo'),  # ✅ BIEN
    )


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
    

class MaterialesProyecto(db.Model):
    __tablename__ = "materiales_proyecto"

    id_mp = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_material = db.Column(db.Integer, db.ForeignKey("materiales.id_material"), nullable=False, index=True)  # ÍNDICE
    id_proyecto = db.Column(db.Integer, db.ForeignKey("proyectos.id_proyecto"), nullable=False, index=True)   # ÍNDICE

    cantidad = db.Column(db.Integer, nullable=False)
    estado = db.Column(db.Enum('PENDIENTE', 'EN_PROCESO', 'LISTO', name='estado_material_enum'), default="PENDIENTE")
    fecha_entrega = db.Column(db.Date, nullable=True)
    usado_en = db.Column(db.DateTime, default=datetime.utcnow)

    proyecto = db.relationship("Proyectos", back_populates="materiales")
    material = db.relationship("Materiales")

    # Índice compuesto
    __table_args__ = (
        db.Index('idx_materiales_proyecto_proyecto_material', 'id_proyecto', 'id_material'),  #  BIEN
    )


# ===========================================
# 9.1 HistorialMateriales (nuevo modelo para registro de eliminación)
# ===========================================
class HistorialMateriales(db.Model):
    __tablename__ = "historial_materiales"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    # Proyecto eliminado (nombre original)
    nombre_proyecto_eliminado = db.Column(db.String(150), nullable=False)
    # Material eliminado
    id_material = db.Column(db.Integer, db.ForeignKey("materiales.id_material"), nullable=False)
    nombre_material = db.Column(db.String(100), nullable=False)  # Guardar nombre por si se elimina el material
    unidad_material = db.Column(db.String(20), nullable=False)   # Guardar unidad por si se elimina el material
    cantidad = db.Column(db.Integer, nullable=False)  # Cantidad que se "gastó"
    # Fecha de eliminación
    fecha_registro = db.Column(db.Date, default=datetime.utcnow)
    # Motivo
    motivo = db.Column(db.String(200), default="Proyecto eliminado")

    # Relación
    material = db.relationship("Materiales", backref="historial_uso")




# ===========================================
# 9.2 Inventario Real de Bodega (Independiente)
# ===========================================
class InventarioBodega(db.Model):
    __tablename__ = "inventario_bodega"

    id_ib = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre_item = db.Column(db.String(150), nullable=False) # Ej: "Pintura Azul Pintuco"
    unidad = db.Column(db.String(20), nullable=False)
    stock_actual = db.Column(db.Integer, default=0, nullable=False)
    stock_minimo = db.Column(db.Integer, default=0, nullable=False)



# ===========================================
# 10. Asistencia
# ===========================================
class Asistencia(db.Model):
    __tablename__ = "asistencia"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    personal_id = db.Column(db.Integer, db.ForeignKey("personal.id", ondelete="SET NULL"), nullable=True)
    proyecto_id = db.Column(db.Integer, db.ForeignKey("proyectos.id_proyecto", ondelete="CASCADE"), nullable=False)
    fecha = db.Column(db.Date, nullable=False)
    trabajo_manana = db.Column(db.Boolean, default=False)
    trabajo_tarde = db.Column(db.Boolean, default=False)
    horas_trabajadas = db.Column(db.Integer, default=0)  # Ej: 8, 6, 4
    motivo = db.Column(db.String(200), nullable=True)   # Ej: "permiso médico"
    nombre_proyecto_eliminado = db.Column(db.String(150), nullable=True)  # Nuevo campo

    personal = db.relationship("Personal", back_populates="asistencias")
    proyecto = db.relationship("Proyectos", back_populates="asistencias")


# ===========================================
# 11. ProyectoPersonal (N:N entre proyecto y personal)
# ===========================================
class ProyectoPersonal(db.Model):
    __tablename__ = "proyecto_personal"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    proyecto_id = db.Column(db.Integer, db.ForeignKey("proyectos.id_proyecto", ondelete="CASCADE"), nullable=False, index=True)  # ✅ ÍNDICE
    personal_id = db.Column(db.Integer, db.ForeignKey("personal.id", ondelete="CASCADE"), nullable=True, index=True)  # ✅ ÍNDICE

    proyecto = db.relationship("Proyectos", back_populates="personal_asignado")
    personal = db.relationship("Personal", back_populates="proyectos")
    
    # Índice compuesto para optimizar JOINs frecuentes
    __table_args__ = (
        db.Index('idx_proyecto_personal_proyecto_personal', 'proyecto_id', 'personal_id'),  # ✅
    )


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


# ===========================================
# 13. AsignacionDiaria
# ===========================================
class AsignacionDiaria(db.Model):
    __tablename__ = "asignacion_diaria"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    fecha = db.Column(db.Date, nullable=False) # Fecha de la asignación
    proyecto_id = db.Column(db.Integer, db.ForeignKey("proyectos.id_proyecto"), nullable=False)
    personal_id = db.Column(db.Integer, db.ForeignKey("personal.id"), nullable=False) # El personal específico asignado
    hora_entrada = db.Column(db.Time, nullable=False) # Hora de entrada
    observacion = db.Column(db.Text, nullable=True) # Observación opcional

    proyecto = db.relationship("Proyectos", back_populates="asignaciones_diarias")
    personal = db.relationship("Personal", back_populates="asignaciones_diarias")


# ===========================================
# 14. SolicitudMateriales
# ===========================================
class SolicitudMateriales(db.Model):
    __tablename__ = "solicitudes_materiales"

    id_solicitud = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_proyecto = db.Column(db.Integer, db.ForeignKey("proyectos.id_proyecto"), nullable=False)
    id_usuario_solicitante = db.Column(db.Integer, db.ForeignKey("usuarios.id_usuario"), nullable=False)  # Admin que solicita
    id_usuario_responsable = db.Column(db.Integer, db.ForeignKey("usuarios.id_usuario"), nullable=True)  # Bodega que procesa
    fecha_solicitud = db.Column(db.Date, default=datetime.today)  # Fecha automática
    fecha_actualizacion = db.Column(db.Date, default=datetime.today)
    estado = db.Column(
        db.Enum('PENDIENTE', 'EN_PROCESO', 'COMPLETADO', 'RECHAZADO', name='estado_solicitud_enum'),
        default='PENDIENTE'
    )   
    observaciones = db.Column(db.Text)
    archivo_ruta = db.Column(db.String(255), nullable=True)

    # El trabajador puede "borrarlo" de su vista, pero el dato sigue vivo
    visible_para_trabajador = db.Column(db.Boolean, default=True, nullable=False)
    visible_para_bodega = db.Column(db.Boolean, default=True)

    nombre_proyecto_eliminado = db.Column(db.String(150), nullable=True)  # Nuevo campo

    # CAMPOS MOVIDOS DESDE (de Detalle a Solicitud)
    fecha_entrega_estimada = db.Column(db.Date, nullable=True)
    observacion_bodega = db.Column(db.Text, nullable=True)

    # Relaciones
    proyecto = db.relationship("Proyectos")
    usuario_solicitante = db.relationship("Usuarios", foreign_keys=[id_usuario_solicitante])
    usuario_responsable = db.relationship("Usuarios", foreign_keys=[id_usuario_responsable])
    detalles = db.relationship("DetalleSolicitudMaterial", back_populates="solicitud", cascade="all, delete-orphan")



# ===========================================
# 15. Registro de consumo real por reporte
# ===========================================
class AvanceMaterial(db.Model):
    __tablename__ = "avance_material"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_avance = db.Column(db.Integer, db.ForeignKey("avances.id_avance", ondelete="CASCADE"), nullable=False)
    id_material = db.Column(db.Integer, db.ForeignKey("materiales.id_material"), nullable=False)
    
    # Esta es la cantidad que el trabajador ingresa en los campos de tu dibujo
    cantidad_usada = db.Column(db.Float, nullable=False, default=0.0)

    # Relaciones para acceder fácil a los nombres
    avance = db.relationship("Avances", back_populates="materiales_usados")
    material = db.relationship("Materiales")


# ===========================================
#    Cotizaciones
# ===========================================
class Cotizacion(db.Model):
    __tablename__ = "cotizaciones"

    id = db.Column(db.Integer, primary_key=True)
    cliente = db.Column(db.String(150), nullable=False)
    proyecto = db.Column(db.String(150), nullable=False)
    numero_cotizacion = db.Column(db.String(50), unique=True, nullable=False)

    estado = db.Column(
        db.Enum("PENDIENTE", "ACEPTADA", "RECHAZADA", name="estado_cotizacion_enum"),
        default="PENDIENTE",
        nullable=False
    )

    imagen_cotizacion = db.Column(db.String(250), nullable=True)

    contrato = db.relationship(
        "Contrato",
        uselist=False,
        back_populates="cotizacion"
    )
# ===========================================


# 17. Contratos (Antes Facturas)
class Contrato(db.Model):
    __tablename__ = "contratos"

    id = db.Column(db.Integer, primary_key=True)

    cotizacion_id = db.Column(
        db.Integer,
        db.ForeignKey("cotizaciones.id", ondelete="CASCADE"),
        nullable=False,
        unique=True
    )

    cliente = db.Column(db.String(150), nullable=False)
    proyecto = db.Column(db.String(150), nullable=False)

    estado = db.Column(
        db.Enum("activo", "pausado", "cerrado", name="estado_contrato_enum"),
        default="activo",
        nullable=False
    )

    valor_total = db.Column(db.Numeric(12, 2), nullable=False)
    anticipo_porcentaje = db.Column(db.Numeric(5, 2), default=0) # ej: 20.00
    valor_anticipo = db.Column(db.Numeric(12, 2), default=0) # Calculado
    retencion_garantia_porcentaje = db.Column(db.Numeric(5, 2), default=0) # ej: 10.00
    
    total_sin_iva = db.Column(db.Numeric(12, 2), default=0) # Manteniendo el campo base opcional

    cotizacion = db.relationship(
        "Cotizacion",
        back_populates="contrato"
    )

# ===========================================
# 17.1 Bancos
# ===========================================
class Bancos(db.Model):
    __tablename__ = "bancos"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre_banco = db.Column(db.String(150), nullable=False)
    numero_cuenta = db.Column(db.String(100), nullable=False)
    saldo_actual = db.Column(db.Numeric(12, 2), default=0, nullable=False)
    color = db.Column(db.String(7), nullable=True, default="#004481")
    
    # Nuevos campos específicos para Belvo
    belvo_link_id = db.Column(db.String(100), nullable=True)
    belvo_institution = db.Column(db.String(100), nullable=True)
    
    movimientos = db.relationship("Movimientos", back_populates="banco", cascade="all, delete-orphan")


# ===========================================
# 16. Movimientos (Registro de Tesorería)
# ===========================================
class Movimientos(db.Model):
    __tablename__ = "movimientos"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    contrato_id = db.Column(
        db.Integer,
        db.ForeignKey("contratos.id", ondelete="CASCADE"),
        nullable=True # Puede ser nulo si es un gasto que no pertenece a un contrato
    )
    
    banco_id = db.Column(
        db.Integer,
        db.ForeignKey("bancos.id", ondelete="CASCADE"),
        nullable=False
    )
    
    tipo = db.Column(
        db.Enum('INGRESO', 'EGRESO', name='tipo_movimiento_enum'),
        nullable=False
    )

    categoria = db.Column(
        db.Enum(
            'anticipo', 'acta', 'nomina', 'materiales', 'maquinaria', 'subcontrato', 'seguros', 'saldo_inicial',
            name='categoria_movimiento_enum'
        ),
        nullable=False
    )
    
    valor_bruto = db.Column(db.Numeric(12, 2), nullable=False)
    amortizacion_anticipo = db.Column(db.Numeric(12, 2), default=0)
    retencion_garantia = db.Column(db.Numeric(12, 2), default=0)
    valor_neto = db.Column(db.Numeric(12, 2), nullable=False)

    fecha_movimiento = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    numero_documento = db.Column(db.String(100), nullable=True)
    archivo_soporte = db.Column(db.String(255), nullable=True)

    creado_en = db.Column(db.DateTime, default=datetime.utcnow)

    contrato = db.relationship(
        "Contrato",
        backref=db.backref("movimientos", cascade="all, delete-orphan")
    )
    
    banco = db.relationship(
        "Bancos",
        back_populates="movimientos"
    )



class DetalleSolicitudMaterial(db.Model):
    __tablename__ = "detalle_solicitud_material"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_solicitud = db.Column(db.Integer, db.ForeignKey("solicitudes_materiales.id_solicitud", ondelete="CASCADE"), nullable=False)
    id_material = db.Column(db.Integer, db.ForeignKey("materiales.id_material"), nullable=True) # Recuerda el nullable=True para el borrado del admin
    
    nombre_material_escrito = db.Column(db.String(255), nullable=True)

    # LO QUE PIDE EL ADMIN
    cantidad = db.Column(db.Integer, nullable=False, default=1) 

    # LO QUE ENTREGA BODEGA (NUEVO)
    cantidad_entregada = db.Column(db.Integer, default=0) 

    # Relaciones
    solicitud = db.relationship("SolicitudMateriales", back_populates="detalles")
    material = db.relationship("Materiales")

# ===========================================
# 18. Requisiciones a Oficina (Bodega -> Oficina)
# ===========================================
class RequisicionOficina(db.Model):
    __tablename__ = "requisiciones_oficina"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    bodeguero_id = db.Column(db.Integer, db.ForeignKey("usuarios.id_usuario"), nullable=False)
    fecha_solicitud = db.Column(db.DateTime, default=datetime.utcnow)
    estado = db.Column(
        db.Enum('PENDIENTE', 'APROBADA', 'COMPRADA', 'RECHAZADA', name='estado_req_oficina_enum'),
        default='PENDIENTE'
    )
    observaciones = db.Column(db.Text, nullable=True)

    bodeguero = db.relationship("Usuarios", backref="requisiciones_realizadas")
    detalles = db.relationship("DetalleRequisicionOficina", back_populates="requisicion", cascade="all, delete-orphan")

class DetalleRequisicionOficina(db.Model):
    __tablename__ = "detalle_requisicion_oficina"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    requisicion_id = db.Column(db.Integer, db.ForeignKey("requisiciones_oficina.id"), nullable=False)
    material_texto = db.Column(db.String(255), nullable=False)
    cantidad = db.Column(db.String(100), nullable=False)

    requisicion = db.relationship("RequisicionOficina", back_populates="detalles")