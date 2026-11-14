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
