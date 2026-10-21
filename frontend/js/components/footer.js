/** Three equal footer columns: contact, socials, mailing list. */
import { api, ApiError } from "../utils/api.js";
import { qs } from "../utils/dom.js";

export function renderFooter() {
  const mount = document.getElementById("site-footer");
  if (!mount) return;
  const year = new Date().getFullYear();

  mount.innerHTML = `
    <footer class="site-footer">
      <div class="container footer-grid">
        <div class="footer-col">
          <h4>Contact us</h4>
          <a href="mailto:funkies254@gmail.com">funkies254@gmail.com</a>
          <p>Questions or an event to suggest? Email us.</p>
        </div>
        <div class="footer-col">
          <h4>Follow us</h4>
          <div class="footer-socials">
            <a href="https://www.instagram.com/funkies.254/" aria-label="Instagram" target="_blank" rel="noopener">
              <img src="/assets/images/icon-instagram.svg" alt="" />
            </a>
            <a href="https://www.linkedin.com/in/funkies-kenya-367880420" aria-label="LinkedIn" target="_blank" rel="noopener">
              <img src="/assets/images/icon-linkedin.svg" alt="" />
            </a>
            <a href="https://www.tiktok.com/@funkies254" aria-label="TikTok" target="_blank" rel="noopener">
              <img src="/assets/images/icon-tiktok.svg" alt="" />
            </a>
          </div>
        </div>
        <div class="footer-col">
          <h4>Mailing list</h4>
          <form class="mailing-form" id="mailing-form">
            <input type="email" name="email" placeholder="Email" required />
            <button class="btn btn-primary btn-sm" type="submit">Subscribe</button>
          </form>
          <p id="mailing-status" class="mailing-status" role="status"></p>
        </div>
      </div>
      <p class="footer-bottom">© ${year} Funkies 254 · <a href="/pages/about.html">About</a></p>
    </footer>
  `;

  qs("#mailing-form", mount).addEventListener("submit", async (event) => {
    event.preventDefault();
    const status = qs("#mailing-status", mount);
    const email = new FormData(event.target).get("email");
    try {
      await api.post("/newsletter/", { email });
      status.textContent = "You're subscribed. We'll be in touch.";
      event.target.reset();
    } catch (err) {
      status.textContent = err instanceof ApiError ? err.message : "Enter a valid email address.";
    }
  });
}
