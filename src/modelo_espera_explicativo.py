"""
modelo_espera_explicativo.py  -  version 1 (8-nov-2026)
Ficha A4 / 3.3 del plan de cuellos de botella (docs/fichas_de_tareas.md, docs/pendientes_y_reparto.md).

PREGUNTA
  Que caracteristicas conocidas AL LLEGAR se asocian a esperar mas de 24 h por una cama, separando el efecto
  de cada una (razon de probabilidades con intervalo), con validacion temporal y sin esconder que el modelo
  explica poco (AUC/Brier).

QUE HACE (este archivo: solo el PASO 2 del plan, el modelo base "al llegar")
  1. Carga tabla_episodios.parquet, filtra a estancia_unica & hospitalizado & espera_cama_h medida.
  2. Separa en 3 tramos TEMPORALES: entrenamiento (2023-02 a 2025-06), validacion (2025-07 a 2025-12) y
     prueba (2026-01 a 2026-04-09, NO 2026-05-31 como decia la ficha original: el registro se degrada desde
     el 10-abr-2026, docs/CONTEXTO_TECNICO.md 4.9 - no se toca la prueba todavia, solo se separa).
  3. Construye el diseno de variables (dummies con categoria de referencia fija en el tramo de entrenamiento;
     numericas estandarizadas con media/desvio del tramo de entrenamiento).
  4. Ajusta una regresion logistica A MANO (Newton-Raphson/IRLS, sin scikit-learn ni statsmodels, mismo estilo
     que ols() en dependencia_carga.py y altas_y_factores.py) y calcula errores estandar de Wald.
  5. Reporta razones de probabilidades (OR = exp(beta)) con intervalo de 95 %, y AUC/Brier en entrenamiento y
     validacion (la prueba se deja para el paso 5 del plan, no se toca aqui).

VARIABLES (permitidas por la ficha 3.3 - se conocen al llegar; nunca categoria_dx, dx_*, n_lab*, horas_*, ruta*)
  Categoricas (dummy, referencia fija o la mas frecuente del entrenamiento): franja, dia_semana_num, mes,
    grupo_edad, sexo, tipo_visita.
  Booleanas (0/1 directo): festivo, reingreso_72h, reingreso_30d.
  Numericas (estandarizadas con media/desvio de ENTRENAMIENTO): ocup_hosp, ocup_tu, llegadas_6h_previas,
    llegadas_24h_previas, n_episodios_previos.
  Dos ajustes sobre la lista de la ficha, para evitar colinealidad perfecta (se declaran, no son un olvido):
    - se usa SOLO grupo_edad (no tambien edad continua: son la misma informacion, edad binned).
    - se usa SOLO festivo + dia_semana_num (no tambien dia_no_habil: dia_no_habil = fin_de_semana OR festivo,
      ya esta cubierto por la combinacion de las dos).

ENTRADA  datos/procesados/tabla_episodios.parquet

SALIDAS  resultados/tablas/modelo_espera_coeficientes_base.csv (razones de probabilidades con IC 95 % y valor p)
         resultados/tablas/modelo_espera_metricas_base.csv (AUC y Brier por tramo)

OJO AL LEER
  - Es un modelo EXPLICATIVO, no una alerta individual: el AUC de referencia (prueba del 21-oct, sin este rigor
    de validacion) fue 0,60. Si este modelo da un numero parecido, confirma el techo ya conocido.
  - Los errores estandar son los de Wald (inversa de la matriz de informacion de Fisher en el optimo): son el
    equivalente exacto a lo que daria statsmodels.Logit, solo que se escriben a mano.
  - Todo es asociacion, no causa.
"""
import math
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
PROC = RAIZ / "datos" / "procesados"
TABLAS = RAIZ / "resultados" / "tablas"
TABLAS.mkdir(parents=True, exist_ok=True)

# ----------------------------------------------------------------------
# Parametros
# ----------------------------------------------------------------------
TRAIN = ("2023-02-01", "2025-07-01")   # [ini, fin)
VAL = ("2025-07-01", "2026-01-01")
TEST = ("2026-01-01", "2026-04-10")    # corte v3.9 (docs/CONTEXTO_TECNICO.md 4.9): no usar mas alla del 9-abr-2026

