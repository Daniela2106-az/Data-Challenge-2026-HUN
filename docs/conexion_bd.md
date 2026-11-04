# Cómo conectarse a la base del reto y hacer consultas

Guía para quien clone este repositorio y trabaje con Claude Code en la terminal. **Aquí no hay datos, ni contraseñas, ni la dirección del servidor**: todo eso se lo pides al equipo (o a los organizadores) y se guarda en tu computador, fuera del proyecto.

## 0. Lo que necesitas

1. **Acceso a la VPN de Uninorte** (usuario y contraseña de VPN que dan los organizadores) y el cliente de VPN instalado.
2. **Usuario y contraseña de la base**, y los datos de conexión (servidor, puerto y nombre de la base). Pídeselos a Daniela (coordinadora del equipo) o a los organizadores. No están en el repositorio a propósito.
3. Python 3.14 y las librerías: `pip install -r requirements.txt` (incluye `sqlalchemy` y `psycopg`).
4. macOS (las notificaciones del final usan `osascript`; en otros sistemas todo funciona menos el aviso).

## 1. Configuración, una sola vez (2 minutos)

Abre un **terminal normal** (no el de Claude Code) y escribe estos comandos **uno por uno, cada uno en una sola línea**. Si al copiar se parte una línea en dos, el comando falla (le pasó al equipo).

```
HOST='EL_SERVIDOR'; BASE='EL_NOMBRE_DE_LA_BASE'; PUERTO=EL_PUERTO; USUARIO='TU_USUARIO_BD'
```
```
printf '{"host":"%s","port":%s,"database":"%s","user":"%s"}\n' $HOST $PUERTO $BASE $USUARIO > ~/.hun_db.json
```
```
read -s "PW?Contraseña de la BD: "
```
```
echo "$HOST:$PUERTO:$BASE:$USUARIO:$PW" >> ~/.pgpass; unset PW; chmod 600 ~/.pgpass
```
```
ls -la ~/.hun_db.json ~/.pgpass
```

- El `read -s` te pide la contraseña **sin mostrarla** (sirve con símbolos como `%` o `*`). Escríbela y presiona Enter; después ejecuta la línea siguiente.
- El último comando debe mostrar los dos archivos, y `.pgpass` debe empezar con `-rw-------`.
- Los dos archivos viven en tu carpeta personal y **nunca** deben entrar al proyecto (el `.gitignore` ya bloquea `.pgpass`, `.hun_db.json`, `.env` y `credenciales*`).
- Si te equivocas: `rm -f ~/.hun_db.json ~/.pgpass` y repite desde el primer comando.

## 2. La regla de oro: la VPN te deja sin internet

**Mientras la VPN está conectada, el computador pierde el internet normal, y Claude Code (que necesita internet) se queda sin conexión.** Por eso las consultas no se corren «en vivo»: se **lanza un script en segundo plano ANTES de conectar la VPN**, que espera a que el servidor aparezca, corre las consultas, guarda CSV y avisa con una notificación.

Flujo de trabajo:

1. Escribes las consultas en un archivo `.sql` (ver `sql/ejemplo_consultas.sql`).
2. Lanzas el script (Claude Code puede hacerlo por ti):
   ```
   cd src && nohup caffeinate -i python3 ejecutar_consultas.py ../sql/mis_consultas.sql --esperar 120 > ../datos/crudos/consultas/salida.txt 2>&1 &
   ```
   (`caffeinate -i` evita que el Mac se duerma; `--esperar 120` = espera hasta 120 minutos a que conectes la VPN.)
