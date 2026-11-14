// Recorrido con el teclado (13-nov-2026): las flechas izquierda y derecha pasan a la pagina anterior o siguiente, como en una
// presentacion. Usa los botones del pie que arma dashboard/main.py. No actua si se esta escribiendo o moviendo un control.
document.addEventListener('keydown', function (e) {
  if (e.altKey || e.ctrlKey || e.metaKey || e.shiftKey) { return; }
  var t = e.target;
  var etiqueta = t && t.tagName ? t.tagName.toLowerCase() : '';
  if (etiqueta === 'input' || etiqueta === 'textarea' || etiqueta === 'select' || (t && t.isContentEditable)) { return; }
  if (t && t.closest && t.closest('[role="slider"], [role="listbox"], [role="combobox"], .rc-slider, .Select, .dash-dropdown')) { return; }
  var selector = e.key === 'ArrowRight' ? '.paso__btn--sig' : (e.key === 'ArrowLeft' ? '.paso__btn--ant' : null);
  if (!selector) { return; }
  var boton = document.querySelector(selector);
  if (boton) { e.preventDefault(); boton.click(); }
});

// Modo presentacion (14-nov-2026): el boton de la barra superior oculta el menu lateral y agranda la pagina, para exponer.
// Se sale con el mismo boton o con Esc. El estado se recuerda mientras la pestaña este abierta.
(function () {
  var CLASE = 'presentando';
  function aplicar(activo) {
    document.documentElement.classList.toggle(CLASE, activo);
    try { sessionStorage.setItem('hun-presentando', activo ? '1' : '0'); } catch (err) {}
    setTimeout(function () { window.dispatchEvent(new Event('resize')); }, 60);   // las graficas se ajustan al nuevo ancho
  }
  try { if (sessionStorage.getItem('hun-presentando') === '1') { document.documentElement.classList.add(CLASE); } } catch (err) {}
  document.addEventListener('click', function (e) {
    if (e.target && e.target.closest && e.target.closest('#modo-presentacion')) {
      aplicar(!document.documentElement.classList.contains(CLASE));
    }
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && document.documentElement.classList.contains(CLASE)) { aplicar(false); }
  });
})();
