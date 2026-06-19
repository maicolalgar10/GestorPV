-- Tabla principal de Clientes
CREATE TABLE IF NOT EXISTS clientes (
    id SERIAL PRIMARY KEY,
    nombre_cliente VARCHAR(150) NOT NULL,
    nit VARCHAR(50),
    contacto VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

-- Tabla de Reporte/Contratos de Clientes
CREATE TABLE IF NOT EXISTS reporte_clientes (
    id SERIAL PRIMARY KEY,
    cliente_id INTEGER REFERENCES clientes(id) ON DELETE CASCADE,
    
    -- Datos del Contrato
    valor_contrato NUMERIC(15,2) NOT NULL DEFAULT 0.00,
    contrato_pdf_url TEXT,
    actas_pdf_url TEXT, -- Almacena el documento de actas de obra
    
    -- Datos de Facturación actual
    valor_factura NUMERIC(15,2) NOT NULL DEFAULT 0.00,
    factura_pdf_url TEXT,
    
    -- Retenciones y Pagos
    porcentaje_rete_garantia NUMERIC(5,2) DEFAULT 0.00, -- Porcentaje (ej: 10.00 para 10%)
    retencion_ley NUMERIC(15,2) DEFAULT 0.00,
    pago_realizado NUMERIC(15,2) DEFAULT 0.00,
    fecha_pago DATE,
    comprobante_pago_url TEXT, -- PDF o Imagen del pago
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);
