"""
generar_borrador_mapeo_dx.py  -  version 1 (26-oct-2026)
Tarea A3: agrupa los diagnosticos (nombres SNOMED en ingles) en categorias clinicas simples.

QUE HACE
  Aplica reglas por palabras clave EN ORDEN (la primera que coincide gana) a cada diagnostico de resultados/tablas/dx_frecuencias.csv
  y escribe datos/referencia/mapeo_dx.csv (dx_nombre, categoria_dx, regla). preparar_variables.py solo lee las dos primeras columnas.
  Es un BORRADOR por reglas: un diagnostico sin regla queda en "Otros / sin clasificar". Las correcciones a mano van en
  datos/referencia/mapeo_dx_correcciones.csv (dx_nombre, categoria_dx) y GANAN sobre las reglas.

ENTRADAS  resultados/tablas/dx_frecuencias.csv, datos/referencia/mapeo_dx_correcciones.csv (opcional)
SALIDAS   datos/referencia/mapeo_dx.csv   (se sube a git: no tiene datos de pacientes)

OJO AL LEER
  - La categoria es por palabras del nombre, no por jerarquia SNOMED (no tenemos concept_ancestor). Revisar con alguien del area de salud.
  - "Dolor/sintomas" agrupa diagnosticos que son solo un sintoma (dolor abdominal, fiebre...): no dicen la causa.
"""
import re
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
REF = RAIZ / "datos" / "referencia"
REF.mkdir(parents=True, exist_ok=True)

