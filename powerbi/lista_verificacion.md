# Lista de verificación (QA y publicación)

## Antes de armar
- [ ] ¿Windows con Power BI Desktop? ¿Licencia para publicar y compartir (verificar con Uninorte)?
- [ ] Paquete de datos descargado; fecha de `LEEME.txt` coincide con la última que dio Daniela.
- [ ] Análisis pendientes entregados (A1, A2, A2b, A4, A5, B2) o páginas 7 (bandas), 8, 9 y 11 marcadas como «Pendiente».
- [ ] Autorización de los organizadores sobre datos por fila (D2 y D3 de `docs/hun/sesion_de_preguntas.md`). Si no: publicar solo tablas agregadas.

## Calidad de los números
- [ ] Todas las filas de `cifras_de_control.csv` reproducidas en el dashboard (y la sección 8 de `roadmap_powerbi.md`).
- [ ] Espera: mediana 18,8 / p75 37,9 / p90 73,3; >24 h 43,9 %; >48 h 20 %; estancias 25.777.
- [ ] Simulador en base: 105,0 camas; estancia −5 % → −5,9; ingresos +10 % → +11,9; 30 % altas → 5,1 camas libres y 8,3 % / 2,9 %.
- [ ] Todo percentil lleva su n; grupos con n < 30 ocultos.
- [ ] Segmentadores sincronizados y «Restablecer» funciona; ninguna página queda vacía con algún filtro.
- [ ] Filtrar `periodo_caida_de_datos = 0` da mediana 18,5 y p90 72,6 (comprobar que se entiende la diferencia).

## Honestidad del mensaje
- [ ] «Asociación, no causa» en páginas 4, 5 y 11; R² del 14 % visible.
- [ ] Pronóstico de ingresos diario NO presentado como bueno; usar el semanal.
- [ ] Simulador rotulado «escenario»; cota y estimación distinguidas.
- [ ] Nota de registro degradado desde el 10-abr-2026 y de duración medida en ~38 % de urgencias.
- [ ] Ninguna cifra provisional en páginas pendientes.

## Visual
- [ ] Tema `tema.json` aplicado; azul = espera, naranja = referencia; leyenda con 2+ series; no solo color.
- [ ] Probado en proyector, alto contraste y ancho móvil; títulos con la conclusión.

## Publicación
- [ ] Si hay filas por estancia: **no** usar «Publicar en la web» (enlace público). Compartir por el Service con cuentas, o publicar agregados.
- [ ] Abrir el enlace con una cuenta sin acceso previo.
- [ ] Exportar `.pbit` (sin datos) y capturas; **no subir el `.pbix` a git**.
- [ ] PDF de respaldo y video corto de navegación (plan B si falla el enlace).
