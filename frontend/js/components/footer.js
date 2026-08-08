/** Renders the shared footer (contact, socials + mailing list) into `<div id="site-footer"></div>`. */
import { qs } from "../utils/dom.js";
import { toast } from "../utils/toast.js";

export function renderFooter() {
  const mount = document.getElementById("site-footer");
  if (!mount) return;

  mount.innerHTML = `
    <footer class="site-footer">
      <div class="container footer-grid">
        <div class="footer-contact">
          <p>Not seeing an event on our platform?<br />Contact us on</p>
          <div class="footer-contact-line">
            <span aria-hidden="true">&#9993;&#65039;</span>
            <a href="mailto:funkies254@gmail.com">funkies254@gmail.com</a>
          </div>
          <div class="footer-contact-line">
            <img src="/assets/images/icon-whatsapp.svg" alt="" />
            <a href="https://wa.me/16092556544" target="_blank" rel="noopener">WhatsApp</a>
          </div>
        </div>
        <div class="footer-social">
          <p>Follow Funkies254 on social media :</p>
          <div class="footer-socials">
            <a href="https://www.instagram.com/funkies.254/" aria-label="Instagram" target="_blank" rel="noopener">
              <img src="/assets/images/icon-instagram.svg" alt="" />
              Instagram
            </a>
            <a href="https://www.linkedin.com/in/funkies-kenya-367880420" aria-label="LinkedIn" target="_blank" rel="noopener">
              <img src="/assets/images/icon-linkedin.svg" alt="" />
              LinkedIn
            </a>
            <a href="https://www.tiktok.com/@funkies254" aria-label="TikTok" target="_blank" rel="noopener">
              <img src="/assets/images/icon-tiktok.svg" alt="" />
              TikTok
            </a>
          </div>
        </div>
        <div class="mailing-card">
          <h4>Join the Mailing List?</h4>
          <p>Receive notifications for events that fit your <a href="/pages/preferences.html">preferences</a></p>
          <form class="mailing-form" id="mailing-form">
            <input type="email" placeholder="Email" required />
          </form>
        </div>
      </div>
      <p class="footer-bottom">&copy; ${new Date().getFullYear()} Funkies254. Built for Kenyan students, by Kenyan students.</p>
    </footer>
  `;

  qs("#mailing-form", mount).addEventListener("submit", (event) => {
    event.preventDefault();
    // Mailing list capture isn't wired to the backend yet — the form works,
    // it just confirms the intent for now. Swap this for a real API call
    // once a `subscribers` endpoint exists.
    toast.success("Thanks! We'll email you about events you'll love.");
    event.target.reset();
  });
}
