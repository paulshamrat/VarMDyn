(function () {
  "use strict";

  var storageKey = "varmdyn-docs-theme";
  var root = document.documentElement;

  function preferredTheme() {
    var stored = window.localStorage.getItem(storageKey);
    if (stored === "light" || stored === "dark") {
      return stored;
    }
    if (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches) {
      return "dark";
    }
    return "light";
  }

  function applyTheme(theme) {
    root.setAttribute("data-varmdyn-theme", theme);
    var button = document.querySelector("[data-varmdyn-theme-toggle]");
    if (button) {
      button.textContent = theme === "dark" ? "Light mode" : "Dark mode";
      button.setAttribute("aria-label", theme === "dark" ? "Switch to light mode" : "Switch to dark mode");
    }
  }

  function toggleTheme() {
    var next = root.getAttribute("data-varmdyn-theme") === "dark" ? "light" : "dark";
    window.localStorage.setItem(storageKey, next);
    applyTheme(next);
  }

  applyTheme(preferredTheme());

  document.addEventListener("DOMContentLoaded", function () {
    var content = document.querySelector(".wy-nav-content");
    if (!content || document.querySelector("[data-varmdyn-theme-toggle]")) {
      applyTheme(root.getAttribute("data-varmdyn-theme") || preferredTheme());
      return;
    }

    var button = document.createElement("button");
    button.type = "button";
    button.className = "vm-theme-toggle";
    button.setAttribute("data-varmdyn-theme-toggle", "true");
    button.addEventListener("click", toggleTheme);
    content.insertBefore(button, content.firstChild);
    applyTheme(root.getAttribute("data-varmdyn-theme") || preferredTheme());
  });
})();
