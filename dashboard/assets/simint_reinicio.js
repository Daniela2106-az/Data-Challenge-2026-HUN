// dashboard/assets/simint_reinicio.js (19-nov-2026)
// Al RECARGAR la pagina (Cmd+R) el simulador debe salir en ceros, como la primera vez: este archivo solo corre en una carga completa,
// no al navegar dentro de la app, asi que borra el estado guardado de la sesion (corrida, cursor, sliders y selectores).
// Navegar a otra pagina y volver NO pasa por aqui, y por eso ahi si se conserva donde ibas.
(function () {
  try {
    var borrar = [];
    for (var i = 0; i < sessionStorage.length; i++) {
      var k = sessionStorage.key(i);
      if (k && k.indexOf('simint') >= 0) { borrar.push(k); }
    }
    borrar.forEach(function (k) { sessionStorage.removeItem(k); });
  } catch (e) {}
})();
