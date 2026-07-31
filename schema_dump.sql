CREATE TABLE bancos (
	id SERIAL NOT NULL, 
	nombre_banco VARCHAR(150) NOT NULL, 
	numero_cuenta VARCHAR(100) NOT NULL, 
	saldo_actual NUMERIC(12, 2) NOT NULL, 
	color VARCHAR(7), 
	pluggy_item_id VARCHAR(100), 
	pluggy_connector_id VARCHAR(100), 
	PRIMARY KEY (id)
);

CREATE TABLE clientes (
	id SERIAL NOT NULL, 
	nombre_cliente VARCHAR(150) NOT NULL, 
	nit VARCHAR(50), 
	contacto VARCHAR(100), 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE comprobantes_egreso (
	id SERIAL NOT NULL, 
	numero_comprobante INTEGER NOT NULL, 
	fecha DATE NOT NULL, 
	concepto TEXT NOT NULL, 
	valor NUMERIC(12, 2) NOT NULL, 
	metodo_pago VARCHAR(20) NOT NULL, 
	numero_cheque VARCHAR(50), 
	archivo_url VARCHAR(500), 
	banco VARCHAR(100), 
	debitese_a VARCHAR(150) NOT NULL, 
	tipo_documento VARCHAR(10), 
	documento_numero VARCHAR(50), 
	elaborado_por VARCHAR(100) NOT NULL, 
	aprobado_por VARCHAR(100) NOT NULL, 
	fecha_creacion TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	UNIQUE (numero_comprobante)
);

CREATE TABLE contratista_facturas (
	id SERIAL NOT NULL, 
	nombre_contratista VARCHAR(200) NOT NULL, 
	orden_compra_url VARCHAR(500), 
	comprobante_compra_url VARCHAR(500), 
	banco_pago_url VARCHAR(500), 
	fecha_factura DATE NOT NULL, 
	plazo_dias INTEGER NOT NULL, 
	fecha_vencimiento DATE NOT NULL, 
	fecha_pago DATE, 
	valor_neto NUMERIC(14, 2) NOT NULL, 
	valor_cancelado NUMERIC(14, 2) NOT NULL, 
	retencion NUMERIC(14, 2) NOT NULL, 
	creado_en TIMESTAMP WITHOUT TIME ZONE, 
	porcentaje_iva NUMERIC(14, 2) NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE contratistas (
	id SERIAL NOT NULL, 
	nombre VARCHAR(200) NOT NULL, 
	nit VARCHAR(50), 
	telefono VARCHAR(50), 
	fecha_registro TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id)
);

CREATE TABLE cotizaciones (
	id SERIAL NOT NULL, 
	cliente VARCHAR(150) NOT NULL, 
	proyecto VARCHAR(150) NOT NULL, 
	numero_cotizacion VARCHAR(50) NOT NULL, 
	estado estado_cotizacion_enum NOT NULL, 
	imagen_cotizacion TEXT, 
	PRIMARY KEY (id), 
	UNIQUE (numero_cotizacion)
);

CREATE TABLE inventario_bodega (
	id_ib SERIAL NOT NULL, 
	nombre_item VARCHAR(150) NOT NULL, 
	unidad VARCHAR(20) NOT NULL, 
	stock_actual INTEGER NOT NULL, 
	stock_minimo INTEGER NOT NULL, 
	PRIMARY KEY (id_ib)
);

CREATE TABLE materiales (
	id_material SERIAL NOT NULL, 
	nombre VARCHAR(100) NOT NULL, 
	unidad VARCHAR(20) NOT NULL, 
	PRIMARY KEY (id_material)
);

CREATE TABLE personal (
	id SERIAL NOT NULL, 
	nombre VARCHAR(100) NOT NULL, 
	rol rol_personal_enum NOT NULL, 
	rol_personalizado VARCHAR(100), 
	activo BOOLEAN, 
	costo_diario NUMERIC(10, 2) NOT NULL, 
	contacto VARCHAR(50), 
	PRIMARY KEY (id), 
	UNIQUE (contacto)
);

CREATE TABLE proveedor_facturas (
	id SERIAL NOT NULL, 
	nombre_proveedor VARCHAR(200) NOT NULL, 
	orden_compra_url VARCHAR(500), 
	comprobante_compra_url VARCHAR(500), 
	banco_pago_url VARCHAR(500), 
	fecha_factura DATE NOT NULL, 
	plazo_dias INTEGER NOT NULL, 
	fecha_vencimiento DATE NOT NULL, 
	fecha_pago DATE, 
	valor_neto NUMERIC(14, 2) NOT NULL, 
	valor_cancelado NUMERIC(14, 2) NOT NULL, 
	retencion NUMERIC(14, 2) NOT NULL, 
	creado_en TIMESTAMP WITHOUT TIME ZONE, 
	porcentaje_iva NUMERIC(14, 2) NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE proveedores (
	id SERIAL NOT NULL, 
	nombre VARCHAR(200) NOT NULL, 
	nit VARCHAR(50), 
	telefono VARCHAR(50), 
	fecha_registro TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id)
);

CREATE TABLE contratos (
	id SERIAL NOT NULL, 
	cotizacion_id INTEGER, 
	cliente VARCHAR(150) NOT NULL, 
	proyecto VARCHAR(150) NOT NULL, 
	estado estado_contrato_enum NOT NULL, 
	valor_total NUMERIC(12, 2) NOT NULL, 
	anticipo_porcentaje NUMERIC(5, 2), 
	valor_anticipo NUMERIC(12, 2), 
	retencion_garantia_porcentaje NUMERIC(5, 2), 
	total_sin_iva NUMERIC(12, 2), 
	cliente_id INTEGER, 
	PRIMARY KEY (id), 
	UNIQUE (cotizacion_id), 
	FOREIGN KEY(cotizacion_id) REFERENCES cotizaciones (id) ON DELETE CASCADE, 
	FOREIGN KEY(cliente_id) REFERENCES clientes (id) ON DELETE SET NULL
);

CREATE TABLE contratos_clientes (
	id SERIAL NOT NULL, 
	cliente_id INTEGER NOT NULL, 
	nombre_proyecto VARCHAR(255) NOT NULL, 
	valor_total NUMERIC(15, 2) NOT NULL, 
	porcentaje_retegarantia NUMERIC(5, 2), 
	archivo_pdf TEXT, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(cliente_id) REFERENCES clientes (id) ON DELETE CASCADE
);

CREATE TABLE historial_materiales (
	id SERIAL NOT NULL, 
	nombre_proyecto_eliminado VARCHAR(150) NOT NULL, 
	id_material INTEGER NOT NULL, 
	nombre_material VARCHAR(100) NOT NULL, 
	unidad_material VARCHAR(20) NOT NULL, 
	cantidad INTEGER NOT NULL, 
	fecha_registro DATE, 
	motivo VARCHAR(200), 
	PRIMARY KEY (id), 
	FOREIGN KEY(id_material) REFERENCES materiales (id_material)
);

CREATE TABLE proyectos (
	id_proyecto SERIAL NOT NULL, 
	nombre VARCHAR(150) NOT NULL, 
	lugar VARCHAR(150) NOT NULL, 
	responsable_id INTEGER, 
	descripcion TEXT, 
	fecha_inicio DATE NOT NULL, 
	fecha_fin DATE NOT NULL, 
	estado estado_proyecto_enum, 
	fecha_fin_real DATE, 
	visible BOOLEAN, 
	PRIMARY KEY (id_proyecto), 
	FOREIGN KEY(responsable_id) REFERENCES personal (id) ON DELETE SET NULL ON UPDATE CASCADE
);

CREATE TABLE usuarios (
	id_usuario SERIAL NOT NULL, 
	nombre VARCHAR(100) NOT NULL, 
	email VARCHAR(100) NOT NULL, 
	password VARCHAR(255) NOT NULL, 
	rol rol_usuario_enum NOT NULL, 
	foto_perfil VARCHAR(200), 
	debe_cambiar_contrasena BOOLEAN, 
	reset_token VARCHAR(100), 
	personal_id INTEGER, 
	PRIMARY KEY (id_usuario), 
	FOREIGN KEY(personal_id) REFERENCES personal (id) ON DELETE SET NULL
);

CREATE TABLE asignacion_diaria (
	id SERIAL NOT NULL, 
	fecha DATE NOT NULL, 
	proyecto_id INTEGER NOT NULL, 
	personal_id INTEGER NOT NULL, 
	hora_entrada TIME WITHOUT TIME ZONE NOT NULL, 
	observacion TEXT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(proyecto_id) REFERENCES proyectos (id_proyecto), 
	FOREIGN KEY(personal_id) REFERENCES personal (id)
);

CREATE TABLE asistencia (
	id SERIAL NOT NULL, 
	personal_id INTEGER, 
	proyecto_id INTEGER NOT NULL, 
	fecha DATE NOT NULL, 
	trabajo_manana BOOLEAN, 
	trabajo_tarde BOOLEAN, 
	horas_trabajadas INTEGER, 
	motivo VARCHAR(200), 
	nombre_proyecto_eliminado VARCHAR(150), 
	PRIMARY KEY (id), 
	FOREIGN KEY(personal_id) REFERENCES personal (id) ON DELETE SET NULL, 
	FOREIGN KEY(proyecto_id) REFERENCES proyectos (id_proyecto) ON DELETE CASCADE
);

CREATE TABLE horarios (
	id SERIAL NOT NULL, 
	personal_id INTEGER NOT NULL, 
	proyecto_id INTEGER NOT NULL, 
	fecha DATE NOT NULL, 
	hora_entrada TIME WITHOUT TIME ZONE NOT NULL, 
	observacion VARCHAR(200), 
	PRIMARY KEY (id), 
	FOREIGN KEY(personal_id) REFERENCES personal (id) ON DELETE CASCADE, 
	FOREIGN KEY(proyecto_id) REFERENCES proyectos (id_proyecto) ON DELETE CASCADE
);

CREATE TABLE materiales_proyecto (
	id_mp SERIAL NOT NULL, 
	id_material INTEGER NOT NULL, 
	id_proyecto INTEGER NOT NULL, 
	cantidad INTEGER NOT NULL, 
	estado estado_material_enum, 
	fecha_entrega DATE, 
	usado_en TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id_mp), 
	FOREIGN KEY(id_material) REFERENCES materiales (id_material), 
	FOREIGN KEY(id_proyecto) REFERENCES proyectos (id_proyecto)
);

