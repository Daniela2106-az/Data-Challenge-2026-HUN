// Retira la animacion de entrada (intro.css) al terminar, al hacer clic/tecla, y la recuerda por sesion.
(function () {
  var el = document.getElementById("intro-hun");
  if (!el) return;
  function quitar() { el.classList.add("intro-listo"); try { sessionStorage.setItem("intro-hun", "1"); } catch (e) {} }
  el.addEventListener("click", quitar);
  document.addEventListener("keydown", quitar, { once: true });
  setTimeout(quitar, 3900);
})();
