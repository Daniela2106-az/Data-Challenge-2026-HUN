// dashboard/assets/acordeon.js (16-nov-2026)
// Comportamiento de las "laminas" de resultados agrupadas en fila horizontal con laminas_grupo() (ver
// dashboard/componentes.py): colapsadas solo muestran su numero; se turnan para expandirse solas cada
// INTERVALO_MS, o al pasar el mouse por encima (ahi se pausa la rotacion hasta que el mouse sale de la fila).
// Al expandirse, el contenido ya aparece con una transicion de opacidad (puro CSS, theme.css); aqui solo se
// anima el GRAFICO: barra por barra si es un grafico de barras, o un fundido si es de otro tipo.
//
// Dash reemplaza el contenido de la pagina entera al navegar (dash.page_container), asi que esto no se
// enlaza una sola vez al cargar: un barrido periodico detecta filas nuevas (las registra) y filas que ya no
// estan en el documento (les libera el temporizador), para no acumular intervalos de paginas anteriores.
(function () {
  var INTERVALO_MS = 8000;                 // tiempo razonable para leer una tarjeta completa (texto + grafico)
  var REDUCIR_MOVIMIENTO = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var filas = [];                          // {el, timer, idx, manual}

  function tarjetas(filaEl) {
    return Array.prototype.filter.call(filaEl.children, function (c) {
      return c.classList && c.classList.contains('lamina-acordeon');
    });
  }

  function expandir(fila, idx) {
    var cs = tarjetas(fila.el);
    if (!cs.length) { return; }
    idx = ((idx % cs.length) + cs.length) % cs.length;
    cs.forEach(function (c, i) { c.classList.toggle('is-expanded', i === idx); });
    fila.idx = idx;
  }

  function reiniciarTimer(fila) {
    clearInterval(fila.timer);
    if (fila.manual || REDUCIR_MOVIMIENTO) { return; }
    fila.timer = setInterval(function () { expandir(fila, fila.idx + 1); }, INTERVALO_MS);
  }

  function registrar(el) {
    if (el._acordeonListo) { return; }
    el._acordeonListo = true;
    var fila = { el: el, timer: null, idx: -1, manual: false };
    filas.push(fila);
    expandir(fila, 0);
    reiniciarTimer(fila);
    el.addEventListener('mouseover', function (e) {
      var tarjeta = e.target.closest ? e.target.closest('.lamina-acordeon') : null;
      if (!tarjeta || tarjeta.parentElement !== el) { return; }
      var idx = tarjetas(el).indexOf(tarjeta);
      if (idx < 0 || idx === fila.idx) { return; }
      fila.manual = true;
      clearInterval(fila.timer);
      expandir(fila, idx);
    });
    el.addEventListener('mouseleave', function () {
      fila.manual = false;
      reiniciarTimer(fila);
    });
  }

  // Revela el grafico de la tarjeta que se acaba de expandir: barra por barra si tiene barras (Plotly agrupa
  // cada barra en g.point dentro de la capa .barlayer), o un fundido simple para cualquier otro tipo de grafico.
  function revelarGrafico(tarjeta) {
    if (REDUCIR_MOVIMIENTO) { return; }
    var lienzos = tarjeta.querySelectorAll('.js-plotly-plot');
    lienzos.forEach(function (gd) {
      var barras = gd.querySelectorAll('.barlayer .point');
      if (!barras.length) {
        gd.style.transition = 'none'; gd.style.opacity = '0'; gd.style.transform = 'translateY(6px)';
        requestAnimationFrame(function () {
          gd.style.transition = 'opacity .45s ease, transform .45s ease';
          gd.style.opacity = '1'; gd.style.transform = 'translateY(0)';
        });
        return;
      }
      barras.forEach(function (g) {
        g.style.transformOrigin = 'bottom'; g.style.transformBox = 'fill-box';
        g.style.transition = 'none'; g.style.opacity = '.35'; g.style.transform = 'scaleY(.05)';
      });
      requestAnimationFrame(function () {
        requestAnimationFrame(function () {
          barras.forEach(function (g, i) {
            var espera = Math.min(i * 35, 650);
            g.style.transition = 'transform .5s cubic-bezier(.22,.8,.25,1) ' + espera + 'ms, opacity .35s ease ' + espera + 'ms';
            g.style.opacity = '1'; g.style.transform = 'scaleY(1)';
          });
        });
      });
    });
  }

  document.addEventListener('transitionend', function (e) {
    var t = e.target;
    if (e.propertyName !== 'flex-grow' || !t.classList || !t.classList.contains('lamina-acordeon')) { return; }
    if (t.classList.contains('is-expanded')) { revelarGrafico(t); }
  });

  function barrido() {
    filas = filas.filter(function (fila) {
      if (document.body.contains(fila.el)) { return true; }
      clearInterval(fila.timer);
      return false;
    });
    document.querySelectorAll('.laminas-row').forEach(registrar);
  }
  setInterval(barrido, 1000);
  if (document.readyState === 'loading') { document.addEventListener('DOMContentLoaded', barrido); } else { barrido(); }
})();