CREATE TABLE movimientos (
	id SERIAL NOT NULL, 
	contrato_id INTEGER, 
	banco VARCHAR(100), 
	tipo tipo_movimiento_enum NOT NULL, 
	categoria categoria_movimiento_enum NOT NULL, 
	valor_bruto NUMERIC(12, 2) NOT NULL, 
	amortizacion_anticipo NUMERIC(12, 2), 
	retencion_garantia NUMERIC(12, 2), 
	valor_neto NUMERIC(12, 2) NOT NULL, 
	fecha_movimiento DATE NOT NULL, 
	numero_documento VARCHAR(100), 
	archivo_soporte VARCHAR(255), 
	creado_en TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(contrato_id) REFERENCES contratos (id) ON DELETE CASCADE
);

CREATE TABLE proyecto_personal (
	id SERIAL NOT NULL, 
	proyecto_id INTEGER NOT NULL, 
	personal_id INTEGER, 
	PRIMARY KEY (id), 
	FOREIGN KEY(proyecto_id) REFERENCES proyectos (id_proyecto) ON DELETE CASCADE, 
	FOREIGN KEY(personal_id) REFERENCES personal (id) ON DELETE CASCADE
);

CREATE TABLE reporte_clientes (
	id SERIAL NOT NULL, 
	contrato_cliente_id INTEGER NOT NULL, 
	actas_pdf_url TEXT, 
	valor_factura NUMERIC(15, 2) NOT NULL, 
	fecha_factura DATE, 
	factura_pdf_url TEXT, 
	porcentaje_rete_garantia NUMERIC(5, 2), 
	retencion_ley NUMERIC(15, 2), 
	pago_realizado NUMERIC(15, 2), 
	fecha_pago DATE, 
	comprobante_pago_url TEXT, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(contrato_cliente_id) REFERENCES contratos_clientes (id) ON DELETE CASCADE
);

