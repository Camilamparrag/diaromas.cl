/* ==========================================================================
   DIAROMAS — interacciones mínimas y progresivas
   Sin dependencias externas: si el JS no carga, la tienda sigue funcionando
   (el carrito se actualiza por formularios HTML normales).
   ========================================================================== */
(function () {
  "use strict";

  /* --- Menú móvil ------------------------------------------------------- */
  const botonMenu = document.querySelector("[data-menu-boton]");
  const panelMenu = document.querySelector("[data-menu-panel]");

  if (botonMenu && panelMenu) {
    botonMenu.addEventListener("click", () => {
      const activo = panelMenu.classList.toggle("activo");
      botonMenu.setAttribute("aria-expanded", String(activo));
      botonMenu.setAttribute("aria-label", activo ? "Cerrar menú" : "Abrir menú");
    });
  }

  /* --- Menú de usuario -------------------------------------------------- */
  const menuUsuario = document.querySelector("[data-menu-usuario]");
  if (menuUsuario) {
    const disparador = menuUsuario.querySelector(".menu-usuario__boton");
    const panel = menuUsuario.querySelector(".menu-usuario__panel");

    const alternarUsuario = (forzar) => {
      const activo = forzar !== undefined ? forzar : !panel.classList.contains("activo");
      panel.classList.toggle("activo", activo);
      disparador.setAttribute("aria-expanded", String(activo));
    };

    disparador.addEventListener("click", (evento) => {
      evento.stopPropagation();
      alternarUsuario();
    });

    document.addEventListener("click", (evento) => {
      if (!menuUsuario.contains(evento.target)) alternarUsuario(false);
    });

    document.addEventListener("keydown", (evento) => {
      if (evento.key === "Escape") alternarUsuario(false);
    });
  }

  /* --- Selectores de cantidad (+ / -) ----------------------------------- */
  document.querySelectorAll(".selector-cantidad__controles").forEach((grupo) => {
    const campo = grupo.querySelector('input[type="number"]');
    const minimo = parseInt(campo.min, 10) || 1;
    const maximo = parseInt(campo.max, 10) || 99;

    const fijar = (valor) => {
      campo.value = String(Math.min(Math.max(valor, minimo), maximo));
      campo.dispatchEvent(new Event("change", { bubbles: true }));
    };

    const restar = grupo.querySelector("[data-restar]");
    const sumar = grupo.querySelector("[data-sumar]");

    if (restar) restar.addEventListener("click", () => fijar(parseInt(campo.value, 10) - 1));
    if (sumar) sumar.addEventListener("click", () => fijar(parseInt(campo.value, 10) + 1));
  });

  /* --- Avisos: cierre manual -------------------------------------------- */
  document.querySelectorAll("[data-cerrar-aviso]").forEach((boton) => {
    boton.addEventListener("click", () => {
      const aviso = boton.closest(".aviso");
      if (aviso) aviso.remove();
    });
  });

  /* --- Imágenes de respaldo (productos sin foto subida) ------------------ */
  document.querySelectorAll("img[data-fallback]").forEach((imagen) => {
    imagen.addEventListener(
      "error",
      () => {
        const respaldo = imagen.dataset.fallback;
        if (respaldo && imagen.src !== new URL(respaldo, location.href).href) {
          imagen.src = respaldo;
        }
      },
      { once: true }
    );
  });

  /* --- Aviso discreto al agregar al carrito ----------------------------- */
  const insignia = document.querySelector("[data-carrito-cantidad]");
  const botonCarrito = document.querySelector(".boton-carrito");

  document.querySelectorAll('.form-agregar button[type="submit"]').forEach((boton) => {
    boton.addEventListener("click", () => {
      const textoOriginal = boton.textContent;
      boton.textContent = "Agregado";
      boton.disabled = true;
      // El formulario se envía igual: solo es una confirmación visual.
      setTimeout(() => {
        boton.textContent = textoOriginal;
        boton.disabled = false;
      }, 1200);

      if (insignia && botonCarrito) {
        const actual = parseInt(insignia.textContent, 10) || 0;
        insignia.textContent = String(actual + 1);
      }
    });
  });

  /* --- Confirmación al cancelar ------------------------------------------ */
  const botonVaciar = document.querySelector('form[action*="/carrito/vaciar/"]');
  if (botonVaciar) {
    botonVaciar.addEventListener("submit", (evento) => {
      if (!window.confirm("¿Quieres vaciar todo el carrito?")) evento.preventDefault();
    });
  }
})();