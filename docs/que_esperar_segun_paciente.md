# Qué esperar según el paciente: espera de cama y estancia (10-nov-2026)

Reúne en un solo lugar lo que sabemos de **cómo cambian la espera de cama y la estancia en cama** según quién es el paciente, qué diagnóstico tiene y qué se le hace. Sirve para el documento final y para el dashboard (perfil simulado).
Script de la consulta: `src/que_esperar.py` (tablas `que_esperar_*.csv`, fuera de git). Detalles: `docs/perfiles_pacientes.md`, `docs/factores_estancia.md`, `docs/diagnosticos_todos.md`, `docs/estancias_disparadas.md`, `docs/procedimientos_y_laboratorios.md`.
Periodo confiable (1-feb-2023 a 9-abr-2026), estancias únicas hospitalizadas (23.537). Referencia: **espera de cama mediana 18,5 h (p90 72,9 h); estancia mediana 69,8 h (p90 266 h)**. Todo son asociaciones, no causas.

## 1. Quién es el paciente (perfil)
«Raza» y «etnicidad» **no se pueden usar**: en `PERSON` el 95 % de la raza está sin dato y la etnicidad es casi toda «Hispanic or Latino». El perfil queda en **edad, sexo y tipo de visita**.

| Característica | Espera de cama | Estancia en cama |
|---|---|---|
| **Edad** | Niños 0–4: 7,8 h; 5–14: 12,3 h; 15–29: 17,2 h; desde los 30: 24–27 h | Sube con la edad: 52–68 h hasta los 44; 92 h a los 60–74; 103 h desde los 75. Frente a 15–29 años: +25 %, +33 %, +46 % |
| **Sexo** | **Mujeres 22,3 h frente a 14,3 h** de hombres; +27 % (IC 23–31) con todo controlado. **Hallazgo abierto sin explicación** (no es obstetricia ni la saturación del momento) | **Sin diferencia** (hombres −2 %) |
| **Tipo de visita** | Treatment urgency 9,8 h; urgencias 20,8 h; ambulatoria 11,3 h | **Treatment urgency 112 h** (+63 %); urgencias 69 h; ambulatoria 44 h (−35 %) |
| **Hora de llegada** | Madrugada 12–15 h; tarde ~25 h (la cama se asigna en dos olas: 15–17 h y 20–23 h) | Sin efecto |
| **Año** | Mediana estable; los peores casos empeoran (p90 de 61 h a 80 h) | Media +16 % (4,57 a 5,31 días): la mitad es la cola de más de 30 días |
| **Espera ↔ estancia** | — | +9 % de estancia por cada desviación estándar más de espera (asociación) |

**Cuánto explica todo esto:** los factores observables explican **16 % de la espera y 8–11 % de la estancia** (`CLAUDE.md` 6b, `docs/factores_estancia.md`): el resto no está en los datos.

## 2. Qué diagnóstico tiene (todos los diagnósticos, `docs/diagnosticos_todos.md`)
El diagnóstico es lo que más mueve la espera (7,2 puntos de R² de la espera). **1.445 diagnósticos distintos**; 105 con n ≥ 30, de los cuales 74 se distinguen del resto en la espera y 55 en la estancia.

| Patrón | Espera | Estancia | Ejemplos (n ≥ 30) |
|---|---|---|---|
| Emergencias vitales | **Muy corta** (−65 a −88 %; 1–4 h) | Variable | Infarto agudo, hemorragia subaracnoidea, insuficiencia respiratoria, cetoacidosis, arritmias |
| Cálculos, colecistitis, fracturas, lumbago, próstata | **Muy larga** (+100 a +140 %; 38–53 h) | Corta (cólico renal 50 h) o larga (colecistitis 138–146 h) | Cólico renal, colecistitis, cálculo biliar, lumbago, fractura de radio |
| Desnutrición, tuberculosis, sepsis, trastorno de la conducta alimentaria | Mediana o corta | **Muy larga** (+80 a +180 %; 150–230 h) | Sepsis (189 h), desnutrición severa (187 h) |
| Embarazo, parto y ginecología | −15 % | **Corta** (47 h) | Falso trabajo de parto, preeclampsia (115 h) |
| Cardiovascular | **−56 %** | −12 % | — |

**Espera y estancia no van juntas:** hemorragia subaracnoidea (espera 2 h, estancia 248 h) y cólico renal (espera 41 h, estancia 50 h).