CREATE TABLE requisiciones_oficina (
	id SERIAL NOT NULL, 
	bodeguero_id INTEGER NOT NULL, 
	fecha_solicitud TIMESTAMP WITHOUT TIME ZONE, 
	estado estado_req_oficina_enum, 
	observaciones TEXT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(bodeguero_id) REFERENCES usuarios (id_usuario)
);

CREATE TABLE solicitudes_materiales (
	id_solicitud SERIAL NOT NULL, 
	id_proyecto INTEGER NOT NULL, 
	id_usuario_solicitante INTEGER NOT NULL, 
	id_usuario_responsable INTEGER, 
	fecha_solicitud DATE, 
	fecha_actualizacion DATE, 
	estado estado_solicitud_enum, 
	observaciones TEXT, 
	archivo_ruta VARCHAR(255), 
	visible_para_trabajador BOOLEAN NOT NULL, 
	visible_para_bodega BOOLEAN, 
	nombre_proyecto_eliminado VARCHAR(150), 
	fecha_entrega_estimada DATE, 
	observacion_bodega TEXT, 
	PRIMARY KEY (id_solicitud), 
	FOREIGN KEY(id_proyecto) REFERENCES proyectos (id_proyecto), 
	FOREIGN KEY(id_usuario_solicitante) REFERENCES usuarios (id_usuario), 
	FOREIGN KEY(id_usuario_responsable) REFERENCES usuarios (id_usuario)
);

