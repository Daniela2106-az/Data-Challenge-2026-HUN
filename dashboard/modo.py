"""
dashboard/modo.py  -  modo ligero para servidores pequenos (20-nov-2026)
Render (plan gratuito) da una fraccion de un procesador y 512 MB: las simulaciones que en un computador tardan 3 s alli pasan de los minutos, el servidor
(un solo trabajador) deja todo lo demas en cola y el navegador se queda esperando. En modo ligero las simulaciones interactivas usan menos repeticiones
(la banda del 10-90 % se ve igual, solo un poco mas ruidosa) y las paginas mandan al navegador solo lo que dibujan.
Se activa solo cuando existe la variable RENDER (la pone Render) o cuando se define HUN_LIGERO=1; HUN_LIGERO=0 lo apaga. La cifra oficial (1.000
repeticiones) no cambia: sale de los scripts de src/, no de las paginas.
"""
import os

LIGERO = (os.environ.get("HUN_LIGERO") == "1") or (bool(os.environ.get("RENDER")) and os.environ.get("HUN_LIGERO") != "0")


def repeticiones(n):
    """Repeticiones de una simulacion interactiva: un tercio (minimo 60) en modo ligero."""
    return max(60, n // 3) if LIGERO else n
