from flask import Blueprint, render_template, request, redirect, url_for, flash
from datetime import date as d
from models import db, Asistencia, Proyectos, Personal, ProyectoPersonal
import traceback

asistencia_bp = Blueprint("asistencia", __name__)


# ------------------------------
# 🔧 Función auxiliar
# ------------------------------
def hoy_ymd() -> str:
    """Devuelve la fecha actual en formato YYYY-MM-DD"""
    return d.today().isoformat()


# =======================================================
# (1) Página general de asistencia
# =======================================================
@asistencia_bp.route("/asistencia", methods=["GET", "POST"])
def manage_asistencia():
    print(f"\n🟢 [DEBUG] {request.method} manage_asistencia")

    fecha_str = request.args.get("fecha") or hoy_ymd()
    fecha_dt = d.fromisoformat(fecha_str)

    proyectos = Proyectos.query.order_by(Proyectos.nombre.asc()).all()
    personal = Personal.query.order_by(Personal.nombre.asc()).all()

    if request.method == "POST":
        try:
            for p in personal:
                trabajo_manana = request.form.get(f"trabajo_manana_{p.id}") == "on"
                trabajo_tarde = request.form.get(f"trabajo_tarde_{p.id}") == "on"
                horas_m = request.form.get(f"horas_manana_{p.id}")
                horas_t = request.form.get(f"horas_tarde_{p.id}")
                horas_totales = (
                    (int(horas_m) if horas_m and horas_m.isdigit() else 0)
                    + (int(horas_t) if horas_t and horas_t.isdigit() else 0)
                )
                motivo = request.form.get(f"motivo_{p.id}")
                proyecto_id = request.form.get(f"proyecto_{p.id}")

                fila = Asistencia.query.filter_by(personal_id=p.id, fecha=fecha_dt).first()
                if fila:
                    fila.trabajo_manana = trabajo_manana
                    fila.trabajo_tarde = trabajo_tarde
                    fila.horas_trabajadas = horas_totales
                    fila.motivo = motivo
                    fila.proyecto_id = proyecto_id
                else:
                    nueva = Asistencia(
                        personal_id=p.id,
                        proyecto_id=proyecto_id,
                        fecha=fecha_dt,
                        trabajo_manana=trabajo_manana,
                        trabajo_tarde=trabajo_tarde,
                        horas_trabajadas=horas_totales,
                        motivo=motivo,
                    )
                    db.session.add(nueva)
            db.session.commit()
            flash("✅ Asistencia registrada correctamente", "success")

        except Exception as e:
            db.session.rollback()
            print(traceback.format_exc())
            flash(f"❌ Error al registrar asistencia: {e}", "danger")

        return redirect(url_for("asistencia.manage_asistencia", fecha=fecha_dt.isoformat()))

    asistencias = Asistencia.query.filter_by(fecha=fecha_dt).all()
    asistencia_dict = {
        a.personal_id: {
            "trabajo_manana": a.trabajo_manana,
            "trabajo_tarde": a.trabajo_tarde,
            "horas_trabajadas": a.horas_trabajadas,
            "motivo": a.motivo or "",
            "proyecto_id": a.proyecto_id,
        }
        for a in asistencias
    }

    return render_template(
        "asistencia.html",
        proyectos=proyectos,
        personal=personal,
        fecha_str=fecha_str,
        asistencia_registrada=asistencia_dict,
    )


# =======================================================
# (2) Asistencia filtrada por proyecto
# =======================================================
@asistencia_bp.route("/proyectos/<int:proyecto_id>/asistencia", methods=["GET", "POST"])
def asistencia_proyecto(proyecto_id):
    print(f"\n🟣 [DEBUG] asistencia_proyecto proyecto_id={proyecto_id}")

    proyecto = Proyectos.query.get_or_404(proyecto_id)
    fecha_str = request.args.get("fecha") or hoy_ymd()
    fecha_dt = d.fromisoformat(fecha_str)

    personal_asignado = (
        Personal.query.join(ProyectoPersonal)
        .filter(ProyectoPersonal.proyecto_id == proyecto_id)
        .order_by(Personal.nombre.asc())
        .all()
    )

    if request.method == "POST":
        try:
            for p in personal_asignado:
                trabajo_manana = request.form.get(f"trabajo_manana_{p.id}") == "on"
                trabajo_tarde = request.form.get(f"trabajo_tarde_{p.id}") == "on"
                horas_m = request.form.get(f"horas_manana_{p.id}")
                horas_t = request.form.get(f"horas_tarde_{p.id}")
                horas_totales = (
                    (int(horas_m) if horas_m and horas_m.isdigit() else 0)
                    + (int(horas_t) if horas_t and horas_t.isdigit() else 0)
                )
                motivo = request.form.get(f"motivo_{p.id}")

                fila = Asistencia.query.filter_by(personal_id=p.id, fecha=fecha_dt).first()
                if fila:
                    fila.trabajo_manana = trabajo_manana
                    fila.trabajo_tarde = trabajo_tarde
                    fila.horas_trabajadas = horas_totales
                    fila.motivo = motivo
                else:
                    nueva = Asistencia(
                        personal_id=p.id,
                        proyecto_id=proyecto_id,
                        fecha=fecha_dt,
                        trabajo_manana=trabajo_manana,
                        trabajo_tarde=trabajo_tarde,
                        horas_trabajadas=horas_totales,
                        motivo=motivo,
                    )
                    db.session.add(nueva)
            db.session.commit()
            flash("✅ Asistencia por proyecto registrada correctamente", "success")

        except Exception as e:
            db.session.rollback()
            print(traceback.format_exc())
            flash(f"❌ Error al registrar asistencia: {e}", "danger")

        return redirect(
            url_for("asistencia.asistencia_proyecto", proyecto_id=proyecto_id, fecha=fecha_dt.isoformat())
        )

    asistencias = Asistencia.query.filter_by(proyecto_id=proyecto_id, fecha=fecha_dt).all()
    asistencia_dict = {
        a.personal_id: {
            "trabajo_manana": a.trabajo_manana,
            "trabajo_tarde": a.trabajo_tarde,
            "horas_trabajadas": a.horas_trabajadas,
            "motivo": a.motivo or "",
        }
        for a in asistencias
    }

    return render_template(
        "asistencia_proyecto.html",
        proyecto=proyecto,
        personal_asignado=personal_asignado,
        fecha_str=fecha_str,
        asistencia_registrada=asistencia_dict,
    )


