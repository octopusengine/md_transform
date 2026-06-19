(function () {
  var storageKey = "md-export-mode";

  function savedMode() {
    try {
      return localStorage.getItem(storageKey);
    } catch (error) {
      return null;
    }
  }

  function rememberMode(mode) {
    try {
      localStorage.setItem(storageKey, mode);
    } catch (error) {
      return;
    }
  }

  function preferredMode() {
    var mode = savedMode();
    if (mode === "dark" || mode === "light") {
      return mode;
    }

    if (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches) {
      return "dark";
    }

    return "light";
  }

  function updateButtons(mode) {
    document.querySelectorAll("[data-mode-toggle]").forEach(function (button) {
      button.textContent = mode === "dark" ? "light" : "dark";
      button.setAttribute(
        "aria-label",
        mode === "dark" ? "Switch to light mode" : "Switch to dark mode"
      );
    });
  }

  function setMode(mode) {
    document.documentElement.setAttribute("data-mode", mode);
    rememberMode(mode);
    updateButtons(mode);
  }

  setMode(preferredMode());

  document.addEventListener("DOMContentLoaded", function () {
    updateButtons(document.documentElement.getAttribute("data-mode") || preferredMode());

    document.querySelectorAll("[data-mode-toggle]").forEach(function (button) {
      button.addEventListener("click", function () {
        var currentMode = document.documentElement.getAttribute("data-mode") || preferredMode();
        setMode(currentMode === "dark" ? "light" : "dark");
      });
    });
  });
})();
