// dashboard/assets/simint_compacto.js (19-nov-2026)
// Alertas comprimidas: al pulsar Continuar o Aplicar mejora, la tarjeta pasa a un chip (punto de color + titulo + metrica + fecha).
// Los chips se acumulan en columnas por gravedad (uno debajo de otro dentro de la misma gravedad), en el lugar de la tarjeta.
// Clic en un chip: se despliega su tarjeta (o, si la alerta ya tenia mejora aplicada, el panel con las tablas de pacientes tal como se vio).
// Cerrar: vuelve a la version comprimida. Los cambios de tamano se acompanan con una transicion de altura.
(function () {
  var comp = new Set();      // alertas comprimidas: siguen listadas siempre (objetos del historial window._simintHist)
  var abierta = null;        // la alerta desplegada desde su chip
  var modo = 'alerta';       // alerta con mejora aplicada: 'alerta' (que paso + recomendacion) o 'listas' (tablas de pacientes); una oculta a la otra
  var captura = null;        // alerta a la que se le aplico la mejora y falta guardar su panel de tablas
  var firma = '';

  function hist() { return window._simintHist || []; }
  function actual() { var h = hist(), i = window._simintVista; return (h.length && typeof i === 'number' && i >= 0) ? h[i] : null; }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]; }); }
  function $(id) { return document.getElementById(id); }

  function revision() {
    var r = $('simint-alerta-rev');
    if (!r) {
      var cols = $('simint-alerta-cols'); if (!cols || !cols.parentNode) { return null; }
      r = document.createElement('div'); r.id = 'simint-alerta-rev'; r.className = 'simint-rev'; r.style.display = 'none';
      var card = $('simint-alerta');
      cols.parentNode.insertBefore(r, card || cols.nextSibling);      // debajo de los componentes comprimidos, en el mismo lugar que la tarjeta
    }
    return r;
  }

  function bloqueVisible() {
    var r = $('simint-alerta-rev'), c = $('simint-alerta');
    if (r && r.style.display !== 'none') { return r; }
    if (c && c.style.display !== 'none') { return c; }
    return null;
  }

  // Transicion de altura: el bloque parte de `desde` px y llega a su alto natural.
  function animar(el, desde) {
    if (!el) { return; }
    var h1 = el.scrollHeight;
    if (Math.abs(h1 - desde) < 2) { return; }
    el.style.transition = 'none'; el.style.overflow = 'hidden'; el.style.minHeight = '0'; el.style.height = desde + 'px';
    void el.offsetHeight;
    el.style.transition = 'height .35s ease'; el.style.height = h1 + 'px';
    setTimeout(function () { el.style.transition = ''; el.style.overflow = ''; el.style.minHeight = ''; el.style.height = ''; }, 380);
  }
  function colapsar(el, fin) {
    if (!el) { fin(); return; }
    var h0 = el.offsetHeight;
    el.style.transition = 'none'; el.style.overflow = 'hidden'; el.style.minHeight = '0'; el.style.height = h0 + 'px';
    void el.offsetHeight;
    el.style.transition = 'height .3s ease, margin .3s ease, padding .3s ease'; el.style.height = '0px'; el.style.paddingTop = '0'; el.style.paddingBottom = '0'; el.style.marginBottom = '0';
    setTimeout(function () {
      fin();
      ['transition', 'overflow', 'minHeight', 'height', 'paddingTop', 'paddingBottom', 'marginBottom'].forEach(function (k) { el.style[k] = ''; });
    }, 320);
  }

  function render() {
    var card = $('simint-alerta'), cols = $('simint-alerta-cols');
    if (!card || !cols) { return; }
    var h = hist();
    comp.forEach(function (o) { if (h.indexOf(o) < 0) { comp.delete(o); } });
    if (abierta && h.indexOf(abierta) < 0) { abierta = null; }
    var cur = actual();
    if (abierta && cur !== abierta) { abierta = null; }          // llego otra alerta: la desplegada vuelve a su chip

    // guardar el panel de tablas de la alerta a la que se le acaba de aplicar la mejora
    var conf = $('simint-confirmacion'), cuerpo = $('simint-confirmacion-cuerpo');
    if (captura && conf && cuerpo && conf.classList.contains('simint-confirmacion--visible') && cuerpo.children.length) {
      captura.panelHTML = cuerpo.innerHTML; captura = null;
    }

    if (cur) {
      var verRev = !!(abierta && abierta.panelHTML && modo === 'listas');
      var verCard = !comp.has(cur) || (abierta === cur && !verRev);
      var r = revision();
      if (r) {
        if (verRev) { var htmlRev = '<div class="simint-rev__barra"><button type="button" id="simint-rev-alerta" class="simint-rev__ver" title="Volver a qué pasó y recomendación" aria-label="Volver a qué pasó y recomendación">←</button><button type="button" id="simint-rev-cerrar" class="simint-alerta__cerrar simint-rev__cerrar" title="Cerrar" aria-label="Cerrar">✕</button></div>' + abierta.panelHTML;
                      if (r.getAttribute('data-k') !== String(h.indexOf(abierta))) { r.innerHTML = htmlRev; r.setAttribute('data-k', String(h.indexOf(abierta))); } }
        r.style.display = verRev ? 'block' : 'none';
      }
      var bl = $('simint-alerta-listas');
      if (bl) { bl.style.display = (abierta === cur && abierta.panelHTML && verCard) ? 'block' : 'none'; }
      if (!verCard) { card.style.display = 'none'; }
      else if (card.style.display === 'none') { card.style.display = 'flex'; }
    }

    var lista = h.filter(function (o) { return comp.has(o); });
    // «sigue activa»: la ultima alerta de cada tipo que se dejo sin corregir y cuya condicion se cumple ahora
    var act = window._simintActivas || {}, vivas = new Set();
    Object.keys(act).forEach(function (tp) {
      for (var k = h.length - 1; k >= 0; k--) { if (h[k].tipo === tp) { if (!h[k].aplicada) { vivas.add(h[k]); } break; } }
    });
    var f = lista.map(function (o) { return h.indexOf(o) + (vivas.has(o) ? '*' : ''); }).join(',') + '|' + (abierta ? h.indexOf(abierta) : '-');
    if (f === firma) { return; }
    firma = f;
    function col(nombre, clase, grav) {
      var its = lista.filter(function (o) { return clase === 'mejora' ? !!o.aplicada : (!o.aplicada && o.gravedad === grav); });
      if (!its.length) { return ''; }
      return '<div class="simint-cols__col"><div class="simint-cols__cab">' + nombre + ' · ' + its.length + '</div>' +
        its.map(function (o) {
          return '<button type="button" class="simint-achip simint-achip--' + (o.aplicada ? 'mejora' : clase) + (o === abierta ? ' simint-achip--abierta' : '') + (vivas.has(o) ? ' simint-achip--viva' : '') + '" data-i="' + h.indexOf(o) + '" title="' + (vivas.has(o) ? 'Sigue activa: no se ha corregido. ' : '') + 'Ver la alerta completa">' +
            '<i class="simint-achip__punto"></i><span class="simint-achip__titulo">' + esc(o.titulo) + '</span>' +
            '<span class="simint-achip__fecha">' + esc(o.fecha) + '</span></button>';
        }).join('') + '</div>';
    }
    cols.innerHTML = lista.length ? col('Críticas', 'alta', 'Alta') + col('Avisos', 'media', 'Media') + col('Con mejora', 'mejora', null) : '';
    cols.style.display = lista.length ? 'flex' : 'none';
    cols.querySelectorAll('.simint-cols__col').forEach(function (c) {
      function estado() {
        c.classList.toggle('simint-cols__col--desborda', c.scrollHeight > c.clientHeight + 1);
        c.classList.toggle('simint-cols__col--fin', c.scrollTop + c.clientHeight >= c.scrollHeight - 2);
      }
      estado();
      c.addEventListener('scroll', estado);
    });
  }

  document.addEventListener('click', function (e) {
    var t = e.target.closest && e.target.closest('#simint-continuar, #simint-aplicar, #simint-alerta-cerrar, #simint-rev-cerrar, #simint-rev-alerta, #simint-alerta-listas, .simint-achip');
    if (!t) { return; }
    var cur = actual(), h = hist();
    if (t.classList.contains('simint-achip')) {
      var o = h[Number(t.getAttribute('data-i'))]; if (!o) { return; }
      var antes = bloqueVisible(), desde = antes ? antes.offsetHeight : 0;
      if (cur && cur !== o && !comp.has(cur)) { comp.add(cur); }     // la que esperaba respuesta queda listada como chip
      if (abierta === o) { cerrar(); return; }
      abierta = o; modo = 'alerta'; window._simintVista = h.indexOf(o);
      window.dash_clientside.set_props('simint-alerta-texto', {children: JSON.stringify(Object.assign({}, o, {pos: (h.indexOf(o) + 1) + ' de ' + h.length, ultima: h.indexOf(o) === h.length - 1}))});
      firma = ''; render();
      var ahora = bloqueVisible(); if (ahora && ahora !== antes) { animar(ahora, desde); }
    } else if (t.id === 'simint-alerta-listas' || t.id === 'simint-rev-alerta') {      // conmutar: una seccion se oculta y la otra aparece
      var b0 = bloqueVisible(), d0 = b0 ? b0.offsetHeight : 0;
      modo = (t.id === 'simint-alerta-listas') ? 'listas' : 'alerta';
      firma = ''; render();
      var b1 = bloqueVisible(); if (b1 && b1 !== b0) { animar(b1, d0); }
    } else if (t.id === 'simint-alerta-cerrar' || t.id === 'simint-rev-cerrar') {
      cerrar();
    } else if (cur) {                                   // Continuar / Aplicar mejora
      comp.add(cur); abierta = null;
      if (t.id === 'simint-aplicar') { captura = cur; cur.aplicada = true; var u = (window._simintUltTipo || {})[cur.tipo]; if (u) { u.mejorada = true; } }
      firma = ''; render();
    }
  }, true);

  function cerrar() {
    var cur = actual(), b = bloqueVisible();
    colapsar(b, function () { if (cur) { comp.add(cur); } abierta = null; firma = ''; render(); });
  }

  // Configuracion: un grupo de sliders se abre o se cierra solo con clic en su encabezado (abre uno a la vez).
  document.addEventListener('click', function (e) {
    var hd = e.target.closest && e.target.closest('.simint-config-group-header');
    if (!hd || e.target.closest('.info-badge, [class*="info"]')) { return; }
    var g = hd.closest('.simint-config-section'); if (!g) { return; }
    var abrir = !g.classList.contains('simint-grupo--abierto');
    document.querySelectorAll('.simint-config-section.simint-grupo--abierto').forEach(function (x) { x.classList.remove('simint-grupo--abierto'); });
    if (abrir) { g.classList.add('simint-grupo--abierto'); }
  });

  new MutationObserver(function () { render(); }).observe(document.documentElement, {subtree: true, childList: true, attributes: true, attributeFilter: ['style', 'class']});
  setInterval(render, 400);
})();