CATEGORICAS = ["franja", "dia_semana_num", "mes", "grupo_edad", "sexo", "tipo_visita"]
REF_FIJA = {"franja": "madrugada 0-5", "dia_semana_num": "0", "sexo": "Hombre"}   # el resto: la mas frecuente en entrenamiento
BOOLEANAS = ["festivo", "reingreso_72h", "reingreso_30d"]
NUMERICAS = ["ocup_hosp", "ocup_tu", "llegadas_6h_previas", "llegadas_24h_previas", "n_episodios_previos"]
OBJETIVO = "espera_mas_24h"

pd.set_option("display.width", 220)
pd.set_option("display.max_columns", None)
pd.set_option("display.max_rows", 200)


def titulo(t):
    print("\n" + "=" * 70 + "\n" + t + "\n" + "=" * 70)


# ----------------------------------------------------------------------
# 1) Carga y filtro
# ----------------------------------------------------------------------
titulo("1. CARGA Y FILTRO")
ep = pd.read_parquet(PROC / "tabla_episodios.parquet")
m = ep[ep.estancia_unica & ep.hospitalizado & ep.espera_cama_h.notna()].copy()
print(f"episodios totales: {len(ep)} | con estancia_unica & hospitalizado & espera medida: {len(m)}")
print(f"espera_cama_h: mediana {m.espera_cama_h.median():.1f} h | p90 {m.espera_cama_h.quantile(.9):.1f} h | "
      f"% > 24h {100 * m[OBJETIVO].mean():.1f} %  (referencia docs/CONTEXTO_TECNICO.md: 18,6 / 73,9 / 43,7)")
for c in CATEGORICAS + BOOLEANAS + NUMERICAS:
    assert m[c].notna().all(), f"hay nulos en {c}, revisar"
print("sin nulos en las variables del modelo: OK")

# ----------------------------------------------------------------------
# 2) Split temporal
# ----------------------------------------------------------------------
titulo("2. SPLIT TEMPORAL")


def tramo(desde, hasta):
    return m[(m.ini >= desde) & (m.ini < hasta)]


tr, va, te = tramo(*TRAIN), tramo(*VAL), tramo(*TEST)
for nombre, d in [("entrenamiento", tr), ("validacion", va), ("prueba", te)]:
    print(f"{nombre:14s}: n={len(d):6d}  {d.ini.min()} -> {d.ini.max()}  % > 24h = {100 * d[OBJETIVO].mean():.1f} %")
assert len(tr) + len(va) + len(te) <= len(m), "los tramos se solapan"

# ----------------------------------------------------------------------
# 3) Diseno de variables (parametros fijados SOLO con entrenamiento)
# ----------------------------------------------------------------------
titulo("3. DISENO DE VARIABLES")
meta = {"cat": {}, "num": {}}
for col in CATEGORICAS:
    niveles = sorted(tr[col].astype(str).unique().tolist())
    ref = REF_FIJA.get(col) or tr[col].astype(str).value_counts().index[0]
    meta["cat"][col] = (niveles, ref)
    print(f"  {col:16s} niveles={niveles}  referencia='{ref}'")
for col in NUMERICAS:
    meta["num"][col] = (tr[col].mean(), tr[col].std())
    print(f"  {col:20s} media_train={meta['num'][col][0]:.2f}  desvio_train={meta['num'][col][1]:.2f}")


def construir_X(df):
    partes = [pd.Series(1.0, index=df.index, name="const")]
    for col in CATEGORICAS:
        niveles, ref = meta["cat"][col]
        s = pd.Categorical(df[col].astype(str), categories=niveles)
        d = pd.get_dummies(s, prefix=col, dtype=float)
        d.index = df.index
        col_ref = f"{col}_{ref}"
        if col_ref in d.columns:
            d = d.drop(columns=col_ref)
        partes.append(d)
    for col in BOOLEANAS:
        partes.append(df[col].astype(float).rename(col))
    for col in NUMERICAS:
        mu, sd = meta["num"][col]
        partes.append(((df[col].astype(float) - mu) / sd).rename(col))
    return pd.concat(partes, axis=1)


Xtr, Xva, Xte = construir_X(tr), construir_X(va), construir_X(te)
ytr, yva, yte = tr[OBJETIVO].values, va[OBJETIVO].values, te[OBJETIVO].values
print(f"\ncolumnas del diseno ({Xtr.shape[1]}): {list(Xtr.columns)}")