# (categoria, patron) en orden de prioridad
REGLAS = [
    # reglas de prioridad alta: casos que las reglas generales clasificarian mal
    ("Trauma y lesiones", r"^(open wound|multiple open|contusion|fracture|superficial injur|injury|multiple superficial|multiple injur)"),
    ("Cancer y tumores", r"malignant|neoplasm|neoplastic|carcinoma|lymphoma|leukemia|tumou?r|cancer|sarcoma|metasta"),
    ("Sangre e inmunologia", r"anemia|hemoglobin|thrombocyt|purpura|lupus|allergic disposition|coagul"),
    ("Ojo, oido, boca y dientes", r"tooth|teeth|dental|periapical|pulp|pain (of|in) (ear|eye)"),
    ("Digestivo", r"hemorrhoid|food poisoning"),
    ("Renal y urinario", r"kidney injury|renal failure|genital herpes"),
    ("Respiratorio", r"tubercul|sleep apnea"),
    ("Infecciosas", r"herpes|meningitis"),
    ("Embarazo, parto y ginecologia", r"pregnan|gestation|labor|miscarriage|obstetric|delivery|puerper|fetal|fetus|amniotic|membranes|eclampsia|"
        r"hyperemesis|abortive|maternal|contracted pelvis|uterine scar|postpartum|cesarean|ectopic|vaginitis|vulvo|vaginal|pelvic inflammatory|"
        r"pelvic and perineal|dysmenorrhea|menstrua|menorrhagia|uterine|leiomyoma|ovar|cervic(?!obrachial)|breast|lactation|contracepti|"
        r"genitourinary tract hemorrhage|bartholin|endometri|vaginal discharge|female"),
    ("Trauma y lesiones", r"contusion|fracture|wound|injur|sprain|dislocation|amputation|burn|laceration|foreign body|bite|abrasion|crush|"
        r"strain of|rupture of (tendon|ligament)|physical aggression|sexual abuse|assault|poisoning|intoxication|overdose|accidental|"
        r"traumatic|concussion|hematoma|bruise|derangement of knee|adverse reaction"),
    ("Cancer y tumores", r"malignant|neoplasm|carcinoma|lymphoma|leukemia|tumou?r|cancer|sarcoma|metasta"),
    ("Salud mental", r"anxiety|depress|bipolar|schizophren|psychosis|psychotic|psychosocial|mental|behavio|dementia|alzheimer|eating disorder|"
        r"autis|attention deficit|sleep|insomnia|suicid|panic|personality|stimulant|alcohol|substance|drug (abuse|dependence)|neurocognitive|"
        r"psychotherapy|emotional|counseling|mood|delirium|agitation"),
    ("Cardiovascular", r"heart|cardiac|cardio|myocard|angina|infarct|arrhythm|tachycardia|atrial|ventricular|hypertension|hypotension|"
        r"blood.pressure|vein|venous|varicose|thrombo|embol|aort|arter|vascular|syncope|palpitation|preinfarction|hemorrhoid|edema|aneurysm|"
        r"cerebrovascular|stroke|ischemi"),
    ("Neurologico", r"headache|migraine|seizure|epilep|convulsion|vertigo|dizziness|neuropath|neuralg|palsy|parkinson|brain|cerebr|"
        r"intracranial|nerve|meningitis|encephal|polyneuro|carpal tunnel|neurolog|syncope|tremor|paralysis|subarachnoid|speech and language"),
    ("Respiratorio", r"respirat|pneumon|bronch|asthma|lung|pulmonary(?! embol)|cough|dyspnea|copd|chronic obstructive|pleur|sinusitis|"
        r"pharyng|tonsill|laryng|rhinitis|common cold|influenza|nasal|nose|epistaxis|tuberculosis|hemoptysis|apnea|croup|hypox|wheez|upper airway"),
    ("Digestivo", r"intestin|gastro|abdom|bowel|colon|appendic|hernia|cholecyst|biliary|gallbladder|bile|liver|cirrhosis|hepat|pancrea|"
        r"dyspepsia|gastritis|diarrhea|vomiting|nausea|constipation|rectal|anal|diverticul|ulcer of (stomach|duoden)|esophag|reflux|"
        r"dysphagia|ascites|jaundice|colic(?! renal)|impaction|obstruction|peritonitis|stomach|digestive|fecal|hemorrhoid|ileus"),
    ("Renal y urinario", r"renal|kidney|urin|ureter|bladder|cystitis|nephr|pyelo|calculus of (kidney|ureter|urinary)|urolith|prostat|testis|"
        r"testic|epididym|penis|penile|genital|scrot|circumcis|hematuria|blood in urine|retention of urine|dysuria|incontinence"),
    ("Infecciosas", r"infect|dengue|sepsis|septic|viral|virus|bacterial|fever|herpes|zoster|malaria|hiv|immunodeficiency|covid|sars|"
        r"chikungunya|zika|syphilis|hepatitis|mycosis|candid|scabies|infestation|parasit|typhoid|leptospir|varicella|measles|mumps|abscess"),
    ("Piel y tejidos blandos", r"cellulitis|skin|dermat|urticaria|eczema|rash|erysipelas|abscess|boil|furuncle|pruritus|psoriasis|acne|"
        r"subcutaneous|ulcer of lower|cutaneous|nail|scalp|alopecia|wart|cyst|lipoma|pressure ulcer|decubitus"),
    ("Musculoesqueletico y dolor", r"back|lumbago|sciatica|neck pain|pain in|pain of|joint|arthr|osteo|tendin|bursitis|myalgia|muscle|"
        r"rotator cuff|epicondylitis|disc|spondyl|rheumat|lupus|gout|tietze|limb|shoulder|knee|hip|ankle|foot|hand|wrist|elbow|fibromyalgia|"
        r"temporomandibular|torticollis|contracture|soft tissue|cervicobrachial"),
    ("Endocrino y metabolico", r"diabet|glyc|thyroid|hypothyroid|hyperthyroid|obesity|malnutrition|dehydration|electrolyte|fluid|hyponatr|"
        r"hypernatr|hyperkal|hypokal|acidosis|ketoacidosis|vitamin|anemia(?! due)|weight|metabolic|dyslipid|cholesterol|hyperlipid|"
        r"adrenal|pituitary|hormone|hemoglobin|sickle"),
    ("Ojo, oido, boca y dientes", r"otitis|ear|hearing|eye|conjunctiv|vision|visual|cataract|glaucoma|dental|tooth|teeth|caries|pulpitis|"
        r"periodont|periapical|gingiv|oral|mouth|gum|malocclusion|stomatitis|pharyngitis|corneal|retin|eyelid"),
    ("Dolor y sintomas generales", r"pain|ache|malaise|fatigue|weakness|chest|fever|general examination|health care|follow-up|examination|"
        r"finding|state|symptom|disposition|screening|vaccin|immuniz|procedure|attention to|status|encounter|observation|administrat"),
    ("Sangre e inmunologia", r"anemia|thrombocyt|coagul|bleeding|hemorrhagic|leukocyt|neutropenia|allerg|anaphyla|immun|lymph"),
]
# segundo nivel: solo se usa si nada de lo anterior coincidio (diagnosticos poco frecuentes)
REGLAS_2 = [
    ("Recien nacido", r"prematur|newborn|birth|tongue tie|neonat|infant"),
    ("Salud mental", r"conduct|adjustment|obsessive|phobic|intellectual|dissociative|delusional|scholastic|avoidant|expressive language|"
        r"childhood disorder|delayed milestone|somnolence|personality|tic disorder"),
    ("Digestivo", r"hematemesis|melena|dysentery|cholangitis|rectum|anus|rectal|peritone|enteritis|colitis|hepatic|biliary"),
    ("Cardiovascular", r"bradycardia|shock|cyanosis|circulat|hypovolem"),
    ("Piel y tejidos blandos", r"keratosis|impetigo|tinea|lichen|verruca|hidradenitis|vitiligo|scar|pemphigus|chloasma|exanthema|"
        r"swelling|lipodystrophy|hair|nevus|mole\b|wart"),
    ("Musculoesqueletico y dolor", r"synovitis|spur|triggering|scoliosis|pes planus|bone|tendonitis|fasciitis|gait|spinal|metatarsalgia|"
        r"ligament|myositis|deformity|bursa|cartilage|sclerosis of (bone|joint)"),
    ("Renal y urinario", r"varicocele|balanitis|urethr|hydrocele|phimosis"),
    ("Embarazo, parto y ginecologia", r"amenorrhea|oligohydramnios|hydatidiform|puberty|menopaus|hysterectomy|cervix|placent|polyhydramnios"),
    ("Ojo, oido, boca y dientes", r"cerumen|labyrinth|astigmatism|ptosis|blephar|dysphonia|adenoid|tinnitus|myopia|hyperopia|strabismus|ocular|lip"),
    ("Neurologico", r"dystonia|motor neuron|multiple sclerosis|hydrocephalus|amnesia|myoclonus|neuro|ataxia|spasm"),
    ("Infecciosas", r"toxoplasm|amoeb|amebic|mycobacter|parasit|fungal|helminth"),
    ("Endocrino y metabolico", r"undernutrition|lipid|lipoid|gout|hyperuric|porphyr|amyloid"),
    ("Sangre e inmunologia", r"systemic sclerosis|scleroderma|vasculitis|sarcoidosis"),
    ("Dolor y sintomas generales", r"history of|exposure|neck swelling|abnormal|disorder of"),
]
SIN_REGLA = "Otros / sin clasificar"

