/** Minimal toast/snackbar notifications — no dependencies, just DOM + CSS animation. */

function getContainer() {
  let container = document.querySelector(".toast-container");
  if (!container) {
    container = document.createElement("div");
    container.className = "toast-container";
    document.body.appendChild(container);
  }
  return container;
}

function showToast(message, type = "success", duration = 4500, action = null) {
  const container = getContainer();
  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  const text = document.createElement("span");
  text.textContent = message;
  toast.appendChild(text);
  if (action) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "toast-action";
    button.textContent = action.label;
    button.addEventListener("click", () => {
      action.onClick();
      toast.remove();
    });
    toast.appendChild(button);
  }
  container.appendChild(toast);

  setTimeout(() => {
    toast.remove();
  }, duration);
}

export const toast = {
  success: (message, options = {}) =>
    showToast(message, "success", options.duration ?? 4500, options.action || null),
  error: (message) => showToast(message, "error"),
};