# ----------------------------------------------------------------------
# 4) Regresion logistica a mano (Newton-Raphson / IRLS)
# ----------------------------------------------------------------------
titulo("4. AJUSTE (NEWTON-RAPHSON)")


def sigmoid(z):
    return 1 / (1 + np.exp(-np.clip(z, -35, 35)))


def ajustar_logit(X, y, max_iter=50, tol=1e-9):
    Xv = X.values.astype(float)
    beta = np.zeros(Xv.shape[1])
    for it in range(max_iter):
        p = np.clip(sigmoid(Xv @ beta), 1e-10, 1 - 1e-10)
        w = p * (1 - p)
        XtWX = Xv.T @ (Xv * w[:, None])
        grad = Xv.T @ (y - p)
        delta = np.linalg.solve(XtWX + np.eye(Xv.shape[1]) * 1e-9, grad)
        beta = beta + delta
        if np.max(np.abs(delta)) < tol:
            break
    else:
        print(f"  AVISO: no convergio del todo en {max_iter} iteraciones (max |delta| = {np.max(np.abs(delta)):.2e})")
    p = np.clip(sigmoid(Xv @ beta), 1e-10, 1 - 1e-10)
    w = p * (1 - p)
    XtWX = Xv.T @ (Xv * w[:, None])
    cov = np.linalg.pinv(XtWX)
    se = np.sqrt(np.diag(cov))
    print(f"  convergio en {it + 1} iteraciones" if it + 1 < max_iter else "")
    return beta, se


beta, se = ajustar_logit(Xtr, ytr)

# ----------------------------------------------------------------------
# 5) Razones de probabilidades (OR) con IC 95 % y valor p
# ----------------------------------------------------------------------
titulo("5. RAZONES DE PROBABILIDADES (OR) - variables conocidas al llegar")


