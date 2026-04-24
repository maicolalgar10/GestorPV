from app import create_app
from models import db
from sqlalchemy import text

app = create_app()

with app.app_context():
    print("=" * 55)
    print("  MIGRACIÓN A PRODUCCIÓN — CorseING")
    print("=" * 55)

    errores = []

    # ─────────────────────────────────────────────────────────
    # PASO 0: Verificar qué tablas existen actualmente
    # ─────────────────────────────────────────────────────────
    print("\n[0/5] Inspeccionando la base de datos de producción...")
    try:
        tablas_existentes = db.session.execute(text(
            """
            SELECT tablename FROM pg_tables
            WHERE schemaname = 'public'
            ORDER BY tablename;
            """
        )).fetchall()
        nombres = [t[0] for t in tablas_existentes]
        if nombres:
            print(f"      Tablas encontradas ({len(nombres)}): {', '.join(nombres)}")
        else:
            print("      ⚠️  Base de datos vacía — se crearán todas las tablas.")
    except Exception as e:
        print(f"      ❌  No se pudo inspeccionar: {e}")
        nombres = []

    # ─────────────────────────────────────────────────────────
    # PASO 1: Crear todas las tablas que no existan
    # ─────────────────────────────────────────────────────────
    print("\n[1/5] Creando tablas faltantes con db.create_all()...")
    try:
        db.create_all()
        print("      ✅  Tablas creadas / verificadas correctamente.")
    except Exception as e:
        msg = f"      ❌  Error en create_all: {e}"
        print(msg)
        errores.append(msg)

    # ─────────────────────────────────────────────────────────
    # PASO 2: ENUM — añadir 'saldo_inicial' si no existe
    # ─────────────────────────────────────────────────────────
    print("\n[2/5] Verificando ENUM categoria_movimiento_enum...")
    try:
        # Primero chequeamos si el valor ya existe
        existe_enum = db.session.execute(text(
            """
            SELECT 1 FROM pg_enum
            JOIN pg_type ON pg_enum.enumtypid = pg_type.oid
            WHERE pg_type.typname = 'categoria_movimiento_enum'
              AND pg_enum.enumlabel = 'saldo_inicial';
            """
        )).fetchone()

        if existe_enum:
            print("      ✅  Valor 'saldo_inicial' ya existe en el ENUM.")
        else:
            db.session.execute(text(
                "ALTER TYPE categoria_movimiento_enum ADD VALUE IF NOT EXISTS 'saldo_inicial';"
            ))
            db.session.commit()
            print("      ✅  Valor 'saldo_inicial' añadido al ENUM.")
    except Exception as e:
        db.session.rollback()
        msg = f"      ❌  Error en ENUM: {e}"
        print(msg)
        errores.append(msg)

    # ─────────────────────────────────────────────────────────
    # PASO 3: BANCOS — columna 'color'
    # ─────────────────────────────────────────────────────────
    print("\n[3/5] Verificando columna 'color' en tabla bancos...")
    try:
        db.session.execute(text(
            "ALTER TABLE bancos ADD COLUMN IF NOT EXISTS color VARCHAR(7) DEFAULT '#004481';"
        ))
        db.session.commit()
        print("      ✅  Columna 'color' en bancos OK.")
    except Exception as e:
        db.session.rollback()
        msg = f"      ❌  Error en bancos.color: {e}"
        print(msg)
        errores.append(msg)

    # ─────────────────────────────────────────────────────────
    # PASO 4: CONTRATOS — columnas de anticipo y retención
    # ─────────────────────────────────────────────────────────
    print("\n[4/5] Verificando columnas en tabla contratos...")
    try:
        db.session.execute(text(
            "ALTER TABLE contratos ADD COLUMN IF NOT EXISTS anticipo_porcentaje FLOAT DEFAULT 0;"
        ))
        db.session.commit()
        print("      ✅  Columna 'anticipo_porcentaje' en contratos OK.")
    except Exception as e:
        db.session.rollback()
        msg = f"      ❌  Error en contratos.anticipo_porcentaje: {e}"
        print(msg)
        errores.append(msg)

    try:
        db.session.execute(text(
            "ALTER TABLE contratos ADD COLUMN IF NOT EXISTS retencion_garantia_porcentaje FLOAT DEFAULT 0;"
        ))
        db.session.commit()
        print("      ✅  Columna 'retencion_garantia_porcentaje' en contratos OK.")
    except Exception as e:
        db.session.rollback()
        msg = f"      ❌  Error en contratos.retencion_garantia_porcentaje: {e}"
        print(msg)
        errores.append(msg)

    # ─────────────────────────────────────────────────────────
    # PASO 5: VERIFICACIÓN FINAL
    # ─────────────────────────────────────────────────────────
    print("\n[5/5] Verificación final del esquema en producción...")
    try:
        # Columnas de bancos
        cols_bancos = db.session.execute(text(
            """
            SELECT column_name, data_type, column_default
            FROM information_schema.columns
            WHERE table_name = 'bancos'
            ORDER BY ordinal_position;
            """
        )).fetchall()
        print("\n  Tabla BANCOS:")
        for col in cols_bancos:
            print(f"     • {col[0]:35s} {col[1]:15s} default={col[2]}")

        # Columnas de contratos
        cols_contratos = db.session.execute(text(
            """
            SELECT column_name, data_type, column_default
            FROM information_schema.columns
            WHERE table_name = 'contratos'
            ORDER BY ordinal_position;
            """
        )).fetchall()
        print("\n  Tabla CONTRATOS:")
        for col in cols_contratos:
            print(f"     • {col[0]:35s} {col[1]:15s} default={col[2]}")

        # Valores del ENUM
        vals_enum = db.session.execute(text(
            """
            SELECT enumlabel
            FROM pg_enum
            JOIN pg_type ON pg_enum.enumtypid = pg_type.oid
            WHERE pg_type.typname = 'categoria_movimiento_enum'
            ORDER BY enumsortorder;
            """
        )).fetchall()
        print(f"\n  ENUM categoria_movimiento_enum: {[v[0] for v in vals_enum]}")

        # Conteo de registros
        total_bancos     = db.session.execute(text("SELECT COUNT(*) FROM bancos;")).scalar()
        total_contratos  = db.session.execute(text("SELECT COUNT(*) FROM contratos;")).scalar()
        total_movimientios = db.session.execute(text("SELECT COUNT(*) FROM movimientos;")).scalar()
        total_proyectos  = db.session.execute(text("SELECT COUNT(*) FROM proyectos;")).scalar()
        print(f"\n  Conteo de registros:")
        print(f"     • bancos:      {total_bancos}")
        print(f"     • contratos:   {total_contratos}")
        print(f"     • movimientos: {total_movimientios}")
        print(f"     • proyectos:   {total_proyectos}")

    except Exception as e:
        msg = f"      ❌  Error en verificación: {e}"
        print(msg)
        errores.append(msg)

    # ─────────────────────────────────────────────────────────
    # RESUMEN
    # ─────────────────────────────────────────────────────────
    print("\n" + "=" * 55)
    if errores:
        print(f"  MIGRACION COMPLETADA CON {len(errores)} ERROR(ES):")
        for err in errores:
            print(f"  {err}")
    else:
        print("  MIGRACION COMPLETADA EXITOSAMENTE — Sin errores.")
    print("=" * 55 + "\n")