CREATE TABLE sub_proyectos (
	id SERIAL NOT NULL, 
	proyecto_id INTEGER NOT NULL, 
	nombre_miniproyecto VARCHAR(100) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(proyecto_id) REFERENCES proyectos (id_proyecto) ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE vehiculos (
	id_vehiculo SERIAL NOT NULL, 
	placa VARCHAR(20) NOT NULL, 
	marca VARCHAR(100) NOT NULL, 
	modelo VARCHAR(100) NOT NULL, 
	documentos_al_dia BOOLEAN, 
	soat_vencimiento DATE NOT NULL, 
	tecno_vencimiento DATE NOT NULL, 
	estado estado_vehiculo_enum, 
	updated_at TIMESTAMP WITHOUT TIME ZONE, 
	proyecto_actual_id INTEGER, 
	ubicacion_actual VARCHAR(100), 
	PRIMARY KEY (id_vehiculo), 
	UNIQUE (placa), 
	FOREIGN KEY(proyecto_actual_id) REFERENCES proyectos (id_proyecto)
);

CREATE TABLE actividades (
	id_actividad SERIAL NOT NULL, 
	id_proyecto INTEGER NOT NULL, 
	sub_proyecto_id INTEGER, 
	nombre VARCHAR(150) NOT NULL, 
	descripcion TEXT, 
	unidades_totales INTEGER, 
	PRIMARY KEY (id_actividad), 
	FOREIGN KEY(id_proyecto) REFERENCES proyectos (id_proyecto) ON DELETE CASCADE, 
	FOREIGN KEY(sub_proyecto_id) REFERENCES sub_proyectos (id) ON DELETE SET NULL
);

CREATE TABLE detalle_requisicion_oficina (
	id SERIAL NOT NULL, 
	requisicion_id INTEGER NOT NULL, 
	material_texto VARCHAR(255) NOT NULL, 
	cantidad VARCHAR(100) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(requisicion_id) REFERENCES requisiciones_oficina (id)
);

CREATE TABLE detalle_solicitud_material (
	id SERIAL NOT NULL, 
	id_solicitud INTEGER NOT NULL, 
	id_material INTEGER, 
	nombre_material_escrito VARCHAR(255), 
	cantidad INTEGER NOT NULL, 
	cantidad_entregada INTEGER, 
	PRIMARY KEY (id), 
	FOREIGN KEY(id_solicitud) REFERENCES solicitudes_materiales (id_solicitud) ON DELETE CASCADE, 
	FOREIGN KEY(id_material) REFERENCES materiales (id_material)
);

CREATE TABLE mantenimiento_vehiculo (
	id SERIAL NOT NULL, 
	vehiculo_id INTEGER NOT NULL, 
	fecha DATE NOT NULL, 
	tipo VARCHAR(100), 
	observaciones TEXT, 
	proximo DATE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(vehiculo_id) REFERENCES vehiculos (id_vehiculo) ON DELETE CASCADE
);

CREATE TABLE movimiento_vehiculo (
	id_movimiento SERIAL NOT NULL, 
	id_vehiculo INTEGER NOT NULL, 
	id_usuario INTEGER, 
	fecha_hora TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	proyecto_anterior_id INTEGER, 
	proyecto_nuevo_id INTEGER, 
	ubicacion_anterior VARCHAR(100), 
	ubicacion_nueva VARCHAR(100), 
	motivo TEXT, 
	PRIMARY KEY (id_movimiento), 
	FOREIGN KEY(id_vehiculo) REFERENCES vehiculos (id_vehiculo) ON DELETE CASCADE, 
	FOREIGN KEY(id_usuario) REFERENCES usuarios (id_usuario) ON DELETE SET NULL, 
	FOREIGN KEY(proyecto_anterior_id) REFERENCES proyectos (id_proyecto), 
	FOREIGN KEY(proyecto_nuevo_id) REFERENCES proyectos (id_proyecto)
);

CREATE TABLE notificaciones (
	id_notificacion SERIAL NOT NULL, 
	id_usuario_destino INTEGER NOT NULL, 
	mensaje TEXT NOT NULL, 
	leido BOOLEAN, 
	creado_en TIMESTAMP WITHOUT TIME ZONE, 
	id_horario INTEGER, 
	PRIMARY KEY (id_notificacion), 
	FOREIGN KEY(id_usuario_destino) REFERENCES usuarios (id_usuario), 
	FOREIGN KEY(id_horario) REFERENCES horarios (id) ON DELETE CASCADE
);

CREATE TABLE vehiculo_proyecto (
	id_vp SERIAL NOT NULL, 
	id_vehiculo INTEGER NOT NULL, 
	id_proyecto INTEGER NOT NULL, 
	fecha DATE, 
	hora TIME WITHOUT TIME ZONE, 
	observacion TEXT, 
	nombre_proyecto_eliminado VARCHAR(150), 
	PRIMARY KEY (id_vp), 
	FOREIGN KEY(id_vehiculo) REFERENCES vehiculos (id_vehiculo), 
	FOREIGN KEY(id_proyecto) REFERENCES proyectos (id_proyecto)
);

CREATE TABLE avances (
	id_avance SERIAL NOT NULL, 
	id_actividad INTEGER NOT NULL, 
	id_usuario INTEGER, 
	fecha DATE, 
	unidades_avanzadas INTEGER, 
	mensaje TEXT, 
	trayecto VARCHAR(100), 
	calzada VARCHAR(100), 
	carril VARCHAR(100), 
	ubicacion_pr VARCHAR(100), 
	tipo VARCHAR(100), 
	elemento VARCHAR(100), 
	area_elemento FLOAT, 
	area_total FLOAT, 
	PRIMARY KEY (id_avance), 
	FOREIGN KEY(id_actividad) REFERENCES actividades (id_actividad) ON DELETE CASCADE, 
	FOREIGN KEY(id_usuario) REFERENCES usuarios (id_usuario) ON DELETE SET NULL
);

CREATE TABLE avance_material (
	id SERIAL NOT NULL, 
	id_avance INTEGER NOT NULL, 
	id_material INTEGER NOT NULL, 
	cantidad_usada FLOAT NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(id_avance) REFERENCES avances (id_avance) ON DELETE CASCADE, 
	FOREIGN KEY(id_material) REFERENCES materiales (id_material)
);

CREATE TABLE evidencias (
	id_evidencia SERIAL NOT NULL, 
	id_avance INTEGER NOT NULL, 
	ruta_archivo VARCHAR(255) NOT NULL, 
	tipo VARCHAR(50) NOT NULL, 
	subido_en TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id_evidencia), 
	FOREIGN KEY(id_avance) REFERENCES avances (id_avance) ON DELETE CASCADE
);

