// dashboard/assets/anclas.js (18-nov-2026)
// Lleva a la tarjeta exacta cuando se abre una pagina con un ancla: /recomendaciones#rec-R4 (la recomendacion R4) o /alertas#alerta-A2 (la alerta A2).
// Dash dibuja el contenido despues de cargar la pagina, asi que el navegador solo no encuentra el elemento: se revisa cada 0,4 s (hasta 24 s) hasta que existe,
// se desplaza hasta el, se vuelve a ajustar cuando la pagina termina de acomodarse y se resalta unos segundos.
(function () {
  var ultimo = null, intentos = 0;
  function destacar(el) {
    el.classList.add('ancla-destacada');
    setTimeout(function () { el.classList.remove('ancla-destacada'); }, 3500);
  }
  function ir() {
    var h = decodeURIComponent((location.hash || '').replace('#', ''));
    if (!/^(rec-R|alerta-)/.test(h)) { ultimo = null; return; }
    if (h !== ultimo) { ultimo = h; intentos = 0; }
    if (intentos > 60) { return; }
    intentos++;
    var el = document.getElementById(h);
    if (!el || el._anclaHecha) { return; }
    el._anclaHecha = true;
    el.scrollIntoView({ block: 'start' });
    destacar(el);
    setTimeout(function () { el.scrollIntoView({ block: 'start' }); }, 1400);   // la pagina aun se acomoda (graficos, tarjetas): se vuelve a centrar
  }
  setInterval(ir, 400);
})();
