from flask import Blueprint, render_template

egreso_caja_bp = Blueprint('egreso_caja', __name__, url_prefix='/egreso_caja')

@egreso_caja_bp.route('/', methods=['GET'])
def index():
    return render_template('egreso_caja.html')
