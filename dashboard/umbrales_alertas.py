"""
dashboard/umbrales_alertas.py  -  umbrales de las alertas del simulador integral (18-nov-2026)
Los usan la pagina /simulador (para que salten) y la pagina /alertas (para listarlas), asi las dos dicen siempre lo mismo.
"""
# Alertas del simulador. Hay dos gravedades: AVISO (media) y CRITICO (alta). Las dos frenan la simulacion, pero cada alerta (tipo y gravedad) se muestra UNA SOLA VEZ por corrida.
# Como cada alerta se muestra una sola vez por corrida, una condicion que dura casi todo el tiempo (superar las 106 camas es lo normal en esta simulacion: la probabilidad
# tiene mediana 68 %) avisa una vez y no vuelve a molestar; lo critico esta por encima de lo tipico (en un caso normal de 90 dias:
# probabilidad casi nunca mayor de 84 %, camas ocupadas mediana 111 y p90 114,5, cola mediana 25 y p99 28). Criterios de esta pagina, no cifras validadas.
# "Faltaran camas" (18-nov): una sola alerta para lo que antes eran dos (riesgo de saturar y ocupacion alta), porque las dos decian lo mismo: se necesitaran mas de las 106 camas.
# Dice CUANDO (probabilidad de superar la capacidad a 48 h) y CUANTO (camas que faltan en la mediana de las repeticiones); la gravedad sale de cualquiera de las dos.
UMBRAL_ALERTA_MEDIA = 50                 # faltaran camas: aviso cuando es mas probable que si superar la capacidad a 48 h
UMBRAL_ALERTA = 84                       # faltaran camas: critico por probabilidad (solo se alcanza en los picos de un caso normal)
UMBRAL_FALTAN = 1                        # faltaran camas: aviso si en la mediana falta al menos 1 cama (107 ocupadas contra 106)
UMBRAL_FALTAN_CRITICO = 12               # faltaran camas: critico si faltan 12 o mas (118 ocupadas contra 106)
UMBRAL_COLA = 28                         # cola: aviso (pacientes esperando cama a la vez; lo habitual son ~25)
UMBRAL_COLA_CRITICA = 33                 # cola: critico (el percentil 90 real de la cola es 33)
ARRANQUE_SIN_ALERTAS = 7                 # los primeros dias vienen de la siembra con el censo real y no generan alertas: 7 (4 si el plazo es de 2 semanas o menos, porque la siembra deja las camas por encima de 118 los primeros 3 dias; 12 h en la vista horaria)

