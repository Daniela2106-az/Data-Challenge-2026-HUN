// dashboard/assets/carrusel.js (21-nov-2026, grupos añadidos el mismo día)
// Carrusel generico para los modulos de "vistas" del simulador integral (edad/sexo/ruta, franjas/patron por
// hora, etc.): varios paneles en una pista horizontal que se deslizan con CSS (transform), rotando solos
// cada INTERVALO_MS o al hacer clic en un boton. Mismo patron de barrido periodico que acordeon.js: Dash
// reemplaza el contenido de la pagina al navegar/recalcular, asi que un barrido registra carruseles nuevos
// y libera temporizadores de los que ya no estan en el documento.
//
// GRUPOS (21-nov): dos carruseles pueden compartir una sola fila de botones EXTERNA (.simint-vista-switch,
// mismo atributo data-grupo en los dos carruseles y en la fila) en vez de tener cada uno la suya — los
// carruseles de un grupo no manejan su propio click/temporizador: lo hace el grupo, que mueve a los dos a
// la vez para que siempre muestren la misma vista (edad/sexo/ruta).
(function () {
  var INTERVALO_MS = 6000;
  var REDUCIR_MOVIMIENTO = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var carruseles = [];   // carruseles SIN grupo (data-grupo ausente): {el, timer, idx}
  var grupos = {};       // clave de grupo -> {timer, idx}

  function paneles(el) {
    var track = el.querySelector('.simint-carrusel__track');
    return track ? Array.prototype.slice.call(track.children) : [];
  }

  // Mueve UN carrusel a `idx` (ajustado a su propio numero de paneles) y actualiza sus botones PROPIOS, si
  // los tiene (los carruseles de un grupo no dibujan botones propios, ver sin_botones en simulador.py).
  function mostrarEnCarrusel(el, idx) {
    var ps = paneles(el);
    if (!ps.length) { return idx; }
    var real = ((idx % ps.length) + ps.length) % ps.length;
    var track = el.querySelector('.simint-carrusel__track');
    if (track) { track.style.transform = 'translateX(-' + (real * 100) + '%)'; }
    var botones = el.querySelectorAll('.simint-carrusel__boton');   // vacio si el carrusel no dibuja los suyos (sin_botones=True)
    botones.forEach(function (b, i) { b.classList.toggle('is-active', i === real); });
    return real;
  }

  function mostrar(car, idx) {
    car.idx = mostrarEnCarrusel(car.el, idx);
  }

  function reiniciarTimer(car) {
    clearInterval(car.timer);
    if (REDUCIR_MOVIMIENTO) { return; }
    car.timer = setInterval(function () { mostrar(car, car.idx + 1); }, INTERVALO_MS);
  }

  function registrar(el) {
    if (el.hasAttribute('data-grupo')) { return; }   // lo maneja el mecanismo de grupos, mas abajo
    if (el._carruselListo) { return; }
    el._carruselListo = true;
    var car = { el: el, timer: null, idx: 0 };
    carruseles.push(car);
    mostrar(car, 0);
    reiniciarTimer(car);
    el.addEventListener('click', function (e) {
      var btn = e.target.closest ? e.target.closest('.simint-carrusel__boton') : null;
      if (!btn || !btn.parentElement || btn.parentElement.closest('.simint-carrusel') !== el) { return; }
      var idx = Array.prototype.indexOf.call(btn.parentElement.children, btn);
      if (idx < 0) { return; }
      mostrar(car, idx);
      reiniciarTimer(car);     // sigue rotando, pero desde la posicion que se elegio
    });
  }

  // Mueve TODOS los carruseles de un grupo (y la fila de botones externa que los acompaña) a la misma vista.
  function mostrarGrupo(clave, idx) {
    var els = document.querySelectorAll('.simint-carrusel[data-grupo="' + clave + '"]');
    var max = 0;
    els.forEach(function (el) { max = Math.max(max, paneles(el).length); });
    if (!max) { return idx; }
    var real = ((idx % max) + max) % max;
    els.forEach(function (el) { mostrarEnCarrusel(el, real); });
    document.querySelectorAll('.simint-vista-switch[data-grupo="' + clave + '"] .simint-carrusel__boton')
      .forEach(function (b, i) { b.classList.toggle('is-active', i === real); });
    return real;
  }

  function reiniciarTimerGrupo(clave) {
    var g = grupos[clave];
    clearInterval(g.timer);
    if (REDUCIR_MOVIMIENTO) { return; }
    g.timer = setInterval(function () { g.idx = mostrarGrupo(clave, g.idx + 1); }, INTERVALO_MS);
  }

  function registrarGrupo(clave) {
    if (grupos[clave]) { return; }
    grupos[clave] = { idx: 0, timer: null };
    grupos[clave].idx = mostrarGrupo(clave, 0);
    reiniciarTimerGrupo(clave);
  }

  function registrarFilasDeGrupo() {
    document.querySelectorAll('.simint-vista-switch').forEach(function (fila) {
      var clave = fila.getAttribute('data-grupo');
      if (!clave || fila._filaListo) { return; }
      fila._filaListo = true;
      fila.addEventListener('click', function (e) {
        var btn = e.target.closest ? e.target.closest('.simint-carrusel__boton') : null;
        if (!btn) { return; }
        var idx = Array.prototype.indexOf.call(fila.children, btn);
        if (idx < 0) { return; }
        grupos[clave] = grupos[clave] || { idx: 0, timer: null };
        grupos[clave].idx = mostrarGrupo(clave, idx);
        reiniciarTimerGrupo(clave);
      });
    });
  }

  // Switch 14/30 dias de "Estancias largas": div clicable (sin <input> real), independiente del carrusel
  // (no rota); alterna su propia clase is-on y mueve data-umbral del carrusel contenedor — el CSS
  // (theme.css) decide que figura mostrar segun ese atributo.
  function registrarSwitches() {
    document.querySelectorAll('.simint-switch').forEach(function (sw) {
      if (sw._switchListo) { return; }
      sw._switchListo = true;
      sw.addEventListener('click', function () {
        var encendido = !sw.classList.contains('is-on');
        sw.classList.toggle('is-on', encendido);
        var car = sw.closest('.simint-carrusel');
        if (car) { car.setAttribute('data-umbral', encendido ? '30' : '14'); }
      });
    });
  }

  function barrido() {
    carruseles = carruseles.filter(function (car) {
      if (document.body.contains(car.el)) { return true; }
      clearInterval(car.timer);
      return false;
    });
    document.querySelectorAll('.simint-carrusel').forEach(registrar);

    var clavesVivas = {};
    document.querySelectorAll('.simint-carrusel[data-grupo]').forEach(function (el) {
      clavesVivas[el.getAttribute('data-grupo')] = true;
    });
    Object.keys(clavesVivas).forEach(registrarGrupo);
    Object.keys(grupos).forEach(function (clave) {
      if (!clavesVivas[clave]) { clearInterval(grupos[clave].timer); delete grupos[clave]; }
    });
    registrarFilasDeGrupo();
    registrarSwitches();
  }
  setInterval(barrido, 1000);
  if (document.readyState === 'loading') { document.addEventListener('DOMContentLoaded', barrido); } else { barrido(); }
})();
