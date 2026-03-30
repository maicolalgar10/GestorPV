# frases_motivacionales.py
import random
from datetime import datetime

#  Diccionario de frases clasificadas por tipo
FRASES = {
    "general": [
        "Cada día es una nueva oportunidad para dar lo mejor de ti 💪",
        "El éxito es la suma de pequeños esfuerzos repetidos día tras día.",
        "Hazlo con pasión o no lo hagas.",
        "Cree en ti, incluso cuando nadie más lo haga.",
        "Tu actitud determina tu altitud 🚀",
        "No cuentes los días, haz que los días cuenten.",
        "El trabajo duro supera al talento cuando el talento no trabaja duro.",
        "Tu actitud determina tu altitud, ¡y aquí volamos alto como el cóndor! 🚀",  # Colombiano
        "Es mejor madrugar a trabajar que madrugar a buscar trabajo. "
    ],

    "avance": [
        "Excelente trabajo, estás dejando huella 👷‍♂️",
        "¡Gran avance! El esfuerzo de hoy será tu recompensa mañana.",
        "Cada paso te acerca más a la meta. Sigue así 💪",
        "La disciplina vence a la motivación. ¡Buen ritmo!",
        "Tu compromiso marca la diferencia, sigue adelante 🔥",
    ],

    "admin": [
        "Un buen líder inspira confianza, no miedo 👑",
        "La gestión efectiva empieza con escuchar.",
        "Coordinar bien a tu equipo es el primer paso hacia el éxito.",
        "Cada decisión que tomas construye el futuro de tu equipo.",
        "Liderar es servir, no mandar.",
    ]
}


# 🎲 Función principal: obtener una frase aleatoria según el contexto
def obtener_frase(tipo="general"):
    frases = FRASES.get(tipo, FRASES["general"])
    return random.choice(frases)


# 🌅 (Opcional) Frase del día, siempre igual por día calendario
def frase_del_dia():
    hoy = datetime.now().strftime("%Y-%m-%d")
    random.seed(hoy)  # misma frase cada día
    return obtener_frase()