# =======================================================
# (3) 🧍‍♂️ Asistencia individual por trabajador
# =======================================================
@asistencia_bp.route("/personal/<int:personal_id>/asistencia", methods=["GET", "POST"])
@asistencia_bp.route("/personal/<int:personal_id>/registrar_asistencia", methods=["GET", "POST"])
def asistencia_trabajador(personal_id):
    """Registrar o consultar asistencia de un trabajador individual"""
    print(f"\n🟡 [DEBUG] {request.method} asistencia_trabajador personal_id={personal_id}")

    fecha_str = request.args.get("fecha") or hoy_ymd()
    fecha_dt = d.fromisoformat(fecha_str)

    trabajador = Personal.query.get_or_404(personal_id)

    # 🆕 Solo proyectos en los que está asignado el trabajador
    proyectos_asignados = (
        Proyectos.query
        .join(ProyectoPersonal)
        .filter(ProyectoPersonal.personal_id == personal_id)
        .order_by(Proyectos.nombre.asc())
        .all()
    )

    if request.method == "POST":
        try:
            proyecto_id = request.form.get("proyecto_id")
            proyecto_id = int(proyecto_id) if proyecto_id else None

            trabajo_manana = "trabajo_manana" in request.form
            trabajo_tarde = "trabajo_tarde" in request.form

            horas_m = request.form.get("horas_manana")
            horas_t = request.form.get("horas_tarde")
            horas_totales = (
                (int(horas_m) if horas_m and horas_m.isdigit() else 0)
                + (int(horas_t) if horas_t and horas_t.isdigit() else 0)
            )

            motivo = request.form.get("motivo")

            fila = Asistencia.query.filter_by(personal_id=personal_id, fecha=fecha_dt).first()

            if fila:
                fila.proyecto_id = proyecto_id
                fila.trabajo_manana = trabajo_manana
                fila.trabajo_tarde = trabajo_tarde
                fila.horas_trabajadas = horas_totales
                fila.motivo = motivo
            else:
                db.session.add(
                    Asistencia(
                        personal_id=personal_id,
                        proyecto_id=proyecto_id,
                        fecha=fecha_dt,
                        trabajo_manana=trabajo_manana,
                        trabajo_tarde=trabajo_tarde,
                        horas_trabajadas=horas_totales,
                        motivo=motivo,
                    )
                )

            db.session.commit()
            flash("✅ Asistencia del trabajador registrada correctamente", "success")

        except Exception as e:
            db.session.rollback()
            print("❌ Error en asistencia_trabajador POST")
            print(traceback.format_exc())
            flash(f"❌ Error al guardar asistencia: {e}", "danger")

        return redirect(url_for("asistencia.asistencia_trabajador", personal_id=personal_id, fecha=fecha_dt.isoformat()))

    # Últimas asistencias del trabajador
    asistencias = (
        Asistencia.query.filter_by(personal_id=personal_id)
        .order_by(Asistencia.fecha.desc())
        .limit(7)
        .all()
    )

    asistencia_registrada = {
        a.fecha.isoformat(): {
            "manana": a.trabajo_manana,
            "tarde": a.trabajo_tarde,
            "horas_trabajadas": a.horas_trabajadas,
            "motivo": a.motivo or "",
            "proyecto_id": a.proyecto_id,
        }
        for a in asistencias
    }

    return render_template(
        "asistencia_trabajador.html",
        trabajador=trabajador,
        proyectos=proyectos_asignados,
        fecha_str=fecha_str,
        asistencia_registrada=asistencia_registrada,
    )
