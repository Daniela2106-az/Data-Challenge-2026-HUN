"""
dashboard/umbrales_alertas.py  -  umbrales de las alertas del simulador integral (18-nov-2026)
Los usan la pagina /simulador (para que salten) y la pagina /alertas (para listarlas), asi las dos dicen siempre lo mismo.
"""
# Alertas del simulador. Hay dos gravedades: AVISO (media) y CRITICO (alta). Las dos frenan la simulacion. Una alerta salta cuando APARECE (19-nov): si ya estaba activa no vuelve a saltar, y si se va y vuelve a aparecer, salta otra vez.
# Una condicion que dura casi todo el tiempo (superar las 106 camas es lo normal en esta simulacion: la probabilidad
# tiene mediana 68 %) avisa al aparecer y no vuelve a molestar mientras siga; lo critico esta por encima de lo tipico (en un caso normal de 90 dias:
# probabilidad casi nunca mayor de 84 %, camas ocupadas mediana 111 y p90 114,5, cola mediana 25 y p99 28). Criterios de esta pagina, no cifras validadas.
# "Faltaran camas" (18-nov): una sola alerta para lo que antes eran dos (riesgo de saturar y ocupacion alta), porque las dos decian lo mismo: se necesitaran mas de las 106 camas.
# Dice CUANDO (probabilidad de superar la capacidad a 48 h) y CUANTO (camas que faltan en la mediana de las repeticiones); la gravedad sale de cualquiera de las dos.
UMBRAL_ALERTA_MEDIA = 50                 # faltaran camas: aviso cuando es mas probable que si superar la capacidad a 48 h
UMBRAL_ALERTA = 84                       # faltaran camas: critico por probabilidad (solo se alcanza en los picos de un caso normal)
UMBRAL_FALTAN = 1                        # faltaran camas: aviso si en la mediana falta al menos 1 cama (107 ocupadas contra 106)
UMBRAL_FALTAN_CRITICO = 12               # faltaran camas: critico si faltan 12 o mas (118 ocupadas contra 106)
UMBRAL_COLA = 28                         # cola: aviso (pacientes esperando cama a la vez; lo habitual son ~25)
UMBRAL_COLA_CRITICA = 33                 # cola: critico (el percentil 90 real de la cola es 33)
# Pico de llegadas de la tarde (19-nov-2026): adelanta la alerta de cola. Las llegadas entre las 14 y las 19 h son 65 por dia en promedio (datos reales, 1-feb-2023 a 9-abr-2026,
# llegadas del dia por su reparto por franja del dia de la semana) y el percentil 90 es 81. Con la operacion normal del simulador nunca se supera (maximo 76,7 en 90 dias); con 15 % mas de
# llegadas se supera 19 de 90 dias. Es un indicador del volumen del dia, no una medida independiente: el reparto por franja es fijo por dia de la semana. Criterio de esta pagina.
UMBRAL_LLEGADAS_TARDE = 81               # cola (pico de la tarde): aviso si las llegadas de 14 a 19 h llegan a 81 o mas ese dia...
FRACCION_COLA_PICO = 0.8                 # ...y la cola ya es de al menos el 80 % del umbral de cola (22 de 28 pacientes)
ARRANQUE_SIN_ALERTAS = 7                 # los primeros dias vienen de la siembra con el censo real y no generan alertas: 7 (4 si el plazo es de 2 semanas o menos, porque la siembra deja las camas por encima de 118 los primeros 3 dias; 12 h en la vista horaria)


# ---------- Alertas por paciente (20-nov-2026) ----------
# Se cuentan sobre los pacientes de UNA repeticion de la simulacion (los mismos de las tablas), dia a dia. Umbrales calibrados con corridas de 90 dias
# en operacion normal (sin palancas): mediana, percentil 90 y maximo de cada conteo; con estancia +15 % y con perfiles de estres para ver cuanto sube.
# 1) Estancias mas largas de lo normal: pacientes en cama que ya llevan mas dias que el 90 % de los pacientes de su perfil (edad x tipo de visita) en los datos
#    reales 2023-2026. Normal: mediana 15, p90 21, maximo 23; con estancia +15 %: mediana 20, p90 28.
NORMAL_SOBRE_PERFIL = 15
UMBRAL_SOBRE_PERFIL = 23                 # aviso
UMBRAL_SOBRE_PERFIL_CRITICO = 28         # critico
# 2) Esperas de mas de 3 dias: pacientes que llevan 72 h o mas sin cama (el percentil 90 real de la espera es 73,9 h). Normal: mediana 5, p90 8, maximo 12.
#    Se mueve aparte de la cola total (correlacion 0,35): la cola puede verse normal mientras se acumulan los peores casos.
NORMAL_ESPERA_EXTREMA = 5
UMBRAL_ESPERA_EXTREMA = 10               # aviso
UMBRAL_ESPERA_EXTREMA_CRITICO = 13       # critico
ESPERA_EXTREMA_H = 72
# 3) Ingresos con riesgo de estancia larga: % de quienes recibieron cama en los ultimos 7 dias que son mayores de 60 o entraron como treatment urgency
#    (2 a 3 veces mas riesgo de pasar de 14 dias, pagina Estancias largas). Normal: mediana 37 %, maximo 46 %; con 20 % de perfiles de estres: mediana 56 %.
NORMAL_INGRESOS_RIESGO = 37
UMBRAL_INGRESOS_RIESGO = 47              # aviso
UMBRAL_INGRESOS_RIESGO_CRITICO = 55      # critico
# Histeresis (20-nov-2026): una alerta por paciente que ya salto sigue activa (no vuelve a saltar) hasta que el conteo baja de este nivel. Sin esto el conteo, que sube y baja
# de un dia a otro, cruzaba el umbral una y otra vez (hasta 10 avisos por corrida con estancia +15 %).
SUELTA_SOBRE_PERFIL = 19
SUELTA_ESPERA_EXTREMA = 7
SUELTA_INGRESOS_RIESGO = 42
