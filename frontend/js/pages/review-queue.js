import { renderFooter } from "../components/footer.js";
import { renderHeader } from "../components/header.js";
import { api } from "../utils/api.js";
import { getCurrentUser, isAdmin } from "../utils/auth.js";
import { escapeHtml, qs } from "../utils/dom.js";
import { toast } from "../utils/toast.js";

function row(proposal) {
  const payload = proposal.payload || {};
  const current = proposal.event;
  const diff = current
    ? `<p><strong>Current title:</strong> ${escapeHtml(current.title)}</p>`
    : "";
  return `
    <article class="card-panel" data-id="${proposal.id}" style="margin-bottom:16px;">
      <p><strong>${escapeHtml(proposal.kind)}</strong> · ${escapeHtml(payload.title || current?.title || "Untitled")}</p>
      ${diff}
      <p>${escapeHtml(payload.description || "")}</p>
      <p><a href="${escapeHtml(proposal.source_url || payload.registration_link || "#")}" target="_blank" rel="noopener">Source</a></p>
      <pre style="white-space:pre-wrap;">${escapeHtml(JSON.stringify(payload, null, 2))}</pre>
      <button type="button" class="btn btn-gold btn-sm" data-action="approve">Approve</button>
      <button type="button" class="btn btn-secondary btn-sm" data-action="reject">Reject</button>
    </article>
  `;
}

async function load() {
  const data = await api.get("/agent/proposals/?status=pending");
  const mount = qs("#queue");
  const items = data.results || data;
  if (!items.length) {
    mount.innerHTML = `<p>Nothing is waiting for review.</p>`;
    return;
  }
  mount.innerHTML = items.map(row).join("");
  mount.querySelectorAll("button").forEach((button) => {
    button.addEventListener("click", async () => {
      const id = button.closest("article").dataset.id;
      const action = button.dataset.action;
      await api.post(`/agent/proposals/${id}/${action}/`, {});
      toast.success(action === "approve" ? "Approved." : "Rejected.");
      load();
    });
  });
}

async function init() {
  await renderHeader();
  renderFooter();
  const user = await getCurrentUser();
  if (!isAdmin(user)) {
    window.location.href = "/index.html";
    return;
  }
  qs("#approve-all").addEventListener("click", async () => {
    if (!window.confirm("Approve every pending proposal?")) return;
    await api.post("/agent/proposals/approve-all/", {});
    toast.success("Approved.");
    load();
  });
  await load();
}

init();
