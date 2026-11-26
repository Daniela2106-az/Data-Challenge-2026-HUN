# Página «Presentación» (final del Data Challenge, 27-nov-2026)

Página `/presentacion` del dashboard (menú lateral, sección «Presentación»): 12 diapositivas para 10 minutos ante el hospital, con el mismo estilo del dashboard. Código: `dashboard/pages/presentacion.py`, `dashboard/assets/presentacion.js` y `dashboard/assets/presentacion.css`.

## Cómo se usa
- **Pantalla completa:** botón «Pantalla completa» o tecla F. Esc sale.
- **Avanzar:** →, espacio, AvPág, Enter o el clicker. **Retroceder:** ←, RePág o Retroceso. **Ensayar desde una diapositiva:** `/presentacion?diapo=5`.
- Nadie toca el computador: lo demás ocurre solo.
  - Diapositiva 4: los cinco módulos aparecen uno tras otro (si se pulsa Siguiente antes, aparecen todos).
  - Diapositiva 5: al entrar, el simulador queda quieto para explicar el caso; la siguiente pulsación lo arranca (sin cambiar de diapositiva) y la siguiente avanza. Se reproduce con el caso de temporada alta (10 % más llegadas, 90 días). Un cursor pulsa «Reproducir», «Aplicar mejora y comparar» y «Continuar con la mejora»; solo se muestra la alerta «Faltarán camas» (las demás se continúan solas) y al final salen los resultados como notificaciones. Si se vuelve desde la diapositiva anterior, se reinicia y espera otra pulsación; desde la siguiente, se queda como iba.
  - Diapositiva 6: módulos del simulador calculados con esa misma corrida.
  - Diapositiva 10: las dos preguntas del asistente se escriben solas; las respuestas son del asistente real, guardadas en `dashboard/presentacion_asistente.json` (no dependen de la conexión ni del límite diario).

## De dónde salen las cifras
- **Fijas (diapositivas 7, 8 y 11):** `src/impacto_presentacion.py` (simulador integral, 90 días desde el 9-abr-2026, 400 repeticiones, semilla fija). En temporada alta la alerta propone sola la operación óptima (estancias de más de 14 días −15 % y 30 % de las altas de la tarde a la mañana): 4,0 camas desocupadas cada día, 25 % menos camas faltantes, ~66 pacientes hospitalizados más en los 3 meses (pacientes = camas desocupadas ÷ estancia media, una aproximación). La diapositiva 7 («Qué gana el hospital») usa en cambio un año completo (365 días, 1.000 repeticiones, operación normal) sin y con todas las recomendaciones medibles: ~320 pacientes hospitalizados más (~1.730 días-cama liberados), ≈5 camas ganadas (4,7 libres más cada día), ~6.700 horas menos de espera por cama sumadas y 35 % menos camas faltantes.
- **Validación (diapositiva 9):** lo que cada módulo estimó frente a lo que pasó en meses que no conocía. Pronosticador: pruebas guardadas del modelo (`BT` de la página Pronóstico). Paciente en espera: `calibracion_corte_paso3.csv`. Paciente en cama: `comparacion_estimadores_estancia.csv` (corrido el 26-nov-2026; mejora vigente 4,4 %). Planeación de camas y Simulador integral: se recalculan al abrir la página con el motor de cada uno (entrenados hasta dic-2025, enero a 9-abr-2026), con la serie real completa (sin excluir días).
- La ocupación simulada de enero a abril de 2026 queda algo por encima de la real (en marzo y abril la ocupación real bajó); no se ajusta: la validación se muestra tal como sale.

## Reutiliza, no recalcula
Las gráficas de Resumen, Llegada y altas, Espera de cama y Estancias largas se llaman desde sus páginas; el Simulador integral se incrusta completo (su `layout()`, sin persistencia de sesión). Los módulos de `pages/` se toman de `dash.page_registry`: Dash ejecuta cada archivo de `pages/` una sola vez y una importación propia registraría sus callbacks dos veces.
