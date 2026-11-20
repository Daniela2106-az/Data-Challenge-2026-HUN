// dashboard/assets/navegacion_rapida.js (20-nov-2026): respuesta inmediata al cambiar de pagina.
// Cuando el servidor esta ocupado (Render gratuito calcula una cosa a la vez), el clic en el menu tarda en traer la pagina nueva y parece que no paso nada.
// Aqui, al hacer clic en un enlace interno: el enlace se marca como activo al instante y aparece una barra de progreso
// arriba, que desaparece cuando llega la pagina. No se toca el texto de la barra superior: React lo administra y cambiarlo a mano rompia la actualizacion
// cuando la pagina no tenia categoria (el asistente). No cambia lo que se calcula: solo que el usuario ve que el clic funciono.
(function () {
  var reloj = null, destino = null;
  function fin() { document.documentElement.classList.remove('nav-cargando'); clearTimeout(reloj); }
  document.addEventListener('click', function (e) {
    var a = e.target.closest && e.target.closest('a[href^="/"]');
    if (!a || a.target === '_blank' || e.metaKey || e.ctrlKey || e.shiftKey || a.getAttribute('href') === location.pathname) { return; }
    var barra = document.querySelector('.sidebar');
    if ((a.classList.contains('nav__item') || a.classList.contains('nav__simular')) && barra) {      // «Simular» tambien se marca al instante
      barra.querySelectorAll('.nav__item.is-active, .nav__simular.is-active').forEach(function (x) { x.classList.remove('is-active'); });
      a.classList.add('is-active');
    }
    destino = a.getAttribute('href').split('#')[0].split('?')[0];
    document.documentElement.classList.add('nav-cargando');
    clearTimeout(reloj); reloj = setTimeout(fin, 12000);
  }, true);
  // la pagina llego cuando el contenido de la zona principal cambia (en cualquier nivel: Dash reutiliza los nodos y a veces solo cambia lo de adentro).
  // Solo cuenta si la URL ya es la del enlace pulsado; se espera un momento sin cambios y, pase lo que pase, la barra se quita a los 12 s.
  var intentos = 0, quieto = null;
  (function observar() {
    var c = document.getElementById('_pages_content');
    if (c) {
      new MutationObserver(function () {
        if (!document.documentElement.classList.contains('nav-cargando') || location.pathname !== destino) { return; }
        clearTimeout(quieto); quieto = setTimeout(fin, 350);
      }).observe(c, {childList: true, subtree: true});
      return;
    }
    if (intentos++ < 100) { setTimeout(observar, 100); }
  })();
})();
