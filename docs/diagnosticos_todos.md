# Espera de cama y estancia para TODOS los diagnósticos (10-nov-2026)

Script: `src/diagnosticos_todos.py`. Tablas (fuera de git): `resultados/tablas/dx_todos_espera_estancia.csv` (**cada** diagnóstico), `dx_grupos_espera_estancia.csv`, `dx_todos_resumen.txt`.
Antes (`docs/diagnosticos_y_tiempos.md`) solo se miraban 16 grupos y el diagnóstico principal. Aquí se cuentan **todos** los diagnósticos distintos de cada estancia.

## Cómo se hizo
- Estancias únicas hospitalizadas del periodo confiable (1-feb-2023 a 9-abr-2026): 23.537; con espera medida 22.819; con alta registrada 23.405.
- Una estancia «tiene» un diagnóstico si lo trae alguna de sus visitas (copias y registros gemelos incluidos) **y** la persona dominante de los diagnósticos de esa visita (P02) es la persona real de la estancia. Así se descartan los diagnósticos que son de la otra persona del par.
- **Cobertura: 16.265 de 23.537 estancias (69 %) tienen al menos un diagnóstico traducido.** Sin el filtro de persona serían 21.777, pero una cuarta parte de esos diagnósticos es de la otra persona. El 31 % restante no se clasifica y no se puede leer como «sin enfermedad».
- Por diagnóstico: n, espera (p25, mediana, p75, p90), estancia (ídem), % de estancias de más de 14 días y el **efecto ajustado** (cambio % de la espera y de la estancia frente a las demás estancias, controlando edad, sexo, tipo de visita y año; log(espera + 1) y log(estancia)). Valor p corregido por Benjamini–Hochberg sobre todos los diagnósticos con n ≥ 30.
- **1.445 diagnósticos distintos**: 105 tienen n ≥ 30 (interpretables); 574 aparecen en una sola estancia. Todos están en el CSV, con su n; los de n < 30 se marcan «no interpretable» y no tienen efecto ajustado.
- Referencia (todas las estancias): espera mediana 18,5 h; estancia mediana 69,0 h.

## 1. Por grupo de diagnóstico (una estancia cuenta en cada grupo que tenga)
| Grupo | Estancias | Espera mediana (p90) | Estancia mediana (p90) | Efecto ajustado en la espera | Efecto ajustado en la estancia |
|---|---|---|---|---|---|
| Musculoesquelético y dolor | 487 | 35,9 h (104) | 109 h (399) | **+64 %** (+48 a +80) | **+34 %** (+21 a +47) |
| Renal y urinario | 1.587 | 33,8 h (95) | 70 h (214) | **+71 %** (+63 a +79) | −7 % (−11 a −3) |
| Cáncer y tumores | 255 | 31,6 h (108) | 115 h (487) | **+48 %** (+29 a +71) | **+46 %** (+28 a +66) |
| Digestivo | 2.361 | 29,3 h (78) | 90 h (265) | **+49 %** (+43 a +55) | **+13 %** (+8 a +17) |
| Trauma y lesiones | 1.541 | 23,6 h (73) | 52 h (211) | +27 % (+20 a +34) | −21 % (−25 a −17) |
| Infecciosas | 1.057 | 17,5 h (110) | 98 h (407) | +14 % (+6 a +23) | **+45 %** (+37 a +54) |
| Endocrino y metabólico | 572 | 17,3 h (109) | 118 h (355) | sin efecto claro | **+28 %** (+17 a +40) |
| Embarazo, parto y ginecología | 1.949 | 17,2 h (39) | 47 h (118) | −15 % (−19 a −11) | −25 % (−28 a −22) |
| Piel y tejidos blandos | 549 | 15,3 h (96) | 89 h (308) | sin efecto claro | **+32 %** (+23 a +42) |
| Neurológico | 717 | 13,2 h (61) | 91 h (383) | **−31 %** (−38 a −24) | +10 % (+1 a +20) |
| Salud mental | 615 | 11,2 h (66) | 74 h (362) | −24 % (−32 a −16) | sin efecto claro |
| Respiratorio | 1.315 | 8,9 h (58) | 71 h (286) | −19 % (−25 a −14) | sin efecto claro |
| Cardiovascular | 2.352 | 8,9 h (58) | 86 h (306) | **−56 %** (−58 a −53) | −12 % (−17 a −8) |
| Dolor y síntomas generales | 407 | 7,0 h (30) | 56 h (144) | −38 % (−44 a −32) | −28 % (−34 a −20) |
| Recién nacido | 115 | 2,5 h (48) | 84 h (206) | −37 % (−51 a −19) | +26 % (+7 a +48) |

