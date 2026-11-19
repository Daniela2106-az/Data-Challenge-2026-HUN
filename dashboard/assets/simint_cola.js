// dashboard/assets/simint_cola.js (19-nov-2026)
// Cola de alertas del simulador: las alertas que coinciden en el mismo paso se muestran una despues de otra.
// Cada vez que el usuario pulsa Continuar o Aplicar mejora, pide la siguiente con window.simintSiguienteAlerta().
// Devuelve el JSON de la alerta (la misma forma que usa pages/simulador.py) o null si no quedan pendientes.
window.simintSiguienteAlerta = function () {
  var cola = window._simintCola || [];
  if (!cola.length) { return null; }
  var it = cola.shift();
  var a = it.a;
  var hist = window._simintHist = window._simintHist || [];
  var ob = {tipo: a.tipo, gravedad: a.gravedad, titulo: a.titulo, texto: a.texto, fecha: it.fecha, acciones: a.acciones,
            palancas: a.palancas, mejora: a.mejora, rec: a.rec, alerta: a.alerta, pausada: true};
  hist.push(ob);
  window._simintVista = hist.length - 1;
  return JSON.stringify(Object.assign({}, ob, {pos: hist.length + ' de ' + hist.length, ultima: true}));
};

// Reanudar (19-nov-2026): hay una corrida a medias (el cursor esta dentro de la serie), es la misma serie que se vio y los
// controles siguen como estaban; entonces Reproducir sigue desde ese dia y no vuelve a simular desde el dia 1.
// `valores` = [llegadas, estancia, espera, recorte, adelanto, estres] (los sliders); `plazo` = el horizonte elegido.
window.simintReanudable = function (datos, cursor, valores, plazo) {
  if (!datos || datos.es_horario || typeof cursor !== 'number' || !datos.controles || !datos.fechas) { return false; }
  var n = datos.fechas.length;
  if (Number(plazo) !== n || cursor < 0 || cursor >= n - 1) { return false; }
  var nombres = ['llegadas', 'estancia', 'espera', 'recorte', 'adelanto', 'estres'];
  for (var i = 0; i < nombres.length; i++) {
    if ((datos.controles[nombres[i]] || 0) !== (valores[i] || 0)) { return false; }
  }
  return true;
};
