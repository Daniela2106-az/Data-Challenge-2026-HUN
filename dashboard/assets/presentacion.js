// dashboard/assets/presentacion.js (26-nov-2026): la pagina «Presentación» (dashboard/pages/presentacion.py).
// Mientras se presenta nadie toca el computador: solo se pasa de diapositiva. Todo lo demas ocurre solo:
//   - Siguiente: →, espacio, AvPág, Enter o el clicker. Anterior: ←, RePág o Retroceso. F: pantalla completa. Esc sale de pantalla completa.
//   - Diapositiva con data-auto="secuencia": sus piezas «.pres-frag» aparecen solas, una tras otra; si se pulsa Siguiente antes, aparecen todas.
//   - El lienzo mide 1600 x 900 y se escala para llenar la pantalla sin deformarse.
//   - Diapositiva del simulador (data-auto="simulador"): al entrar queda quieto; la siguiente pulsacion (Siguiente) pulsa «Reproducir»; cuando salta una alerta, la deja ver
//     unos segundos y aplica la mejora (solo la primera vez) o continua; la confirmacion verde tambien se acepta sola. Si se vuelve a ella desde la
//     diapositiva anterior, arranca de nuevo; si se vuelve desde la siguiente, se queda como iba.
//   - Diapositiva del asistente (data-auto="asistente"): escribe las dos preguntas y muestra las respuestas guardadas, con el diseno del asistente.
(function () {
  var ANCHO = 1600, ALTO = 900;
  var LEER_ALERTA = 12000, LEER_OTRA_ALERTA = 250, LEER_CONFIRMACION = 7500;   // la alerta de la mejora y las listas de pacientes se dejan leer       // ms que se deja ver la alerta y el panel verde antes de seguir
  var raizActual = null, estado = null;

  function $(id) { return document.getElementById(id); }
  function diapos() { return raizActual ? Array.prototype.slice.call(raizActual.querySelectorAll('.pres-diapo')) : []; }

  // ------------------------------------------------------------ escala del lienzo y del simulador
  function ajustar() {
    var esc = $('pres-escenario'), lienzo = $('pres-lienzo');
    if (!esc || !lienzo) { return; }
    var s = Math.min(esc.clientWidth / ANCHO, esc.clientHeight / ALTO);
    lienzo.style.transform = 'translate(-50%, -50%) scale(' + s + ')';
    ajustarInternos();
  }
  function ajustarInternos() {
    if (!raizActual) { return; }
    raizActual.querySelectorAll('.pres-ajustar').forEach(function (caja) {
      var hijo = caja.firstElementChild; if (!hijo) { return; }
      var s = Math.min(1, caja.clientWidth / hijo.offsetWidth, caja.clientHeight / Math.max(1, hijo.offsetHeight));
      var t = 'translateX(-50%) scale(' + s.toFixed(3) + ')';
      if (hijo.style.transform !== t) { hijo.style.transform = t; }
    });
  }

  // ------------------------------------------------------------ navegacion
  function mostrar(i) {
    var ds = diapos(); if (!ds.length) { return; }
    i = Math.max(0, Math.min(i, ds.length - 1));
    var desde = estado.i;
    estado.i = i;
    try { sessionStorage.setItem('pres-diapo', String(i)); } catch (e) {}
    ds.forEach(function (d, j) { d.classList.toggle('is-activa', j === i); d.classList.toggle('is-pasada', j < i); });
    var d = ds[i], etapa = d.getAttribute('data-etapa') || '';
    raizActual.querySelectorAll('.pres-etapa').forEach(function (e) {
      var orden = Array.prototype.indexOf.call(e.parentNode.children, e);
      var actual = Array.prototype.map.call(e.parentNode.children, function (x) { return x.getAttribute('data-etapa'); }).indexOf(etapa);
      e.classList.toggle('is-actual', e.getAttribute('data-etapa') === etapa);
      e.classList.toggle('is-hecha', (actual >= 0 && orden < actual) || (!etapa && i > 0));      // en el cierre, todas las etapas quedan hechas
    });
    raizActual.classList.toggle('pres--portada', i === 0);
    raizActual.classList.toggle('pres--cierre', i === ds.length - 1);
    var c = $('pres-contador'); if (c) { c.textContent = i ? (i + ' / ' + (ds.length - 1)) : ''; }
    contar(d);
    var auto = d.getAttribute('data-auto');
    // El simulador no arranca solo (lo arranca la siguiente pulsacion, en siguiente()). Si se sale de el hacia atras, se deja limpio en ese momento,
    // para que al volver no se vea la corrida anterior ni sus notificaciones.
    var dDesde = ds[desde];
    if (dDesde && dDesde.getAttribute('data-auto') === 'simulador' && i < desde && estado.sim) { reiniciarSimulador(); }
    if (auto === 'simulador' && estado.sim && desde === i - 1) { reiniciarSimulador(); }
    if (auto === 'secuencia') { secuencia(d); }
    if (auto === 'asistente') { if (estado.asis && desde === i - 1) { reiniciarAsistente(); } else { arrancarAsistente(); } }
    setTimeout(function () { window.dispatchEvent(new Event('resize')); }, 30);      // las graficas de la diapositiva se ajustan a su caja
  }
  // Cifras que se cuentan solas de 0 a su valor (elementos con data-contar), cada vez que se entra a la diapositiva
  function contar(d) {
    d.querySelectorAll('[data-contar]').forEach(function (el) {
      var fin = parseFloat(el.getAttribute('data-contar')), dec = parseInt(el.getAttribute('data-dec') || '0', 10);
      var pre = el.getAttribute('data-pre') || '', suf = el.getAttribute('data-suf') || '', t0 = null, DUR = 1400;
      function fmt(v) { var s = v.toFixed(dec).replace('.', ','); if (!dec) { s = s.replace(/\B(?=(\d{3})+(?!\d))/g, '.'); } return pre + s + suf; }
      el.textContent = fmt(0);
      function paso(ts) { if (!t0) { t0 = ts; } var x = Math.min(1, (ts - t0) / DUR), e = 1 - Math.pow(1 - x, 3);
        el.textContent = fmt(fin * e); if (x < 1) { requestAnimationFrame(paso); } }
      setTimeout(function () { requestAnimationFrame(paso); }, 450);
    });
  }
  function frags(d) { return Array.prototype.slice.call(d.querySelectorAll('.pres-frag')); }
  // piezas que aparecen solas, una tras otra, cada vez que se entra a la diapositiva
  function secuencia(d) {
    clearInterval(estado.secT);
    var fs = frags(d); fs.forEach(function (f) { f.classList.remove('is-visible'); });
    var k = 0;
    estado.secT = setInterval(function () {
      if (k >= fs.length) { clearInterval(estado.secT); return; }
      fs[k++].classList.add('is-visible');
    }, 650);
  }
  function siguiente() {
    var d = diapos()[estado.i]; if (!d) { return; }
    var ocultos = frags(d).filter(function (f) { return !f.classList.contains('is-visible'); });
    if (ocultos.length) { clearInterval(estado.secT); ocultos.forEach(function (f) { f.classList.add('is-visible'); }); return; }
    if (d.getAttribute('data-auto') === 'simulador' && !estado.sim) { arrancarSimulador(); return; }   // primero se explica el caso; esta pulsacion lo pone a correr
    mostrar(estado.i + 1);
  }
  function anterior() { clearInterval(estado.secT); mostrar(estado.i - 1); }

  // ------------------------------------------------------------ pantalla completa
  function pantallaCompleta() {
    var el = document.documentElement;
    if (document.fullscreenElement) { document.exitFullscreen(); return; }
    if (el.requestFullscreen) { el.requestFullscreen().catch(function () { document.documentElement.classList.add('pres-pantalla'); ajustar(); }); }
  }
  document.addEventListener('fullscreenchange', function () {
    document.documentElement.classList.toggle('pres-pantalla', !!document.fullscreenElement && !!raizActual);
    setTimeout(ajustar, 60); setTimeout(ajustar, 400);
    if (document.fullscreenElement && raizActual && estado) {            // la diapositiva actual vuelve a animarse (portada: electrocardiograma y camas)
      setTimeout(function () {
        var d = diapos()[estado.i]; if (!d) { return; }
        d.classList.remove('is-activa'); void d.offsetWidth; d.classList.add('is-activa'); contar(d);
      }, 450);
    }
  });

  document.addEventListener('keydown', function (e) {
    if (!raizActual || e.altKey || e.ctrlKey || e.metaKey) { return; }
    var t = e.target, tag = t && t.tagName ? t.tagName.toLowerCase() : '';
    if (tag === 'input' || tag === 'textarea' || tag === 'select' || (t && t.isContentEditable)) { return; }
    var k = e.key;
    if (k === 'ArrowRight' || k === 'PageDown' || k === ' ' || k === 'Enter' || k === 'ArrowDown') { siguiente(); }
    else if (k === 'ArrowLeft' || k === 'PageUp' || k === 'Backspace' || k === 'ArrowUp') { anterior(); }
    else if (k === 'f' || k === 'F') { pantallaCompleta(); }
    else if (k === 'Home') { mostrar(0); }
    else { return; }
    e.preventDefault(); e.stopPropagation();
  }, true);

  document.addEventListener('click', function (e) {
    if (!raizActual || !e.target.closest) { return; }
    if (e.target.closest('#pres-sig')) { siguiente(); }
    else if (e.target.closest('#pres-ant')) { anterior(); }
    else if (e.target.closest('#pres-completa')) { pantallaCompleta(); }
  });

  // ------------------------------------------------------------ simulador: se reproduce y atiende las alertas solo
  function arrancarSimulador() {
    if (estado.sim) { return; }                     // ya corrio: no se reinicia
    estado.sim = {aplicada: false, firma: '', t: null, confT: null};
    var intentos = 0;
    var espera = setInterval(function () {
      var b = $('simint-play');
      if (b || intentos++ > 100) {
        clearInterval(espera);
        var g = $('pres-sim-ganancia'); if (g) { Array.prototype.forEach.call(g.children, function (n) { n.classList.remove('is-visible'); }); }
        var sim = raizActual.querySelector('.pres-sim'); if (sim) { sim.classList.remove('pres-sim--callada'); }
        if (b) { setTimeout(function () { clicVisible(b, function () { var pv = $('pres-previa'); if (pv) { pv.classList.add('pres-previa--oculta'); } }); }, 900);
                 estado.sim.vigilante = setInterval(vigilarSimulador, 400); }
      }
    }, 200);
  }
  // Volver a empezar: pausa si esta corriendo, pulsa «Reiniciar» (vuelve los controles a como opera hoy y borra la corrida) y reproduce de nuevo.
  function reiniciarSimulador() {
    var st = estado.sim;
    if (st) { clearInterval(st.vigilante); clearTimeout(st.t); clearTimeout(st.confT); }
    estado.sim = {aplicada: false, firma: '', t: null, confT: null, reiniciando: true};
    var g0 = $('pres-sim-ganancia'); if (g0) { Array.prototype.forEach.call(g0.children, function (n) { n.classList.remove('is-visible'); }); }
    var play = $('simint-play');
    if (play && /Pausa/.test(play.textContent)) { play.click(); }
    setTimeout(function () {
      var r = $('simint-play-reiniciar'); if (r) { r.click(); }
      window._simintHist = []; window._simintCola = []; window._simintVista = -1; window._simintPendienteEscenario = null;
      var cols = $('simint-alerta-cols'); if (cols) { cols.innerHTML = ''; }
      var rev = $('simint-alerta-rev'); if (rev) { rev.style.display = 'none'; }
      setTimeout(function () {                                   // queda listo: vuelve la vista previa y la siguiente pulsacion lo arranca de nuevo
        estado.sim = null;
        var pv = $('pres-previa'); if (pv) { pv.classList.remove('pres-previa--oculta'); }
      }, 1500);
    }, 500);
  }
  // Cursor visible: se desplaza hasta el boton, hace un pulso y entonces pulsa (para que se vea que se esta aplicando la mejora)
  function clicVisible(el, despues) {
    var cur = $('pres-cursor'), lienzo = $('pres-lienzo');
    if (!el || !cur || !lienzo) { if (el) { el.click(); } if (despues) { despues(); } return; }
    var rl = (cur.offsetParent || lienzo).getBoundingClientRect(), re = el.getBoundingClientRect(), s = lienzo.getBoundingClientRect().width / ANCHO;
    cur.style.left = ((re.left + re.width / 2 - rl.left) / s) + 'px';
    cur.style.top = ((re.top + re.height / 2 - rl.top) / s) + 'px';
    cur.classList.add('is-visible');
    setTimeout(function () {
      cur.classList.add('is-clic'); el.click();
      setTimeout(function () { cur.classList.remove('is-clic'); }, 450);
      setTimeout(function () { cur.classList.remove('is-visible'); }, 1300);
      if (despues) { despues(); }
    }, 1100);
  }
  // La comparacion se ve mejor: la linea «sin la mejora» y la de camas ocupadas mas gruesas
  function realzarLineas() {
    var gd = $('simint-grafico'); if (!gd || !gd.data || !window.Plotly) { return; }
    var idx = [], w = [];
    gd.data.forEach(function (tr, i) {
      var n = tr.name || '';
      if (/Sin la mejora/.test(n) && (!tr.line || tr.line.width !== 3.5)) { idx.push(i); w.push({'line.width': 3.5, 'line.color': '#4a5563'}); }
      else if (/Camas ocupadas \(mediana\)|Esperando cama \(mediana\)/.test(n) && (!tr.line || tr.line.width !== 3.5)) { idx.push(i); w.push({'line.width': 3.5}); }
    });
    idx.forEach(function (i, k) { try { Plotly.restyle(gd, w[k], [i]); } catch (e) {} });
  }
  function texto(id) { var el = $(id); return el ? el.textContent : ''; }
  function vigilarSimulador() {
    var st = estado && estado.sim; if (!st) { return; }
    var pct = texto('simint-player-pct'), g = $('pres-sim-ganancia');      // al terminar con la mejora aplicada, aparecen los resultados como notificaciones
    var n = parseInt(pct, 10);                                             // la barra marca 100 % un instante mientras recalcula: solo cuenta si ya avanzo con la mejora
    if (st.aplicada && n >= 20 && n < 100) { st.avanzo = true; }
    if (g && st.aplicada && st.avanzo && n === 100 && !st.notificado) {
      st.notificado = true;
      realzarLineas();
      Array.prototype.forEach.call(g.children, function (n, k) { setTimeout(function () { n.classList.add('is-visible'); }, 400 + k * 900); });
    }
    var conf = $('simint-confirmacion'), cfg = $('simint-config');
    if (conf && conf.className.indexOf('simint-confirmacion--visible') >= 0) {           // panel verde despues de aplicar la mejora
      var moviendo = cfg && cfg.className.indexOf('simint-config--abierto') >= 0;          // los controles todavia se estan desplazando
      if (!st.confT && !moviendo) {
        st.confT = setTimeout(function () { st.confT = null; clicVisible($('simint-confirmar')); }, LEER_CONFIRMACION);
      }
      return;
    }
    var card = $('simint-alerta');
    if (!card || card.style.display === 'none' || card.className.indexOf('--idle') >= 0) { return; }
    var firma = texto('simint-alerta-titulo') + '|' + texto('simint-alerta-fecha') + '|' + texto('simint-alerta-pos');
    if (firma === st.firma) { return; }
    st.firma = firma; clearTimeout(st.t);
    // Solo se muestra la alerta que trae la mejora; las demas (cola, esperas, etc.) se continuan sin dejarlas a la vista
    var apV = $('simint-aplicar'), esMejora = !st.aplicada && apV && apV.style.display === 'block';
    var simRaiz = raizActual.querySelector('.pres-sim'); if (simRaiz) { simRaiz.classList.toggle('pres-sim--callada', !esMejora); }
    if (!esMejora) { st.t = setTimeout(function () { var c = $('simint-continuar'); if (c) { c.click(); } }, 250); return; }
    st.t = setTimeout(function () {
      var ap = $('simint-aplicar');
      if (!st.aplicada && ap && ap.style.display === 'block') { st.aplicada = true; clicVisible(ap); }
      else { var c = $('simint-continuar'); if (c) { c.click(); } }
    }, st.aplicada ? LEER_OTRA_ALERTA : LEER_ALERTA);          // la alerta de la mejora se deja leer; las siguientes pasan rapido
  }

  // ------------------------------------------------------------ asistente: dos preguntas con sus respuestas guardadas
  // Al volver a la diapositiva desde la anterior, la conversacion empieza de nuevo (como si se preguntara en vivo otra vez).
  function reiniciarAsistente() {
    (estado.asisT || []).forEach(function (x) { clearTimeout(x); clearInterval(x); });
    var log = $('pres-chat-log'); if (log) { log.innerHTML = ''; }
    estado.asis = false; arrancarAsistente();
  }
  function arrancarAsistente() {
    if (estado.asis) { return; }
    estado.asis = true;
    var T = estado.asisT = [];
    function luego(f, ms) { var x = setTimeout(f, ms); T.push(x); return x; }
    var qs = [];
    try { qs = JSON.parse(raizActual.getAttribute('data-preguntas') || '[]'); } catch (e) {}
    var log = $('pres-chat-log'); if (!log || !window.asisBurbuja) { return; }
    var i = 0;
    function alFinal() { log.scrollTo({top: log.scrollHeight, behavior: 'smooth'}); }
    function sig() {
      if (i >= qs.length) { return; }
      var q = qs[i++], datos = Object.assign({}, q.datos);
      delete datos.paginas; delete datos.seguimiento;            // en la presentacion no hay enlaces ni preguntas sugeridas que pulsar
      var u = document.createElement('div');
      u.className = 'asis-msg asis-msg--usuario pres-aparece';
      u.innerHTML = '<div class="asis-burbuja"></div>';
      log.appendChild(u); alFinal();
      var b = u.firstChild, k = 0;
      var t = setInterval(function () {
        b.textContent = q.pregunta.slice(0, ++k);
        if (k < q.pregunta.length) { return; }
        clearInterval(t);
        var tmp = document.createElement('div'); tmp.innerHTML = window.asisPensando || '';
        var pensando = tmp.firstChild; if (pensando) { log.appendChild(pensando); alFinal(); }
        luego(function () {
          if (pensando) { pensando.remove(); }
          var r = document.createElement('div'); r.innerHTML = window.asisBurbuja({rol: 'asistente', datos: datos});
          var nodo = r.firstChild; nodo.classList.add('pres-aparece'); log.appendChild(nodo);
          log.scrollTo({top: nodo.offsetTop - 12, behavior: 'smooth'});
          luego(sig, 11000);
        }, 1800);
      }, 40);
      T.push(t);
    }
    luego(sig, 800);
  }

  // ------------------------------------------------------------ montaje: Dash dibuja la pagina despues de cargar, y se puede entrar y salir
  function iniciar(raiz) {
    raizActual = raiz;
    estado = {i: -1, sim: null, asis: false, secT: null};
    document.documentElement.classList.add('en-presentacion');
    var i = 0; try { i = parseInt(sessionStorage.getItem('pres-diapo') || '0', 10) || 0; } catch (e) {}
    if (i === 5 || i === 6) { i = 4; }        // si se recarga en la diapositiva del simulador, se vuelve a la anterior para que arranque al entrar
    var m = /[?&]diapo=(\d+)/.exec(location.search); if (m) { i = parseInt(m[1], 10); }     // para ensayar: /presentacion?diapo=5
    mostrar(i);
    ajustar();
    if (window.ResizeObserver) {
      var ro = new ResizeObserver(function () { ajustarInternos(); });
      raiz.querySelectorAll('.pres-ajustar > *').forEach(function (h) { ro.observe(h); });
    }
  }
  function terminar() {
    if (estado && estado.sim && estado.sim.vigilante) { clearInterval(estado.sim.vigilante); }
    raizActual = null; estado = null;
    document.documentElement.classList.remove('en-presentacion', 'pres-pantalla');
    if (document.fullscreenElement) { document.exitFullscreen(); }
  }
  setInterval(function () {
    var r = $('pres-raiz');
    if (r && r !== raizActual) { iniciar(r); }
    else if (!r && raizActual) { terminar(); }
  }, 250);
  window.addEventListener('resize', function () { if (raizActual) { ajustar(); } });
  setInterval(function () { if (raizActual) { ajustarInternos(); } }, 2500);     // por si el simulador cambia de alto (el ResizeObserver ya lo cubre)
})();
