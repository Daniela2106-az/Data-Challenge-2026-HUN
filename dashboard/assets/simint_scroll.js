// dashboard/assets/simint_scroll.js (19-nov-2026): desplazamiento suave que deja un elemento en el centro de la pantalla.
// Prioridad: que se vea SIEMPRE su parte de arriba (el encabezado de la tarjeta); si no cabe entero, se corta la parte de abajo.
window.simintCentrar = function (el, mantener) {
  if (!el) { return; }
  var r = el.getBoundingClientRect(), vh = window.innerHeight || document.documentElement.clientHeight, MARGEN = 96;
  var topFinal = (vh - r.height) / 2;                 // donde quedaria el borde de arriba si se centra
  if (topFinal < MARGEN) { topFinal = MARGEN; }       // nunca por encima del margen: el encabezado manda
  var y = r.top - topFinal;
  if (mantener) {                                      // un elemento que debe quedar a la vista (p. ej. el boton de reproducir): no se corta por arriba
    var rb = mantener.getBoundingClientRect();
    if (rb.top - y < MARGEN) { y = rb.top - MARGEN; }
  }
  window.scrollBy({top: y, behavior: 'smooth'});
};

// Alerta que pausa la simulacion: el borde de arriba de la tarjeta (su encabezado) queda en el primer cuarto de la pantalla.
window.simintEncabezadoAlMedio = function (el) {
  if (!el) { return; }
  var vh = window.innerHeight || document.documentElement.clientHeight;
  var destino = Math.max(96, vh * 0.15);      // primer cuarto de la pantalla, sin quedar bajo la barra superior
  window.scrollBy({top: el.getBoundingClientRect().top - destino, behavior: 'smooth'});
};