(También están Sangre e inmunología, Ojo/oído/boca y «Otros»; ver `dx_grupos_espera_estancia.csv`.)

## 2. Por diagnóstico concreto (n ≥ 30; efecto ajustado, solo los significativos tras BH)
Con n ≥ 30 hay 105 diagnósticos: **74 se distinguen del resto en la espera y 55 en la estancia**.

**Espera más larga** (cambio % de la espera, ajustado): lumbago con ciática +142 % (n = 112), cálculo ureteral +141 %, cálculo de vía biliar +117 %, cálculo vesicular sin colecistitis +114 %, hiperplasia prostática +110 %, contusión de cadera +110 %, tuberculosis respiratoria +105 %, sangre en la orina +103 %, **cólico renal +102 % (n = 508)**, colecistitis aguda con cálculo +102 % (n = 169), infección localizada de la piel +101 % (n = 420), fractura del extremo distal del radio +100 %, cálculo renal +98 %, fractura de fémur +97 %, colecistitis aguda +97 % (n = 215).
**Espera más corta:** taquicardia supraventricular −88 %, infarto agudo con elevación del ST −81 %, disnea −80 %, hemorragia subaracnoidea −79 %, cetoacidosis diabética −77 %, infarto agudo −75 % (n = 177), infarto sin elevación del ST −74 %, dolor de pecho −69 %, insuficiencia respiratoria aguda −66 %, preeclampsia severa −65 %, síndrome de preinfarto −61 %, arritmia auricular −52 %, convulsiones −49 %.

**Estancia más larga:** trastorno de la conducta alimentaria +182 % (n = 69), desnutrición severa +111 %, tuberculosis pulmonar +109 %, hemorragia subaracnoidea +93 %, desnutrición moderada +85 %, **sepsis +81 % (n = 170)**, colecistitis aguda con cálculo +81 %, diabetes tipo 1 +74 %, preeclampsia severa +67 %, infección de piel +62 %.
**Estancia más corta:** dolor de pecho −67 %, fractura de falange −59 %, infarto agudo −53 % (n = 177), embarazo ectópico −53 %, contusión de dedo −51 %, disnea −48 %, taquicardia supraventricular −42 %, falso trabajo de parto −34 % (n = 507).

**Los más frecuentes** (n; espera mediana; estancia mediana): infección urinaria (645; 24,9 h; 84 h), falso trabajo de parto, cólico renal (508; 40,8 h; 50 h), infección localizada de piel (420; 45,4 h; 116 h)... La tabla completa de los 1.445 diagnósticos está en `dx_todos_espera_estancia.csv`.

## Lectura
- **La espera depende sobre todo de «qué cola» le toca al diagnóstico:** las esperas largas se concentran en cálculos (renales y biliares), colecistitis, fracturas, lumbago y próstata, que parecen casos de cirugía, urología y ortopedia; las cortas, en emergencias vitales (infarto, hemorragia cerebral, insuficiencia respiratoria, arritmia, cetoacidosis). **Hipótesis sin comprobar:** prioridad clínica y colas por servicio o tipo de cama. No hay servicio ni cama en la base.
- **La estancia depende de la gravedad y de la complejidad del caso** (desnutrición, tuberculosis, sepsis, hemorragia cerebral, conducta alimentaria) y poco de la espera: hay diagnósticos con espera corta y estancia larga (hemorragia subaracnoidea: espera 2 h, estancia 248 h) y al revés (cólico renal: espera 41 h, estancia 50 h).
- **Espera y estancia no van juntas:** por eso conviene pedir las dos expectativas por separado (`docs/que_esperar_segun_paciente.md`).

## Límites
- El diagnóstico principal real no se conoce (`condition_type_concept_id` siempre vale 0): aquí se usan **todos** los diagnósticos distintos de la estancia, no uno solo; una estancia con varios diagnósticos cuenta en cada uno.
- El mapeo a grupos es por palabras clave y no tiene validación clínica.
- El diagnóstico se registra al llegar y justo antes de la cama; un diagnóstico de la estancia puede ser posterior a la espera.
- 31 % de las estancias sin diagnóstico; 574 diagnósticos con una sola estancia (no interpretables).
- Son asociaciones, no causas; 105 comparaciones (con corrección BH).