3. **Conectas la VPN.** El script arranca solo.
4. **Dónde ver el progreso:** `datos/crudos/consultas/consultas.log` (o `datos/crudos/auditoria_bd/auditoria.log` si usas `auditoria_bd.py`). Si dice `esperando a que responda...`, todavía no conectó la VPN; cuando dice `servidor alcanzable`, ya está corriendo y va anotando cada consulta con sus filas y segundos. **No apagues la VPN hasta que el log diga `TERMINADO` y oigas la notificación con sonido.** Si la apagas a medias, la consulta que estaba corriendo queda colgada (mata el proceso con `pkill -f ejecutar_consultas.py`) y hay que repetir esa consulta. Mientras tanto, esperas la **notificación con sonido** («Consultas terminadas. Ya puedes desconectar la VPN»). Tarda de segundos a unos minutos. Puedes ver el avance en `datos/crudos/consultas/consultas.log`.
5. **Desconectas la VPN.** Vuelve el internet y Claude Code puede leer los CSV de `datos/crudos/consultas/` y analizarlos.

Formato del `.sql`: cada consulta empieza con una línea `-- nombre: algo` y termina con `;`. Para ver qué detectó sin tocar la base: `python3 src/ejecutar_consultas.py sql/mis_consultas.sql --solo-listar`.

## 3. Instrucciones para Claude Code (si eres Claude y abriste este repositorio)

- **Nunca pidas, leas, escribas ni repitas la contraseña de la base ni la de la VPN**, ni en el chat ni en archivos del proyecto. No te autentiques con credenciales que alguien pegue en el chat: dile que haga la configuración de la sección 1 en su terminal. No abras `~/.pgpass`.
- Conéctate **solo** con `src/conexion_bd.py` (lee `~/.hun_db.json`; la contraseña la toma PostgreSQL de `~/.pgpass`). La sesión es de **solo lectura** con límite de tiempo por consulta; no intentes escribir en la base.
- **No ejecutes consultas mientras la VPN esté conectada desde tu sesión**: se cae tu conexión. Usa el flujo de la sección 2: escribe el `.sql`, lanza `ejecutar_consultas.py` en segundo plano, **dile a la persona que conecte la VPN** y espera su aviso de que desconectó.
- Antes de lanzar, revisa la sintaxis. Para scripts propios con muchas consultas, mira el patrón de `src/auditoria_bd.py --probar-local` (valida el SQL con DuckDB y tablas vacías, sin tocar la base).
- Una consulta pesada que falla no debe tirar todas: `ejecutar_consultas.py` anota el error y sigue con la siguiente.
- Los resultados con datos de pacientes (una fila por paciente o por visita) **no se suben a git** (`datos/crudos/` está ignorado). Solo se suben tablas agregadas y documentos.
- Antes de proponer una consulta nueva, lee `CLAUDE.md` (sección 4 de problemas de calidad y 4.9 de la auditoría): muchas respuestas ya están.

## 4. Qué hay en la base

PostgreSQL 18, esquema **`uninorte_omop`** (formato OMOP simplificado), solo estas 8 tablas:

| Tabla | Filas | Columnas |
|---|---|---|
| `visit_occurrence` | 1,7 M | `visit_occurrence_id`, `person_id`, `visit_concept_id`, `visit_start_datetime`, `visit_end_datetime` (igual al inicio), `provider_id` (siempre 0) |
| `visit_detail` | 3,3 M | `visit_detail_id`, `visit_occurrence_id`, `visit_detail_concept_id`, `visit_detail_start_datetime`, `visit_detail_end_datetime`, `provider_id` |
| `person` | 912 mil | `person_id`, `gender_concept_id`, `year_of_birth`, `race_concept_id`, `ethnicity_concept_id` |
| `condition_occurrence` | 38,6 M | `condition_occurrence_id`, `person_id`, `visit_occurrence_id`, `condition_concept_id` (0 = sin código), `condition_start_datetime`, `condition_type_concept_id` |
| `procedure_occurrence` | 47 M | `procedure_occurrence_id`, `person_id`, `visit_occurrence_id`, `procedure_concept_id`, `procedure_date` (siempre vacía) |
| `measurement` | 16,6 M | `measurement_id`, `person_id`, `visit_occurrence_id`, `measurement_concept_id`, `measurement_datetime`, `value_as_number`, `measurement_source_value_extended` |
| `concept` | 9,6 M | `concept_id`, `concept_name`, `domain_id`, `vocabulary_id` |
| `cups` | 94 mil | `codigo`, `descripcion`, `periodo` (catálogo nacional de procedimientos; no se enlaza con `procedure_occurrence`) |

