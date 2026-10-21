import { renderFooter } from "../components/footer.js";
import { renderHeader } from "../components/header.js";
import { api } from "../utils/api.js";
import { getCurrentUser, isAdmin } from "../utils/auth.js";
import { escapeHtml, qs } from "../utils/dom.js";

async function init() {
  await renderHeader();
  renderFooter();
  const user = await getCurrentUser();
  if (!isAdmin(user)) {
    window.location.href = "/index.html";
    return;
  }
  const report = await api.get("/admin/health-report/latest/");
  const health = report.site_health;
  const approval = report.awaiting_approval;
  qs("#report").innerHTML = `
    <p><strong>Waiting for approval:</strong> ${approval.total}</p>
    <p><a href="/pages/review-queue.html">Open the review queue</a></p>
    <p><strong>API requests (24h):</strong> ${health.requests}</p>
    <p><strong>Average:</strong> ${health.average_ms} ms · <strong>95th percentile:</strong> ${health.p95_ms} ms</p>
    <p><strong>5xx rate:</strong> ${health.server_error_rate}</p>
    <p>${escapeHtml(health.uptime_note)}</p>
    <h2>Usage</h2>
    <p>New sign-ups: ${report.usage.new_signups} · Saves: ${report.usage.saves} · Click-outs: ${report.usage.click_outs}</p>
    <h2>Top searches</h2>
    <ul>${(report.usage.top_searches || []).map((row) => `<li>${escapeHtml(row.query)} (${row.n})</li>`).join("") || "<li>None yet</li>"}</ul>
  `;
}

init();