## 3. Qué se le hace (procedimientos y laboratorios)
- **Procedimientos en estancias largas** (más de 14 días): acceso venoso prolongado (PICC, 20,7 veces más frecuente), guía fluoroscópica (19,3), nutrición hospitalaria (7,8), curación de heridas (7,8), transfusión (6,4). Hay un sesgo: una estancia larga acumula más procedimientos por tener más tiempo. **No se pueden fechar**, así que no sirven para predecir.
- **Laboratorios de las primeras 48 h de cama en estancias largas:** hemocultivos (4,7–6,8 veces), cultivo de LCR (5,5), gases arteriales (3,9), lactato (3,6).
- **Laboratorios de las primeras 6 h y la espera:** troponina alta −41 %, lactato −19 %, BUN −18 % (cama antes), PCR alta +13 %. Más tomas en las 6 h no alargan la espera (−0,8 % por toma, ajustado).
- **Procedimiento y laboratorio:** muchas órdenes son las mismas pruebas; solo 32 de cada 100 órdenes de examen tienen su resultado traducido; el procedimiento sin laboratorio ocurre en el 20,6 % de las estancias cortas y el laboratorio sin procedimiento en el 11,5 % (`docs/procedimientos_y_laboratorios.md`).

## 4. Qué tan bien se puede anticipar (prueba temporal: rangos con llegadas hasta jun-2025, probados con jul-2025 a 9-abr-2026)
Mejora frente a dar a todos el mismo rango (IC 95 %):

| Qué se sabe del paciente | Espera de cama | Estancia en cama |
|---|---|---|
| Solo la edad | 4,5 % (3,9 a 5,1) | 2,3 % (1,6 a 3,0) |
| Edad + sexo + tipo de visita | 6,2 % (5,5 a 6,9) | 3,8 % (2,9 a 4,5) |
| + grupo de diagnóstico | **8,9 %** (7,9 a 9,7) | 4,1 % (3,2 a 4,9) |
| (A6 al llegar, con historial y recorrido) | 8,6–9,2 % | — |

**La espera se puede dar como rango con un acierto parecido al del estimador A6; la estancia solo se describe** (2–4 % de mejora, el 90 % de su variación no está en los datos). Los rangos quedan calibrados (el 26–27 / 49–52 / 72–73 / 87–90 % de los casos reales cae por debajo de cada percentil).

## 5. Ejemplos de lo que devuelve `que_esperar()` (horas: p25 / p50 / p75 / p90)
| Paciente | Espera de cama | Estancia en cama | n |
|---|---|---|---|
| Mujer de 67, urgencias | 9 / 30 / 55 / 87 | 43 / 96 / 178 / 311 | 1.692 |
| Mujer de 67, urgencias, digestivo | 25 / 34 / 56 / 84 | 49 / 116 / 188 / 306 | 268 |
| Hombre de 67, urgencias, cardiovascular | 1 / 4 / 25 / 56 | 32 / 78 / 145 / 300 | 388 |
| Niño de 8, urgencias, respiratorio | 5 / 9 / 12 / 18 | 40 / 50 / 71 / 108 | 59 |
| Mujer de 30, urgencias, embarazo/parto | 11 / 18 / 30 / 39 | 37 / 47 / 71 / 119 | 457 |
| Hombre de 80, treatment urgency | 2 / 18 / 32 / 77 | 65 / 124 / 191 / 329 | 90 |

## 6. Para el dashboard (perfil simulado)
- **Entradas:** edad, sexo, tipo de visita y, opcional, grupo de diagnóstico. **Salida:** los dos rangos, el nivel de detalle usado (si el perfil exacto tenía menos de 30 estancias se sube de nivel y se dice) y el aviso: «rango de pacientes parecidos, no una promesa individual; solo aplica a pacientes con orden de hospitalización; la estancia se describe, no se predice».
- No incluir raza ni etnicidad, ni procedimientos (sin hora y con causalidad inversa).
- Las tablas agregadas (`que_esperar_perfiles.csv`, `que_esperar_dx.csv`) no traen filas de pacientes.

## 7. Límites
- Asociaciones, no causas; el 31 % de las estancias no tiene diagnóstico traducido; el mapeo de diagnósticos a grupos es por palabras clave, sin validación clínica.
- No hay triage, servicio ni cama: la brecha de sexo en la espera y las colas por diagnóstico no se pueden explicar.
- Solo pacientes que se hospitalizan; para cualquier paciente que llega a urgencias no sirve (solo ~9 % se hospitaliza).
- Datos confiables hasta el 9-abr-2026.
