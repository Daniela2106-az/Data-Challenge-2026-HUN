"""
src/grabar_video_presentacion.py  -  graba el video del Simulador integral de la diapositiva 5 de la presentacion

En la final el simulador no corre en vivo (en Render se trababa al recalcular): se reproduce este video de una corrida real hecha en local.
Pasos:
  1. PRES_GRABAR=1 python3 dashboard/main.py          (guarda la corrida en dashboard/presentacion_simulacion.json para la diapositiva 6)
  2. python3 src/grabar_video_presentacion.py         (abre /presentacion?diapo=5&grabar=1 en Chrome sin ventana, pulsa «siguiente»,
                                                       graba hasta que termina y arma dashboard/assets/presentacion_simulador.mp4 y .jpg)
Necesita Google Chrome, ffmpeg, websocket-client y Pillow. Quita los cuadros de ~1 s en que el eje de camas se redibuja de 0 a 140 al terminar.
"""
import json, time, base64, subprocess, urllib.request, sys, os, tempfile
import websocket
ESCALA = 1.3                      # pantalla de grabacion ESCALA veces 1920x1080: el video sale nitido en pantalla grande
S = os.path.join(tempfile.gettempdir(), "grabar_presentacion"); os.makedirs(S, exist_ok=True)
PUERTO = 9333
def arrancar():
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{PUERTO}/json/version", timeout=1)
    except Exception:
        subprocess.Popen(["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "--headless=new", f"--remote-debugging-port={PUERTO}",
                          f"--user-data-dir={S}/chrome-perfil", "--window-size=1920,1080", "--hide-scrollbars", "--no-first-run", "--mute-audio"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(50):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{PUERTO}/json/version", timeout=1); break
            except Exception:
                time.sleep(.2)
class Pestana:
    def __init__(self):
        arrancar()
        req = urllib.request.Request(f"http://127.0.0.1:{PUERTO}/json/new?about:blank", method="PUT")
        info = json.loads(urllib.request.urlopen(req).read())
        self.ws = websocket.create_connection(info["webSocketDebuggerUrl"], timeout=120, suppress_origin=True)
        self.n = 0
        self.cmd("Emulation.setDeviceMetricsOverride", width=int(1920 * ESCALA), height=int(1080 * ESCALA), deviceScaleFactor=1, mobile=False)
    def cmd(self, metodo, **p):
        self.n += 1; i = self.n
        self.ws.send(json.dumps({"id": i, "method": metodo, "params": p}))
        while True:
            m = json.loads(self.ws.recv())
            if m.get("id") == i:
                return m.get("result", m)
    def ir(self, url, espera=6):
        self.cmd("Page.navigate", url=url); time.sleep(espera)
    def js(self, expr):
        r = self.cmd("Runtime.evaluate", expression=expr, returnByValue=True)
        return r.get("result", {}).get("value")
    def tecla(self, key, code=None, kc=0):
        for t in ("keyDown", "keyUp"):
            self.cmd("Input.dispatchKeyEvent", type=t, key=key, code=code or key, windowsVirtualKeyCode=kc)
    def foto(self, nombre):
        r = self.cmd("Page.captureScreenshot", format="png")
        ruta = f"{S}/capturas/{nombre}.png"; os.makedirs(os.path.dirname(ruta), exist_ok=True)
        open(ruta, "wb").write(base64.b64decode(r["data"])); return ruta


OUT = f"{S}/grab"; os.makedirs(OUT, exist_ok=True)
for f in os.listdir(OUT): os.remove(f"{OUT}/{f}")
p = Pestana()
p.ir("http://127.0.0.1:8050/", 3)
p.js("sessionStorage.setItem('intro-hun','1')")
p.ir("http://127.0.0.1:8050/presentacion?diapo=5&grabar=1", 2)
t0 = time.time()
while time.time() - t0 < 120:
    if p.js("(function(){var g=document.getElementById('pres-previa-graf'); var gd=g&&g.querySelector('.js-plotly-plot'); return !!(gd&&gd.data&&gd.data.length) && !!document.getElementById('simint-play')})()"): break
    time.sleep(.5)
p.js("var i=document.getElementById('intro-hun'); if(i){i.remove();} document.documentElement.classList.add('pres-pantalla'); window.dispatchEvent(new Event('resize'));")
time.sleep(5)
caja = p.js("(function(){var r=document.querySelector('.pres-sim-fila .pres-ajustar').getBoundingClientRect(); var h=document.querySelector('.pres-sim-caja').getBoundingClientRect(); return [r.left,r.top,r.width,Math.min(r.height,h.height), h.left, h.width]})()")
print("caja", caja)
x = int(caja[4]); y = int(caja[1]); w = int(caja[5]) // 2 * 2; h = int(caja[3]) // 2 * 2       # la pantalla ya es ESCALA veces mas grande
json.dump(dict(x=x, y=y, w=w, h=h), open(f"{OUT}/caja.json", "w"))
r = p.cmd("Page.captureScreenshot", format="png"); open(f"{OUT}/poster_full.png", "wb").write(base64.b64decode(r["data"]))
# screencast
p.n += 1; p.ws.send(json.dumps({"id": p.n, "method": "Page.startScreencast", "params": {"format": "jpeg", "quality": 92, "everyNthFrame": 1, "maxWidth": int(1920 * ESCALA), "maxHeight": int(1080 * ESCALA)}}))
p.n += 1; p.ws.send(json.dumps({"id": p.n, "method": "Input.dispatchKeyEvent", "params": {"type": "keyDown", "key": "ArrowRight", "code": "ArrowRight", "windowsVirtualKeyCode": 39}}))
p.n += 1; p.ws.send(json.dumps({"id": p.n, "method": "Input.dispatchKeyEvent", "params": {"type": "keyUp", "key": "ArrowRight", "code": "ArrowRight", "windowsVirtualKeyCode": 39}}))
inicio = time.time(); frames = []; fin = None; ultimo_chequeo = 0; chk_id = None
p.ws.settimeout(1)
while True:
    try:
        m = json.loads(p.ws.recv())
    except Exception:
        m = {}
    if m.get("method") == "Page.screencastFrame":
        pr = m["params"]; k = len(frames)
        open(f"{OUT}/f{k:05d}.jpg", "wb").write(base64.b64decode(pr["data"]))
        frames.append(pr["metadata"]["timestamp"])
        p.n += 1; p.ws.send(json.dumps({"id": p.n, "method": "Page.screencastFrameAck", "params": {"sessionId": pr["sessionId"]}}))
    elif chk_id and m.get("id") == chk_id:
        v = m.get("result", {}).get("result", {}).get("value")
        if v and not fin: fin = time.time(); print("termino en", round(fin - inicio, 1), "s")
        chk_id = None
    if time.time() - ultimo_chequeo > 1 and not chk_id:
        ultimo_chequeo = time.time(); p.n += 1; chk_id = p.n
        p.ws.send(json.dumps({"id": chk_id, "method": "Runtime.evaluate", "params": {"expression": "document.querySelectorAll('#pres-sim-ganancia .is-visible').length>0", "returnByValue": True}}))
    if fin and time.time() - fin > 2.5: break
    if time.time() - inicio > 240: print("tiempo agotado"); break
json.dump(frames, open(f"{OUT}/tiempos.json", "w"))
print(len(frames), "cuadros")

# ---- armar el video: recorte de la caja del simulador, sin los cuadros del eje redibujado
import numpy as np
from PIL import Image
t = frames; c = json.load(open(f"{OUT}/caja.json")); n = len(t)
def reg(i):
    return np.asarray(Image.open(f"{OUT}/f{i:05d}.jpg").convert("L").crop((c["x"], c["y"] + int(290 * ESCALA), c["x"] + int(45 * ESCALA), c["y"] + int(540 * ESCALA))), dtype=float)
ref = reg(n - 1)
malos = {i for i in range(n) if t[i] - t[0] > 45 and np.abs(reg(i) - ref).mean() > 4}
keep = [i for i in range(n) if i not in malos]
with open(f"{OUT}/lista.txt", "w") as f:
    for k, i in enumerate(keep):
        d = (t[keep[k + 1]] - t[i]) if k + 1 < len(keep) else 1.0
        if k + 1 < len(keep) and keep[k + 1] - i > 1: d = 0.05
        f.write(f"file 'f{i:05d}.jpg'\nduration {d:.4f}\n")
    f.write(f"file 'f{keep[-1]:05d}.jpg'\n")
ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "dashboard", "assets")
crop = f"crop={c['w']}:{c['h']}:{c['x']}:{c['y']}"
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", f"{OUT}/lista.txt", "-vf", f"{crop},fps=30,format=yuv420p",
                "-c:v", "libx264", "-crf", "20", "-preset", "slow", "-movflags", "+faststart", f"{ASSETS}/presentacion_simulador.mp4"], check=True)
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", f"{OUT}/poster_full.png", "-vf", crop, "-q:v", "3", f"{ASSETS}/presentacion_simulador.jpg"], check=True)
print("listo:", len(keep), "cuadros,", len(malos), "descartados")