def norm_cdf(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


z = beta / se
pval = [2 * (1 - norm_cdf(abs(zi))) for zi in z]
coef = pd.DataFrame({
    "variable": Xtr.columns, "beta": beta.round(4), "error_estandar": se.round(4),
    "OR": np.exp(beta).round(3),
    "IC95_bajo": np.exp(beta - 1.96 * se).round(3),
    "IC95_alto": np.exp(beta + 1.96 * se).round(3),
    "valor_p": np.round(pval, 4),
})
coef = coef[coef.variable != "const"].sort_values("OR", ascending=False)
print(coef.to_string(index=False))
coef.to_csv(TABLAS / "modelo_espera_coeficientes_base.csv", index=False)
print("\nguardado: resultados/tablas/modelo_espera_coeficientes_base.csv")
print("\nreferencias usadas (categoria base de cada variable):")
for col in CATEGORICAS:
    print(f"  {col}: {meta['cat'][col][1]}")

# ----------------------------------------------------------------------
# 6) AUC y Brier (entrenamiento y validacion; la prueba se deja para el paso 5 del plan)
# ----------------------------------------------------------------------
titulo("6. AUC Y BRIER (sin tocar el tramo de prueba todavia)")


def predecir(X):
    return sigmoid(X.values.astype(float) @ beta)


def auc_manual(y, score):
    r = pd.Series(score).rank(method="average").values
    n1 = y.sum()
    n0 = len(y) - n1
    if n1 == 0 or n0 == 0:
        return np.nan
    r_pos = r[y == 1].sum()
    return (r_pos - n1 * (n1 + 1) / 2) / (n1 * n0)


def brier(y, p):
    return float(np.mean((p - y) ** 2))


filas = []
for nombre, X, y in [("entrenamiento", Xtr, ytr), ("validacion", Xva, yva)]:
    p = predecir(X)
    filas.append({"tramo": nombre, "n": len(y), "pct_positivos": round(100 * y.mean(), 1),
                  "AUC": round(auc_manual(y, p), 3), "Brier": round(brier(y, p), 4)})
met = pd.DataFrame(filas)
print(met.to_string(index=False))
print("\n(referencia: la prueba del 21-oct sin este rigor de validacion dio AUC 0,60 'al llegar' - "
      "fichas_de_tareas.md:12. Brier de un modelo que siempre predice la tasa base "
      f"({ytr.mean():.3f}) seria {brier(ytr, np.full_like(ytr, ytr.mean())):.4f} (linea base ingenua).")
met.to_csv(TABLAS / "modelo_espera_metricas_base.csv", index=False)
print("\nguardado: resultados/tablas/modelo_espera_metricas_base.csv")
print("\nNO se evalua el tramo de prueba (2026-01-01 a 2026-04-09) en este script: eso es el paso 5 del plan,")
print("despues de decidir en el paso 3 si alguna mejora (perfiles A1, interacciones) se queda.")

# ----------------------------------------------------------------------
# 7) PASO 3 DEL PLAN: intentos de mejora (siempre comparando contra el modelo base de arriba, en VALIDACION)
# ----------------------------------------------------------------------
titulo("7. EXTENSION A: PERFIL CONJUNTO (grupo_edad x sexo x tipo_visita) en vez de las tres por separado")
tr["perfil"] = tr.grupo_edad.astype(str) + "|" + tr.sexo.astype(str) + "|" + tr.tipo_visita.astype(str)
va["perfil"] = va.grupo_edad.astype(str) + "|" + va.sexo.astype(str) + "|" + va.tipo_visita.astype(str)
conteo_perfil = tr.perfil.value_counts()
validos_perfil = conteo_perfil[conteo_perfil >= 30].index.tolist()
print(f"perfiles con menos de 30 casos en entrenamiento (se colapsan a 'otros'): "
      f"{(conteo_perfil < 30).sum()} de {len(conteo_perfil)}")
tr["perfil_c"] = tr.perfil.where(tr.perfil.isin(validos_perfil), "otros")
va["perfil_c"] = va.perfil.where(va.perfil.isin(validos_perfil), "otros")
niveles_perfil = sorted(tr.perfil_c.unique().tolist())
ref_perfil = tr.perfil_c.value_counts().index[0]
print(f"perfil conjunto: {len(niveles_perfil)} niveles, referencia = '{ref_perfil}'")

CAT_SIN_PERFIL = ["franja", "dia_semana_num", "mes"]   # grupo_edad/sexo/tipo_visita quedan dentro de "perfil"


def dummies_de(df, col, niveles, ref):
    s = pd.Categorical(df[col].astype(str), categories=niveles)
    d = pd.get_dummies(s, prefix=col, dtype=float)
    d.index = df.index
    col_ref = f"{col}_{ref}"
    return d.drop(columns=[col_ref]) if col_ref in d.columns else d


def construir_X_perfil(df):
    partes = [pd.Series(1.0, index=df.index, name="const")]
    for col in CAT_SIN_PERFIL:
        niveles, ref = meta["cat"][col]
        partes.append(dummies_de(df, col, niveles, ref))
    partes.append(dummies_de(df, "perfil_c", niveles_perfil, ref_perfil))
    for col in BOOLEANAS:
        partes.append(df[col].astype(float).rename(col))
    for col in NUMERICAS:
        mu, sd = meta["num"][col]
        partes.append(((df[col].astype(float) - mu) / sd).rename(col))
    return pd.concat(partes, axis=1)


Xtr_A, Xva_A = construir_X_perfil(tr), construir_X_perfil(va)
beta_A, _ = ajustar_logit(Xtr_A, ytr)
print(f"columnas: {Xtr_A.shape[1]} (modelo base tenia {Xtr.shape[1]})")

titulo("8. EXTENSION B: interaccion franja x grupo_edad, agregada SOBRE el modelo base")


def construir_interaccion_franja_edad(df):
    niveles_fr, ref_fr = meta["cat"]["franja"]
    niveles_ge, ref_ge = meta["cat"]["grupo_edad"]
    partes = []
    for fr in niveles_fr:
        if fr == ref_fr:
            continue
        for ge in niveles_ge:
            if ge == ref_ge:
                continue
            nombre = f"franja_{fr}_x_edad_{ge}"
            partes.append(((df.franja.astype(str) == fr) & (df.grupo_edad.astype(str) == ge))
                          .astype(float).rename(nombre))
    r = pd.concat(partes, axis=1)
    r.index = df.index
    return r


Itr, Iva = construir_interaccion_franja_edad(tr), construir_interaccion_franja_edad(va)
Xtr_B, Xva_B = pd.concat([Xtr, Itr], axis=1), pd.concat([Xva, Iva], axis=1)
beta_B, _ = ajustar_logit(Xtr_B, ytr)
print(f"columnas: {Xtr_B.shape[1]} (modelo base + {Itr.shape[1]} terminos de interaccion)")

titulo("9. EXTENSION C: perfil conjunto + interaccion franja x grupo_edad, juntas")
Itr_c, Iva_c = construir_interaccion_franja_edad(tr), construir_interaccion_franja_edad(va)
Xtr_C, Xva_C = pd.concat([Xtr_A, Itr_c], axis=1), pd.concat([Xva_A, Iva_c], axis=1)
beta_C, _ = ajustar_logit(Xtr_C, ytr)
print(f"columnas: {Xtr_C.shape[1]}")

titulo("10. REINGRESO: ¿aporta solo, combinado con n_episodios_previos, o es redundante?")
print("correlacion entre las tres variables de historia del paciente (entrenamiento):")
print(tr[["reingreso_72h", "reingreso_30d", "n_episodios_previos"]].astype(float).corr().round(3).to_string())

Xtr_sin_reing = Xtr.drop(columns=["reingreso_72h", "reingreso_30d"])
Xva_sin_reing = Xva.drop(columns=["reingreso_72h", "reingreso_30d"])
beta_sin_reing, _ = ajustar_logit(Xtr_sin_reing, ytr)

Xtr_sin_nep = Xtr.drop(columns=["n_episodios_previos"])
Xva_sin_nep = Xva.drop(columns=["n_episodios_previos"])
beta_sin_nep, _ = ajustar_logit(Xtr_sin_nep, ytr)

titulo("11. TABLA RESUMEN: ¿alguna mejora sube el AUC/Brier de validacion frente al modelo base?")
modelos = [
    ("base (paso 2)", Xtr, Xva, beta),
    ("A: perfil conjunto", Xtr_A, Xva_A, beta_A),
    ("B: + interaccion franja x edad", Xtr_B, Xva_B, beta_B),
    ("C: perfil + interaccion", Xtr_C, Xva_C, beta_C),
    ("sin reingreso_72h/30d", Xtr_sin_reing, Xva_sin_reing, beta_sin_reing),
    ("sin n_episodios_previos", Xtr_sin_nep, Xva_sin_nep, beta_sin_nep),
]
filas = []
for nombre, Xt, Xv, b in modelos:
    pt, pv = sigmoid(Xt.values.astype(float) @ b), sigmoid(Xv.values.astype(float) @ b)
    filas.append({"modelo": nombre, "n_parametros": Xt.shape[1],
                  "AUC_train": round(auc_manual(ytr, pt), 3), "AUC_val": round(auc_manual(yva, pv), 3),
                  "Brier_train": round(brier(ytr, pt), 4), "Brier_val": round(brier(yva, pv), 4)})
resumen = pd.DataFrame(filas)
print(resumen.to_string(index=False))
resumen.to_csv(TABLAS / "modelo_espera_mejoras.csv", index=False)
print("\nguardado: resultados/tablas/modelo_espera_mejoras.csv")

# ----------------------------------------------------------------------
# 12) PASO 4 DEL PLAN: extension EXPLORATORIA con diagnostico (A3) - FUERA de lo permitido, modelo APARTE
# ----------------------------------------------------------------------
titulo("12. EXTENSION EXPLORATORIA: + categoria_dx (A3) - NO es un modelo 'al llegar', es un chequeo de techo")
print("AVISO DE FUGA: categoria_dx se registra DESPUES de la llegada (88% tras las primeras 2h, docs/CONTEXTO_TECNICO.md) y")
print("depende en parte de cuanto duro la espera (quien espera mas tiene mas tiempo para que se le registre un")
print("diagnostico). Este modelo NUNCA se usa para alertar ni se mezcla con los de los pasos 2-3. Solo responde:")
print("¿cuanto sube el techo si se permite 'trampa', igual que la prueba del 21-oct (AUC 0,60 -> 0,64)?\n")

conteo_dx = tr.categoria_dx.value_counts()
print(f"categoria_dx: {tr.categoria_dx.nunique()} niveles, minimo {conteo_dx.min()} casos en entrenamiento "
      f"(no hace falta colapsar ninguno)")
niveles_dx = sorted(tr.categoria_dx.astype(str).unique().tolist())
ref_dx = tr.categoria_dx.value_counts().index[0]
print(f"referencia = '{ref_dx}' (la mas frecuente)")


def dummies_dx(df):
    return dummies_de(df, "categoria_dx", niveles_dx, ref_dx)


Dtr, Dva = dummies_dx(tr), dummies_dx(va)

# D1: base del paso 2 + categoria_dx (para comparar directo contra la referencia historica 0,60 -> 0,64)
Xtr_D1, Xva_D1 = pd.concat([Xtr, Dtr], axis=1), pd.concat([Xva, Dva], axis=1)
beta_D1, se_D1 = ajustar_logit(Xtr_D1, ytr)

# D2: mejor modelo permitido (A: perfil conjunto) + categoria_dx (el techo real con lo mejor que tenemos + trampa)
Xtr_D2, Xva_D2 = pd.concat([Xtr_A, Dtr], axis=1), pd.concat([Xva_A, Dva], axis=1)
beta_D2, _ = ajustar_logit(Xtr_D2, ytr)

filas_dx = []
for nombre, Xt, Xv, b in [("base (paso 2), permitido", Xtr, Xva, beta),
                          ("D1: base + categoria_dx (fuga)", Xtr_D1, Xva_D1, beta_D1),
                          ("A: perfil conjunto, permitido", Xtr_A, Xva_A, beta_A),
                          ("D2: A + categoria_dx (fuga)", Xtr_D2, Xva_D2, beta_D2)]:
    pt, pv = sigmoid(Xt.values.astype(float) @ b), sigmoid(Xv.values.astype(float) @ b)
    filas_dx.append({"modelo": nombre, "n_parametros": Xt.shape[1],
                      "AUC_train": round(auc_manual(ytr, pt), 3), "AUC_val": round(auc_manual(yva, pv), 3),
                      "Brier_train": round(brier(ytr, pt), 4), "Brier_val": round(brier(yva, pv), 4)})
techo = pd.DataFrame(filas_dx)
print()
print(techo.to_string(index=False))
techo.to_csv(TABLAS / "modelo_espera_techo_con_dx.csv", index=False)
print("\nguardado: resultados/tablas/modelo_espera_techo_con_dx.csv")
print(f"\nreferencia historica (21-oct, fichas_de_tareas.md:12-13): AUC 0,60 'al llegar' -> 0,64 'con trampa' "
      f"(dx y laboratorios). Ganancia documentada entonces: +0,04.")

print("\nrazones de probabilidades de categoria_dx (modelo D1, para ver que diagnosticos pesan mas/menos):")
z_dx = beta_D1 / se_D1
pval_dx = [2 * (1 - norm_cdf(abs(zi))) for zi in z_dx]
coef_dx = pd.DataFrame({"variable": Xtr_D1.columns, "OR": np.exp(beta_D1).round(3),
                        "IC95_bajo": np.exp(beta_D1 - 1.96 * se_D1).round(3),
                        "IC95_alto": np.exp(beta_D1 + 1.96 * se_D1).round(3),
                        "valor_p": np.round(pval_dx, 4)})
coef_dx = coef_dx[coef_dx.variable.str.startswith("categoria_dx")].sort_values("OR", ascending=False)
print(coef_dx.to_string(index=False))
coef_dx.to_csv(TABLAS / "modelo_espera_coeficientes_dx.csv", index=False)
print("\nguardado: resultados/tablas/modelo_espera_coeficientes_dx.csv")
print("\nOJO: estos OR son solo para cuantificar el techo y describir, igual que en altas_y_factores.py seccion E.")
print("No entran al modelo final ni a ninguna alerta.")

# ----------------------------------------------------------------------
# 13) PASO 5 DEL PLAN: EVALUACION FINAL EN PRUEBA (2026-01-01 a 2026-04-09) - UNA SOLA VEZ
# ----------------------------------------------------------------------
titulo("13. EVALUACION FINAL EN EL TRAMO DE PRUEBA (una sola vez, nunca se toco antes)")
print("Modelo elegido en el paso 3: A (perfil conjunto). Se evalua tambien el modelo base del paso 2, solo")
print("para dejar el contraste completo registrado, pero A es el que se usa de aqui en adelante.\n")

te["perfil"] = te.grupo_edad.astype(str) + "|" + te.sexo.astype(str) + "|" + te.tipo_visita.astype(str)
te["perfil_c"] = te.perfil.where(te.perfil.isin(validos_perfil), "otros")
Xte_A = construir_X_perfil(te)

filas_test = []
for nombre, Xt, Xv, Xp, b in [("base (paso 2)", Xtr, Xva, Xte, beta),
                              ("A: perfil conjunto (elegido)", Xtr_A, Xva_A, Xte_A, beta_A)]:
    pt, pv, pp = (sigmoid(Xt.values.astype(float) @ b), sigmoid(Xv.values.astype(float) @ b),
                  sigmoid(Xp.values.astype(float) @ b))
    filas_test.append({"modelo": nombre,
                        "AUC_train": round(auc_manual(ytr, pt), 3), "AUC_val": round(auc_manual(yva, pv), 3),
                        "AUC_prueba": round(auc_manual(yte, pp), 3),
                        "Brier_train": round(brier(ytr, pt), 4), "Brier_val": round(brier(yva, pv), 4),
                        "Brier_prueba": round(brier(yte, pp), 4)})
final = pd.DataFrame(filas_test)
print(final.to_string(index=False))
final.to_csv(TABLAS / "modelo_espera_metricas_finales.csv", index=False)
print("\nguardado: resultados/tablas/modelo_espera_metricas_finales.csv")
print(f"\nn de prueba: {len(yte)} | % > 24h real en prueba: {100 * yte.mean():.1f} %")

titulo("14. CALIBRACION DEL MODELO ELEGIDO (A) EN PRUEBA: probabilidad predicha vs. lo que de verdad paso")
p_te_A = sigmoid(Xte_A.values.astype(float) @ beta_A)
cal = pd.DataFrame({"y": yte, "p": p_te_A})
cal["grupo"] = pd.qcut(cal.p, 5, duplicates="drop")
tabla_cal = cal.groupby("grupo", observed=True).agg(n=("y", "size"), prob_media_predicha=("p", "mean"),
                                                     pct_real_mas_24h=("y", "mean")).reset_index()
tabla_cal["prob_media_predicha"] = (100 * tabla_cal.prob_media_predicha).round(1)
tabla_cal["pct_real_mas_24h"] = (100 * tabla_cal.pct_real_mas_24h).round(1)
print(tabla_cal.drop(columns="grupo").to_string(index=False))
tabla_cal.to_csv(TABLAS / "modelo_espera_calibracion_prueba.csv", index=False)
print("\nguardado: resultados/tablas/modelo_espera_calibracion_prueba.csv")
print("\nSi 'prob_media_predicha' y 'pct_real_mas_24h' quedan parecidos en cada grupo, el modelo esta bien")
print("calibrado (aunque separe poco, cuando dice '70% de probabilidad' de verdad ronda el 70% real).")

titulo("15. POR QUE NO SIRVE PARA ALERTAR A UN PACIENTE (umbrales sobre el tramo de PRUEBA, modelo A)")
filas_u = []
for u in [0.30, 0.40, 0.45, 0.50, 0.55, 0.60, 0.70]:
    flag = p_te_A >= u
    if flag.sum() == 0:
        continue
    vp, fp, fn = (flag & (yte == 1)).sum(), (flag & (yte == 0)).sum(), (~flag & (yte == 1)).sum()
    filas_u.append({"umbral": u, "pct_marcados": round(100 * flag.mean(), 1),
                     "precision_%": round(100 * vp / flag.sum(), 1), "recall_%": round(100 * vp / yte.sum(), 1),
                     "falsas_alarmas": int(fp), "aciertos": int(vp), "se_escapan": int(fn)})
umbrales = pd.DataFrame(filas_u)
print(umbrales.to_string(index=False))
umbrales.to_csv(TABLAS / "modelo_espera_umbrales_prueba.csv", index=False)
print("\nguardado: resultados/tablas/modelo_espera_umbrales_prueba.csv")
print("\nCON ESTO SE CIERRA EL PASO 5: no se vuelve a tocar el tramo de prueba en este script.")