**No hay** servicio, sede, piso ni cama. Las etapas (`visit_detail_concept_id`): **9203** llegada a urgencias (ER), **3045729** atención en urgencias (TU), **9201** hospitalización (HOSP, se registra al asignar la cama), **581479** evento ambulatorio administrativo (AMB, duración 0).

**Trampas que ya conocemos** (detalle en `CLAUDE.md`, secciones 4 y 4.9):
- Cerca del 30 % de las visitas son **copias** (id = original + desfase fijo) y el 53 % de los episodios hospitalizados son la **misma estancia registrada en dos o más personas**: nunca cuentes filas directo, deduplica por intervalo o usa las tablas del pipeline.
- **El registro de etapas es confiable hasta el 9-abr-2026.** Desde el 10-abr hay visitas de más sin etapas y menos visitas con etapa ER; los diagnósticos con código desaparecen desde el 11-may. No uses esos meses para estimar niveles.
- La duración de TU solo existe en ~38 % de las etapas (el resto tiene inicio = fin).
- Las tablas **no tienen índices** (solo llaves primarias): filtra por fecha y agrega en SQL en vez de exportar tablas enteras.

## 5. Cuánto tardan las consultas (medido)

| Tipo de consulta | Tiempo aproximado |
|---|---|
| Agrupar `visit_detail` o `visit_occurrence` (1–3 M filas) | 5–15 s |
| Unir `visit_detail` con `visit_occurrence` y agrupar | 10–20 s |
| Recorrer `condition_occurrence` (38 M) | 30–60 s |
| Recorrer `procedure_occurrence` (47 M) | 45–90 s |
| Unir estancias con `measurement` (16 M) | 1–2 min |

Cada consulta tiene un límite de 15 minutos con `ejecutar_consultas.py`.

## 6. Scripts que ya existen

| Script | Para qué |
|---|---|
| `src/conexion_bd.py` | Conexión de solo lectura (`consultar(sql)` devuelve un DataFrame). |
| `src/ejecutar_consultas.py` | Corre un `.sql` en segundo plano, espera la VPN y guarda un CSV por consulta (esta guía). |
| `src/explorar_bd.py` | Esquema, tamaños, valores de columnas, catálogo `cups` (lotes 1 y 2, ya corridos el 2-nov-2026). |
| `src/auditoria_bd.py` | 30 consultas que contrastan nuestros hallazgos con la base (lotes 1 a 3, ya corridos; resultados en `CLAUDE.md` 4.8 y 4.9). |

## 7. Problemas frecuentes

| Síntoma | Causa y arreglo |
|---|---|
| `connection timeout expired` o `failed to resolve host` | La VPN no está conectada, o el host del `~/.hun_db.json` es incorrecto (revísalo con `cat ~/.hun_db.json`; no muestra la contraseña). |
| `password authentication failed` | La contraseña de `~/.pgpass` está mal o el usuario no coincide con el del `.hun_db.json`. Borra los dos archivos y repite la sección 1. |
| `FATAL: no pg_hba.conf entry` o `Connection refused` | Puerto o servidor equivocado. |
| El terminal muestra `heredoc>` o dice `parse error` | Un comando se partió en dos líneas al copiar. `Ctrl + C` y pega de nuevo, una línea a la vez. |
| `~/.pgpass` ignorado | Debe tener permisos `600` (`chmod 600 ~/.pgpass`). |
| Claude Code deja de responder al conectar la VPN | Es lo esperado: la VPN apaga el internet normal. Lanza siempre el script **antes** de conectar (sección 2). |