dx = pd.read_csv(REF.parent.parent / "resultados" / "tablas" / "dx_frecuencias.csv")
comp = [(c, re.compile(p, re.I)) for c, p in REGLAS]
comp2 = [(c, re.compile(p, re.I)) for c, p in REGLAS_2]


def clasificar(nombre):
    for cat, rx in comp + comp2:
        m = rx.search(nombre)
        if m:
            return cat, m.group(0)
    return SIN_REGLA, ""


res = dx.dx_nombre.map(clasificar)
dx["categoria_dx"] = [r[0] for r in res]
dx["regla"] = [r[1] for r in res]

corr_f = REF / "mapeo_dx_correcciones.csv"
if corr_f.exists():
    c = pd.read_csv(corr_f).drop_duplicates("dx_nombre").set_index("dx_nombre").categoria_dx
    m = dx.dx_nombre.isin(c.index)
    dx.loc[m, "categoria_dx"] = dx.loc[m, "dx_nombre"].map(c)
    dx.loc[m, "regla"] = "correccion manual"
    print(f"correcciones manuales aplicadas: {int(m.sum())}")

dx[["dx_nombre", "categoria_dx", "regla"]].to_csv(REF / "mapeo_dx.csv", index=False)
tot = dx.episodios.sum()
print(f"diagnosticos: {len(dx)} | episodios con diagnostico: {tot}")
print((dx.groupby("categoria_dx").episodios.sum().sort_values(ascending=False) / tot * 100).round(1).to_string())
print(f"sin clasificar entre los 300 mas frecuentes: {(dx.head(300).categoria_dx == SIN_REGLA).sum()}")
