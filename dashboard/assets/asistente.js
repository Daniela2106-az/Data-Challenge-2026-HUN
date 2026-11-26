// dashboard/assets/asistente.js (19-nov-2026, v2): lo que pasa en el navegador con el Asistente de flujo HUN (dashboard/asistente_ui.py)
//  - dibuja la conversacion (Store asis-hist) en el chat pequeno y, si esta en pantalla, en la pagina de inicio: el mosaico de sugerencias al inicio y,
//    despues, cada respuesta como tarjeta (titular, cifras, barras, nota, fuente y preguntas de seguimiento), con el diseno del artifact del equipo
//  - abre y cierra el chat pequeno (boton de la esquina)
//  - «Preguntar sobre esto»: al seleccionar texto aparece el boton; el texto queda citado arriba de la caja
//  - Enter envia (Shift+Enter, otra linea); mientras llega la respuesta se ven la pregunta y tres puntos
//  - un identificador anonimo por navegador (Store asis-uid) para contar las preguntas de cada persona
(function () {
  var MAX_CITA = 1500;
  var esperando = false;
  var IC = {
    reloj: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    tendencia: '<path d="M3 17l6-6 4 4 8-8"/><path d="M15 7h6v6"/>',
    embudo: '<path d="M3 4h18l-7 8v6l-4 2v-8z"/>',
    gente: '<circle cx="9" cy="8" r="3"/><circle cx="17" cy="9" r="2.5"/><path d="M3 20c0-3.5 2.7-6 6-6s6 2.5 6 6M15 14.5c3 0 6 1.5 6 5.5"/>',
    sol: '<circle cx="12" cy="12" r="4"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M5 5l2 2M17 17l2 2M5 19l2-2M17 7l2-2"/>',
    cama: '<path d="M3 19V6M3 15h18v4M21 15v-2a3 3 0 00-3-3h-7v5"/><circle cx="7" cy="11.5" r="1.5"/>',
    calendario: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/>',
    frasco: '<path d="M9 3h6M10 3v6l-5 9a2 2 0 002 3h10a2 2 0 002-3l-5-9V3"/>',
    campana: '<path d="M6 16v-5a6 6 0 0112 0v5l2 2H4zM10 21h4"/>',
    grafico: '<path d="M3 3v18h18"/><path d="M7 15l4-5 3 3 5-6"/>',
    persona: '<circle cx="12" cy="8" r="4"/><path d="M4 21c0-4 3.6-7 8-7s8 3 8 7"/>',
    alerta: '<path d="M12 3l10 18H2z"/><path d="M12 10v5M12 18v.01"/>',
    archivo: '<path d="M6 3h9l4 4v14H6zM14 3v5h5"/>',
    enviar: '<path d="M5 12h14M13 6l6 6-6 6"/>',
    pulso: '<path d="M3 12h4l2.5-6 4 12 2.5-6H21"/>',
    chat: '<path d="M4 5h16v11H9l-5 4z"/>',
    ojo: '<path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
    hospital: '<rect x="4" y="3" width="16" height="18" rx="2"/><path d="M12 8v6M9 11h6M10 21v-4h4v4"/>'
  };
  var TONO = {malo: 'mal', bueno: 'bien'};

  function $(id) { return document.getElementById(id); }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]; }); }
  function set(id, props) { try { window.dash_clientside.set_props(id, props); } catch (e) {} }
  function ico(n, c) { return '<svg class="asis-i ' + (c || '') + '" viewBox="0 0 24 24" aria-hidden="true">' + (IC[n] || IC.pulso) + '</svg>'; }

  // Markdown minimo (negritas, cursivas, codigo, listas y parrafos) sobre texto ya escapado
  function md(texto) {
    var lineas = esc(texto).split('\n'), html = '', lista = null;
    function inline(s) {
      return s.replace(/`([^`]+)`/g, '<code>$1</code>').replace(/\*\*([^*]+)\*\*/g, '<b>$1</b>').replace(/(^|[^*])\*([^*\s][^*]*)\*/g, '$1<i>$2</i>');
    }
    function cerrar() { if (lista) { html += '</' + lista + '>'; lista = null; } }
    lineas.forEach(function (l) {
      var ul = l.match(/^\s*[-*•]\s+(.*)$/), ol = l.match(/^\s*\d+[.)]\s+(.*)$/), h = l.match(/^#{1,4}\s+(.*)$/);
      if (ul || ol) {
        var tipo = ul ? 'ul' : 'ol';
        if (lista !== tipo) { cerrar(); html += '<' + tipo + '>'; lista = tipo; }
        html += '<li>' + inline((ul || ol)[1]) + '</li>';
      } else if (h) { cerrar(); html += '<p><b>' + inline(h[1]) + '</b></p>'; }
      else if (!l.trim()) { cerrar(); }
      else { cerrar(); html += '<p>' + inline(l) + '</p>'; }
    });
    cerrar();
    return html;
  }

  function sugerencias() {
    try { return JSON.parse(($('asis-raiz') || {getAttribute: function () { return '[]'; }}).getAttribute('data-sug') || '[]'); } catch (e) { return []; }
  }
  function disponible() { var r = $('asis-raiz'); return !r || r.getAttribute('data-ok') === '1'; }
  function motivo() { var r = $('asis-raiz'); return r ? r.getAttribute('data-motivo') : ''; }

  // Panel «Explorar el dashboard»: abierto mientras no hay conversacion y plegado a una linea cuando la hay. Solo se pliega solo al empezar a conversar:
  // si despues el usuario lo abre, se queda abierto.
  var explorarHabiaConversacion = null;
  function fijarExplorar(abierto) {
    var b = $('asis-explorar-b'), c = $('asis-explorar-c'); if (!b || !c) { return; }
    b.setAttribute('aria-expanded', String(abierto)); c.hidden = !abierto;
  }
  function plegarExplorar(hayConversacion) {
    if (explorarHabiaConversacion === hayConversacion) { return; }
    explorarHabiaConversacion = hayConversacion; fijarExplorar(!hayConversacion);
  }

  function paginasDash() {
    try { return JSON.parse(($('asis-raiz') || {getAttribute: function () { return '{}'; }}).getAttribute('data-pags') || '{}'); } catch (e) { return {}; }
  }

  function chips(qs) {
    return '<div class="asis-seguir">' + qs.map(function (q) {
      return '<button type="button" class="asis-chip" data-q="' + esc(q) + '">' + ico('chat') + esc(q) + '</button>';
    }).join('') + '</div>';
  }

  // titular con el fragmento destacado
  function titular(d) {
    var t = esc(d.titulo), r = esc(d.resaltado || '');
    if (r && t.indexOf(r) >= 0) { t = t.replace(r, '<strong>' + r + '</strong>'); }
    return '<div class="asis-titular"><div class="asis-ic">' + ico(d.icono) + '</div><div>' + t + '</div></div>';
  }

  function respuesta(d) {
    if (d.error) { return '<div class="asis-vacio">' + ico('alerta') + '<span>' + esc(d.texto) + '</span></div>'; }
    var h = d.titulo ? titular(d) : '';
    if (d.tarjetas && d.tarjetas.length) {
      h += '<div class="asis-cifras">' + d.tarjetas.map(function (c) {
        return '<div class="asis-cifra ' + (TONO[c.tono] || '') + '"><span class="asis-ci">' + ico(c.icono) + '</span><b>' + esc(c.valor) + '</b><span>' + esc(c.etiqueta) + '</span></div>';
      }).join('') + '</div>';
    }
    if (d.barras && d.barras.length) {
      var max = Math.max.apply(null, d.barras.map(function (b) { return b.valor; })) || 1;
      h += '<div class="asis-barras" role="img" aria-label="' + esc(d.barras_titulo) + '">' + (d.barras_titulo ? '<h4>' + ico('grafico') + esc(d.barras_titulo) + '</h4>' : '') +
        d.barras.map(function (b) {
          return '<div class="asis-barra"><span>' + esc(b.etiqueta) + '</span><i><em class="' + (TONO[b.tono] || '') + '" style="width:' + Math.max(2, 100 * b.valor / max).toFixed(1) + '%"></em></i><span>' + esc(b.texto) + '</span></div>';
        }).join('') + '</div>';
    }
    if (d.texto) { h += '<div class="asis-texto">' + md(d.texto) + '</div>'; }
    if (d.nota) { h += '<div class="asis-nota-resp">' + ico('alerta') + esc(d.nota) + '</div>'; }
    if (d.paginas && d.paginas.length) {                       // las paginas del dashboard donde se ve lo respondido (se abren sin recargar)
      var nombres = paginasDash();
      h += '<div class="asis-paginas"><span class="asis-paginas__rotulo">Velo en el dashboard</span>' + d.paginas.filter(function (r) { return nombres[r]; }).map(function (r) {
        return '<a class="asis-pagina-link" href="' + esc(r) + '">' + ico('grafico') + esc(nombres[r]) + '<span aria-hidden="true">→</span></a>';
      }).join('') + '</div>';
    }
    if (d.seguimiento && d.seguimiento.length) { h += chips(d.seguimiento); }
    return h;
  }

  function burbuja(t) {
    if (t.rol === 'usuario') {
      return '<div class="asis-msg asis-msg--usuario"><div class="asis-burbuja">' + (t.cita ? '<div class="asis-msg__cita">' + esc(t.cita) + '</div>' : '') + esc(t.texto) + '</div></div>';
    }
    return '<div class="asis-msg asis-msg--bot"><div class="asis-avatar">' + ico('pulso') + '</div><div class="asis-burbuja">' + respuesta(t.datos || {error: true, texto: ''}) + '</div></div>';
  }

  function bienvenida(mini) {
    var sug = sugerencias(), ok = disponible();
    if (mini) {
      return '<div class="asis-bienvenida asis-bienvenida--mini"><p>Pregunta lo que quieras sobre el análisis del flujo de pacientes del HUN.</p>' +
        (ok ? chips(sug.slice(0, 4).map(function (s) { return s[1]; })) : '<p class="asis-aviso-no">' + esc(motivo()) + '</p>') + '</div>';
    }
    return '<section class="asis-bienvenida"><div class="asis-hero">' + ico('hospital') + '</div><h1>¿Qué quieres saber del flujo de pacientes?</h1>' +
      (ok ? '' : '<p class="asis-aviso-no">' + esc(motivo()) + '</p>') +
      '<div class="asis-mosaico">' + sug.slice(0, 6).map(function (s) {
        return '<button type="button" class="asis-tile" data-q="' + esc(s[1]) + '"' + (ok ? '' : ' disabled') + '><div class="asis-ic">' + ico(s[0]) + '</div><span>' + esc(s[1]) + '</span></button>';
      }).join('') + '</div></section>';
  }

  var PENSANDO = '<div class="asis-msg asis-msg--bot asis-msg--pensando"><div class="asis-avatar">' + ico('pulso') + '</div><div class="asis-burbuja"><div class="asis-escribiendo"><i></i><i></i><i></i></div></div></div>';
  // 26-nov-2026: la diapositiva del asistente en /presentacion pinta sus respuestas guardadas con este mismo diseno
  window.asisBurbuja = burbuja;
  window.asisPensando = PENSANDO;

  window.asisPintar = function (hist, cita, quedan) {
    esperando = false;
    plegarExplorar(hist.length > 0);
    ['asis-log', 'asis-log-mini'].forEach(function (id) {
      var el = $(id); if (!el) { return; }
      el.innerHTML = hist.length ? hist.map(burbuja).join('') : bienvenida(id === 'asis-log-mini');
      if (hist.length) { el.scrollTop = el.scrollHeight; if (id === 'asis-log') { window.scrollTo({top: document.documentElement.scrollHeight, behavior: 'smooth'}); } }
    });
    var c = $('asis-cita-mini');
    if (c) {
      c.innerHTML = cita ? '<span class="asis-cita__texto">' + esc(cita) + '</span><button type="button" class="asis-cita__quitar" title="Quitar">✕</button>' : '';
      c.style.display = cita ? 'flex' : 'none';
    }
    if (quedan !== null && quedan !== undefined) {
      var txt = quedan + (quedan === 1 ? ' pregunta' : ' preguntas') + ' más hoy';
      var m = $('asis-restan-mini'); if (m) { m.textContent = txt; }
    }
    document.querySelectorAll('.asis-enviar, .asis-tile, .asis-chip').forEach(function (b) { b.classList.remove('is-esperando'); });
  };

  // mientras llega la respuesta: la pregunta y tres puntos
  function pendiente(texto, cita) {
    var html = burbuja({rol: 'usuario', texto: texto, cita: cita}) + PENSANDO;
    ['asis-log', 'asis-log-mini'].forEach(function (id) {
      var el = $(id); if (!el) { return; }
      var v = el.querySelector('.asis-bienvenida'); if (v) { v.remove(); }
      plegarExplorar(true);
      el.insertAdjacentHTML('beforeend', html); el.scrollTop = el.scrollHeight;
      if (id === 'asis-log') { window.scrollTo({top: document.documentElement.scrollHeight, behavior: 'smooth'}); }
    });
    document.querySelectorAll('.asis-enviar').forEach(function (b) { b.classList.add('is-esperando'); });
    esperando = true;
    clearTimeout(window._asisReloj);
    window._asisReloj = setTimeout(function () {          // si el servidor no responde, no deja la conversacion bloqueada
      if (esperando && window._asisUltimo) { window.asisPintar.apply(null, window._asisUltimo); }
      esperando = false;
    }, 120000);
  }

  // vacia una caja de texto de Dash (hay que usar el setter nativo y avisar con un evento 'input' para que React se entere)
  function limpiar(el) {
    if (!el) { return; }
    Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set.call(el, '');
    el.dispatchEvent(new Event('input', {bubbles: true}));
    el.style.height = 'auto';
  }

  function abrir(si) {
    var p = $('asis-panel'), f = $('asis-fab'); if (!p) { return; }
    p.classList.toggle('is-abierto', si); p.setAttribute('aria-hidden', si ? 'false' : 'true');
    if (f) { f.classList.toggle('is-abierto', si); }
    if (si) { setTimeout(function () { var i = $('asis-input-mini'); if (i) { i.focus(); } var l = $('asis-log-mini'); if (l) { l.scrollTop = l.scrollHeight; } }, 60); }
  }

  document.addEventListener('click', function (e) {
    var t = e.target;
    if (t.closest('#asis-fab')) { abrir(!$('asis-panel').classList.contains('is-abierto')); return; }
    if (t.closest('#asis-cerrar')) { abrir(false); return; }
    if (t.closest('.asis-cita__quitar')) { set('asis-cita', {data: null}); return; }
    if (t.closest('#asis-sel')) {
      var txt = window._asisSeleccion || '';
      ocultarSel();
      if (txt) { set('asis-cita', {data: txt.slice(0, MAX_CITA)}); abrir(true); }
      return;
    }
    var xb = t.closest('#asis-explorar-b');
    if (xb) { fijarExplorar(xb.getAttribute('aria-expanded') !== 'true'); return; }
    var enl = t.closest('.asis-pagina-link');
    if (enl) {                                               // abre la pagina del dashboard sin recargar (Dash escucha popstate)
      e.preventDefault();
      history.pushState({}, '', enl.getAttribute('href')); window.dispatchEvent(new PopStateEvent('popstate'));
      abrir(false); return;
    }
    if (t.closest('#asis-globo-x')) { ocultarGlobo(); return; }
    if (t.closest('#asis-globo')) { ocultarGlobo(); abrir(true); return; }
    // sugerencia o pregunta de seguimiento
    var q = t.closest('.asis-tile, .asis-chip');
    if (q) {
      if (esperando || q.disabled) { return; }
      var pregunta = q.getAttribute('data-q');
      pendiente(pregunta, null);
      set('asis-directa', {data: {q: pregunta, cita: null, n: Date.now()}});
      return;
    }
    var b = t.closest('#asis-enviar, #asis-enviar-mini');
    if (b) {
      if (esperando || b.disabled) { e.preventDefault(); e.stopPropagation(); return; }
      var mini = b.id === 'asis-enviar-mini';
      var texto = (($(mini ? 'asis-input-mini' : 'asis-input') || {}).value || '');
      if (!texto.trim()) { e.preventDefault(); e.stopPropagation(); return; }
      var citaEl = mini ? document.querySelector('#asis-cita-mini .asis-cita__texto') : null, cita = citaEl ? citaEl.textContent : null;
      e.preventDefault(); e.stopPropagation();
      // La pregunta sale por el mismo Store que las sugerencias (asis-directa): asi la caja se vacia aqui mismo y no depende de que Dash devuelva el valor.
      limpiar($(mini ? 'asis-input-mini' : 'asis-input'));
      if (cita) { set('asis-cita', {data: null}); }
      pendiente(texto.trim(), cita);
      set('asis-directa', {data: {q: texto.trim(), cita: cita, n: Date.now()}});
    }
  }, true);

  // Enter envia; Shift+Enter hace otra linea. La caja crece con el texto.
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && $('asis-panel') && $('asis-panel').classList.contains('is-abierto')) { abrir(false); return; }
    if (e.key !== 'Enter' || e.shiftKey || e.isComposing) { return; }
    var id = e.target && e.target.id;
    if (id === 'asis-input' || id === 'asis-input-mini') {
      e.preventDefault();
      var b = $(id === 'asis-input' ? 'asis-enviar' : 'asis-enviar-mini'); if (b) { b.click(); }
    }
  });
  document.addEventListener('input', function (e) {
    var el = e.target;
    if (el && (el.id === 'asis-input' || el.id === 'asis-input-mini')) { el.style.height = 'auto'; el.style.height = Math.min(el.scrollHeight, 140) + 'px'; }
  });

  // «Preguntar sobre esto»: boton flotante sobre el texto seleccionado (fuera del propio chat)
  function ocultarSel() { var s = $('asis-sel'); if (s) { s.classList.remove('is-visible'); } }
  document.addEventListener('mouseup', function (e) {
    if (e.target.closest && e.target.closest('#asis-sel')) { return; }
    setTimeout(function () {
      var s = $('asis-sel'), sel = window.getSelection();
      if (!s || !disponible() || !sel || sel.isCollapsed) { ocultarSel(); return; }
      var txt = sel.toString().replace(/\s+/g, ' ').trim();
      var nodo = sel.anchorNode && (sel.anchorNode.nodeType === 1 ? sel.anchorNode : sel.anchorNode.parentElement);
      if (txt.length < 3 || (nodo && nodo.closest && nodo.closest('#asis-panel, .asis-pagina, input, textarea'))) { ocultarSel(); return; }
      var r = sel.getRangeAt(0).getBoundingClientRect();
      window._asisSeleccion = txt;
      s.style.left = Math.max(8, Math.min(window.innerWidth - 190, r.left + r.width / 2 - 85)) + 'px';
      s.style.top = Math.max(8, r.top - 44) + 'px';
      s.classList.add('is-visible');
    }, 10);
  });
  document.addEventListener('scroll', ocultarSel, true);

  // identificador anonimo del navegador (para el limite de preguntas por persona)
  function uid() {
    var k = 'asis-uid-v1', v = null;
    try { v = localStorage.getItem(k); if (!v) { v = Math.random().toString(36).slice(2) + Date.now().toString(36); localStorage.setItem(k, v); } } catch (e) { v = 'sin-almacenamiento'; }
    set('asis-uid', {data: v});
  }
  var intentos = 0;
  (function esperarDash() {
    if (window.dash_clientside && window.dash_clientside.set_props && $('asis-raiz')) { uid(); return; }
    if (intentos++ < 100) { setTimeout(esperarDash, 100); }
  })();

  // Letrero junto al boton de la esquina: aparece unos segundos cada vez que se cambia de pagina (menos en el inicio, que ya es el asistente)
  var rutaGlobo = location.pathname, relojGlobo = null;
  function ocultarGlobo() { var g = $('asis-globo'); if (g) { g.classList.remove('is-visible'); } clearTimeout(relojGlobo); }
  function mostrarGlobo() {
    var g = $('asis-globo'), p = $('asis-panel');
    if (!g || !disponible() || location.pathname === '/' || (p && p.classList.contains('is-abierto'))) { return; }
    g.classList.add('is-visible'); clearTimeout(relojGlobo); relojGlobo = setTimeout(ocultarGlobo, 7000);
  }
  setInterval(function () {
    if (location.pathname !== rutaGlobo) { rutaGlobo = location.pathname; ocultarGlobo(); setTimeout(mostrarGlobo, 900); }
  }, 250);
  setTimeout(mostrarGlobo, 2500);                            // tambien al entrar directo a una pagina distinta del inicio

  var pintarOriginal = window.asisPintar;
  window.asisPintar = function (hist, cita, quedan) { window._asisUltimo = [hist, cita, quedan]; pintarOriginal(hist, cita, quedan); };

  // iconos de los botones y encabezados (los pone el servidor vacios), el boton de la esquina en el inicio y el contenido de /preguntas al llegar
  setInterval(function () {
    document.querySelectorAll('.asis-i-slot:empty').forEach(function (el) { el.innerHTML = ico(el.getAttribute('data-ico')); });
    var f = $('asis-fab');
    var enPagina = location.pathname === '/';                // la pagina de inicio ES el asistente
    ['paso-nav', 'doc-rel'].forEach(function (id) { var n = $(id); if (n) { n.style.display = enPagina ? 'none' : ''; } });   // el chat no lleva «anterior / siguiente»
    if (f) {
      f.style.display = enPagina ? 'none' : '';
      if (enPagina && $('asis-panel') && $('asis-panel').classList.contains('is-abierto')) { abrir(false); }
    }
    var log = $('asis-log');
    if (log && !log.getAttribute('data-pintado')) {                       // se llego al inicio: pinta lo que ya hay (o el mosaico)
      log.setAttribute('data-pintado', '1'); explorarHabiaConversacion = null;           // la pagina se acaba de montar: el panel se acomoda segun haya o no conversacion
      window.asisPintar.apply(null, window._asisUltimo || [[], null, null]);
    }
    var mini = $('asis-log-mini');
    if (mini && !mini.getAttribute('data-pintado')) { mini.setAttribute('data-pintado', '1'); window.asisPintar.apply(null, window._asisUltimo || [[], null, null]); }
  }, 300);
})();
