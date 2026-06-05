# decorators.py
from functools import wraps
from flask import session, flash, redirect, url_for

def login_required(f):
    """
    Decorador para proteger rutas que requieren inicio de sesión.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Debes iniciar sesión para acceder a esta página.', 'warning')
            return redirect(url_for('usuarios.login')) # Asegúrate de que 'usuarios.login' sea la ruta correcta de tu login
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """
    Decorador para proteger rutas que requieren rol de ADMIN.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Debes iniciar sesión para acceder a esta página.', 'warning')
            return redirect(url_for('usuarios.login'))

        rol = session.get('rol', 'EMPLEADO') # Asume 'EMPLEADO' como rol por defecto si no está en sesión
        if rol != 'ADMIN':
            flash('Acceso denegado. Requiere rol de Administrador.', 'danger')
            # Opcional: redirigir a una página de error o al dashboard
            return redirect(url_for('dashboard.dashboard')) # O a donde corresponda

        return f(*args, **kwargs)
    return decorated_function

def admin_encargado_required(f):
    """
    Decorador para proteger rutas que requieren rol de ADMIN o ENCARGADO.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash(' Debes iniciar sesión para acceder a esta página.', 'warning')
            return redirect(url_for('usuarios.login'))

        rol = session.get('rol', 'EMPLEADO')
        if rol not in ['ADMIN', 'ENCARGADO']: # Ajusta los roles según tu modelo
            flash(' Acceso denegado. Requiere rol de Administrador o Encargado.', 'danger')
            # Opcional: redirigir a una página de error o al dashboard
            return redirect(url_for('dashboard.dashboard')) # O a donde corresponda

        return f(*args, **kwargs)
    return decorated_function

#  NUEVO: Decorador para Oficina
def admin_oficina_required(f):
    """
    Decorador para proteger rutas que requieren rol de ADMIN o OFICINA.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Debes iniciar sesión para acceder a esta página.', 'warning')
            return redirect(url_for('usuarios.login'))

        rol = session.get('rol', 'EMPLEADO')
        if rol not in ['ADMIN', 'OFICINA', 'ADMINISTRATIVO']:
            flash('Acceso denegado. Requiere rol de Administrador o Administrativo.', 'danger')
            return redirect(url_for('dashboard.dashboard'))

        return f(*args, **kwargs)
    return decorated_function

#  NUEVO: Decorador para Bodega
def admin_bodega_required(f):
    """
    Decorador para proteger rutas que requieren rol de ADMIN o BODEGA.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Debes iniciar sesión para acceder a esta página.', 'warning')
            return redirect(url_for('usuarios.login'))

        rol = session.get('rol', 'EMPLEADO')
        if rol not in ['ADMIN', 'BODEGA']:
            flash('Acceso denegado. Requiere rol de Administrador o Bodega.', 'danger')
            return redirect(url_for('dashboard.dashboard'))

        return f(*args, **kwargs)
    return decorated_function

#  NUEVO: Decorador para Oficina o Bodega
def admin_oficina_bodega_required(f):
    """
    Decorador para proteger rutas que requieren rol de ADMIN, OFICINA o BODEGA.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Debes iniciar sesión para acceder a esta página.', 'warning')
            return redirect(url_for('usuarios.login'))

        rol = session.get('rol', 'EMPLEADO')
        if rol not in ['ADMIN', 'OFICINA', 'BODEGA']:
            flash('Acceso denegado. Requiere rol de Administrador, Oficina o Bodega.', 'danger')
            return redirect(url_for('dashboard.dashboard'))

        return f(*args, **kwargs)
    return decorated_function