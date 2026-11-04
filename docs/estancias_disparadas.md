# A2b — ¿Qué comparten las estancias que se disparan? (3-nov-2026)

Idea de Anthony: mirar las estancias muy largas y ver qué tienen en común. Script: `src/estancias_disparadas.py`. Tablas (fuera de git): `resultados/tablas/disparadas_*.csv`. Gráfico: `resultados/graficos/estancias_disparadas.png`.

**Reglas:** una fila por estancia (`estancia_id`), edad y sexo de la persona real (4.10 de `CLAUDE.md`), ingresos hasta el 9-abr-2026 con alta registrada antes del 10-abr. **Larga** = más de 14 días (1.515 de 23.405 estancias, 6,5 %). **Muy larga** = más de 30 días (277, 1,2 %). Todo son asociaciones, no causas.

## 1. Cuándo
- El % de largas por mes de ingreso sube de 5,5 % a 7,6 % (+0,06 puntos por mes, IC 95 % +0,02 a +0,10). Sube sobre todo desde el 4.º trimestre de 2024 (8,3 %).
- No hay mes del año especial (rango 5,5–7,6 %). Solo 3 de 37 meses están por encima de lo esperado por azar: no hay "meses malos" puntuales; es un aumento gradual.
- Coincide con lo de la ocupación (`CLAUDE.md` 4.8): las estancias de más de 30 días pasaron de 63 a 117 por año.

## 2. Quién
- **Edad:** el % de largas es 3,5–4 % hasta los 29 años y llega a 11,6 % desde los 75. Frente a 15–29 años, la probabilidad de ser larga se multiplica por 2,0 (45–59), 2,5 (60–74) y 3,0 (75+).
- **Tipo de visita:** la de tipo "Treatment urgency" tiene 12,7 % de largas (9 % de las estancias, 18 % de las largas); razón de probabilidades 2,4 (3,6 para muy largas). Las ambulatorias casi nunca (0,9 %).
- **Sexo:** casi sin efecto (hombres 6,9 %, mujeres 6,2 %; razón 1,17).
- **Diagnóstico** (solo estancias con diagnóstico traducido; mapeo revisado el 3-nov): cáncer 2,8 veces, infecciosas 2,7, salud mental 2,6, musculoesquelético 2,3, neurológico 2,1; menos largas: embarazo/parto 0,4 y renal/urinario 0,5. Ojo: el diagnóstico se registra tarde y puede venir del registro gemelo.
- **Franja de llegada:** tarde y madrugada ~1,2 veces. La espera de cama previa también se asocia (1,21).
- Modelo con lo que se sabe al llegar: AUC 0,69 (0,72 para muy largas). Sirve para describir, no para predecir una estancia individual.

## 3. Qué les pasa (procedimientos y laboratorios)
`Q01` y `Q02` (lote 5 de `src/auditoria_bd.py`) se cruzan con la estancia por la visita raíz de cada copia (99,4 % de cobertura) y solo cuentan las filas de la persona real. Se muestran conceptos con al menos 100 estancias; "razón" = % de largas que lo tienen / % de las demás.

**Procedimientos (toda la estancia)** — ojo: una estancia larga tiene más tiempo para acumular procedimientos, así que parte de la razón es solo duración.
| Concepto | Razón | % largas | % otras |
|---|---|---|---|
| Inserción de catéter central de inserción periférica (PICC) | 20,7 | 11,6 | 0,6 |
| Guía fluoroscópica | 19,3 | 7,7 | 0,4 |
| Atendido por nutrición hospitalaria | 7,8 | 22,9 | 2,9 |
| Escarectomía (retiro de tejido muerto de heridas) | 7,8 | 2,8 | 0,4 |
| Transfusión de glóbulos rojos | 6,4 | 13,0 | 2,0 |

**Laboratorios de las primeras 48 h de cama** (menos sesgados por la duración, pues miran antes de que se note la estancia larga):
| Concepto | Razón | % largas | % otras |
|---|---|---|---|
| Hemocultivo anaerobio | 6,8 | 6,9 | 1,0 |
| Cultivo de líquido cefalorraquídeo | 5,5 | 4,3 | 0,8 |
| Hemocultivo aerobio | 4,7 | 9,1 | 1,9 |
| Gases arteriales | 3,9 | 17,5 | 4,5 |
| Ácido láctico | 3,6 | 12,1 | 3,3 |

**Lectura (sin formación clínica, en palabras simples):** las estancias largas se parecen a pacientes con infección grave o inestabilidad desde el inicio (cultivos de sangre y de líquido cefalorraquídeo, gases en sangre, lactato), que luego necesitan acceso venoso prolongado (PICC), transfusiones, nutrición y curaciones. Es coherente con lo ya visto en la auditoría (laboratorios casi diarios, UCI en 33 %, nutrición en 49 % de las de más de 30 días). Validación clínica pendiente.

## 4. Qué NO dice esto
- Un cultivo pedido en las primeras 48 h indica que el médico sospechó infección, no que la causa de la estancia larga sea la infección.
- No hay servicio, cama ni signos vitales en la base: no se puede saber si la larga se debe a la clínica o a esperar un traslado, cuidados en casa o trámites.
- Los nombres de los conceptos salen de la tabla `concept` (consulta `sql/nombres_conceptos_disparadas.sql`).
- Solo se consultó el nombre de los 44 conceptos con mayor razón; el resto aparece en el CSV por su código.

## 5. Para qué sirve
Un criterio de alerta temprana **descriptivo**: paciente de 60+ años, entrada por "Treatment urgency", con cultivos y gases en las primeras 48 h, merece seguimiento de planificación de alta/traslado. No es un modelo predictivo validado (AUC 0,69 con datos al llegar).
