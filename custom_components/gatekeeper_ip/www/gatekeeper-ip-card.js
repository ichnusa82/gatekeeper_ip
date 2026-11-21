/* Gatekeeper IP card — type: custom:gatekeeper-ip-card
 *
 * Opzioni (tutte facoltative):
 *   title: "Gatekeeper IP"
 *   show_history: true      # ultimi eventi
 *   history_items: 8
 *   show_ban_form: true     # campo per bannare a mano
 */
const DURATIONS = [
  ["", "Permanente"],
  ["1", "1 ora"],
  ["24", "24 ore"],
  ["168", "7 giorni"],
  ["720", "30 giorni"],
];

class GatekeeperIpCard extends HTMLElement {
  setConfig(config) {
    this._config = {
      title: "Gatekeeper IP",
      show_history: true,
      history_items: 8,
      show_ban_form: true,
      ...config,
    };
    this._built = false;
  }

  static getStubConfig() {
    return {};
  }

  getCardSize() {
    return 6;
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._built) this._build();
    this._update();
  }

  _find(attr) {
    if (!this._hass) return undefined;
    return Object.values(this._hass.states).find(
      (s) => s.attributes && s.attributes.integration === "gatekeeper_ip" && attr in s.attributes
    );
  }

  _build() {
    const c = this._config;
    this.innerHTML = `
      <ha-card>
        <style>
          .gk { padding: 16px; }
          .gk-head { display:flex; align-items:center; gap:12px; margin-bottom:12px; }
          .gk-head ha-icon { --mdc-icon-size: 32px; color: var(--primary-color); }
          .gk-title { font-size: 1.25em; font-weight: 500; flex:1; }
          .gk-stats { display:flex; gap:8px; margin-bottom:12px; }
          .gk-stat { flex:1; background: var(--secondary-background-color); border-radius: 12px; padding: 8px 10px; text-align:center; }
          .gk-stat b { display:block; font-size: 1.5em; }
          .gk-stat span { font-size: .8em; color: var(--secondary-text-color); }
          .gk-form { display:flex; gap:8px; margin-bottom: 12px; flex-wrap: wrap; }
          .gk-form input, .gk-form select { flex:1; min-width: 120px; padding: 8px; border-radius: 8px;
            border: 1px solid var(--divider-color); background: var(--card-background-color); color: var(--primary-text-color); font-size: 14px; }
          .gk-form select { flex: 0 0 auto; }
          button.gk-btn { border:none; border-radius: 8px; padding: 8px 14px; cursor:pointer; font-weight:500;
            background: var(--error-color, #db4437); color: #fff; }
          button.gk-btn.unban { background: var(--success-color, #43a047); padding: 6px 10px; font-size: 12px; }
          button.gk-btn:disabled { opacity: .5; cursor: default; }
          .gk-msg { font-size: .85em; margin: -4px 0 10px; min-height: 1em; }
          .gk-msg.err { color: var(--error-color, #db4437); }
          .gk-section { font-weight:500; margin: 12px 0 6px; color: var(--secondary-text-color); text-transform: uppercase; font-size: .75em; letter-spacing: .05em; }
          .gk-row { display:flex; align-items:center; gap:10px; padding: 8px 0; border-bottom: 1px solid var(--divider-color); }
          .gk-row:last-child { border-bottom: none; }
          .gk-flag { font-size: 1.4em; width: 1.6em; text-align:center; }
          .gk-info { flex:1; min-width:0; }
          .gk-ip { font-family: monospace; font-size: 1.05em; }
          .gk-sub { font-size: .8em; color: var(--secondary-text-color); white-space: nowrap; overflow:hidden; text-overflow: ellipsis; }
          .gk-temp { color: var(--warning-color, #ff9800); }
          .gk-empty { color: var(--secondary-text-color); font-style: italic; padding: 8px 0; }
          .gk-hist { font-size: .85em; padding: 4px 0; display:flex; gap:8px; }
          .gk-hist time { color: var(--secondary-text-color); white-space: nowrap; }
        </style>
        <div class="gk">
          <div class="gk-head"><ha-icon icon="mdi:shield-lock"></ha-icon><div class="gk-title"></div></div>
          <div class="gk-stats"></div>
          <div class="gk-form" ${c.show_ban_form ? "" : 'style="display:none"'}>
            <input class="gk-input" placeholder="IP da bannare, es. 45.12.33.7" />
            <select class="gk-dur">${DURATIONS.map(([v, l]) => `<option value="${v}">${l}</option>`).join("")}</select>
            <button class="gk-btn gk-ban">🔒 Banna</button>
          </div>
          <div class="gk-msg"></div>
          <div class="gk-section">IP bannati</div>
          <div class="gk-list"></div>
          <div class="gk-hist-wrap" ${c.show_history ? "" : 'style="display:none"'}>
            <div class="gk-section">Ultimi eventi</div>
            <div class="gk-history"></div>
          </div>
        </div>
      </ha-card>`;
    this.querySelector(".gk-title").textContent = c.title;
    this.querySelector(".gk-ban").addEventListener("click", () => this._ban());
    this.querySelector(".gk-input").addEventListener("keydown", (e) => {
      if (e.key === "Enter") this._ban();
    });
    this.querySelector(".gk-list").addEventListener("click", (e) => {
      const btn = e.target.closest("button[data-ip]");
      if (btn) this._unban(btn.dataset.ip, btn);
    });
    this._built = true;
  }

  _esc(text) {
    return String(text ?? "").replace(/[&<>"']/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch]));
  }

  _update() {
    const bansEnt = this._find("bans");
    const failedEnt = this._find("per_ip");
    const histEnt = this._find("storico");
    const bans = bansEnt ? bansEnt.attributes.bans || [] : [];
    const temp = bans.filter((b) => b.expires).length;
    const failed = failedEnt ? failedEnt.state : "–";

    const key = JSON.stringify([bans, failed, histEnt && histEnt.attributes.storico]);
    if (key === this._lastKey) return;
    this._lastKey = key;

    this.querySelector(".gk-stats").innerHTML = `
      <div class="gk-stat"><b>${bans.length}</b><span>IP bannati</span></div>
      <div class="gk-stat"><b>${temp}</b><span>a tempo</span></div>
      <div class="gk-stat"><b>${this._esc(failed)}</b><span>login falliti 24h</span></div>`;

    const list = this.querySelector(".gk-list");
    if (!bansEnt) {
      list.innerHTML = `<div class="gk-empty">Sensore di Gatekeeper IP non trovato</div>`;
    } else if (!bans.length) {
      list.innerHTML = `<div class="gk-empty">Nessun IP bannato 🎉</div>`;
    } else {
      list.innerHTML = bans
        .map((b) => {
          const where = [b.country, b.city].filter(Boolean).join(", ");
          const sub = [b.banned_at || "data sconosciuta", where, b.isp].filter(Boolean).join(" · ");
          const exp = b.expires ? `<div class="gk-sub gk-temp">⏱ fino al ${this._esc(b.expires)}</div>` : "";
          return `<div class="gk-row">
              <div class="gk-flag">${b.flag || "🌐"}</div>
              <div class="gk-info"><div class="gk-ip">${this._esc(b.ip)}</div>
                <div class="gk-sub" title="${this._esc(sub)}">${this._esc(sub)}</div>${exp}</div>
              <button class="gk-btn unban" data-ip="${this._esc(b.ip)}">🔓 Sblocca</button>
            </div>`;
        })
        .join("");
    }

    if (this._config.show_history) {
      const items = histEnt ? (histEnt.attributes.storico || []).slice(0, this._config.history_items) : [];
      this.querySelector(".gk-history").innerHTML = items.length
        ? items
            .map(
              (h) => `<div class="gk-hist"><time>${this._esc(h.quando)}</time>
                <span>${this._esc(h.azione)} ${this._esc(h.ip || "")} <small>(${this._esc(h.origine || "")})</small></span></div>`
            )
            .join("")
        : `<div class="gk-empty">Nessun evento</div>`;
    }
  }

  _msg(text, error = false) {
    const el = this.querySelector(".gk-msg");
    el.textContent = text;
    el.className = "gk-msg" + (error ? " err" : "");
    clearTimeout(this._msgTimer);
    this._msgTimer = setTimeout(() => (el.textContent = ""), 6000);
  }

  async _ban() {
    const input = this.querySelector(".gk-input");
    const ip = input.value.trim();
    if (!ip) return this._msg("Scrivi un IP", true);
    const hours = this.querySelector(".gk-dur").value;
    const data = { ip };
    if (hours) data.duration = { hours: Number(hours) };
    const btn = this.querySelector(".gk-ban");
    btn.disabled = true;
    try {
      const res = await this._hass.callWS({
        type: "call_service",
        domain: "gatekeeper_ip",
        service: "ban",
        service_data: data,
        return_response: true,
      });
      const r = (res && res.response) || {};
      if (r.banned && r.banned.length) this._msg(`🔒 Bannato: ${r.banned.join(", ")}`);
      else if (r.whitelisted && r.whitelisted.length) this._msg(`IP in whitelist, non bannato: ${r.whitelisted.join(", ")}`, true);
      else if (r.already_banned && r.already_banned.length) this._msg(`Già bannato: ${r.already_banned.join(", ")}`);
      else this._msg("Fatto");
      input.value = "";
    } catch (err) {
      // fallback senza risposta (versioni vecchie di HA)
      try {
        await this._hass.callService("gatekeeper_ip", "ban", data);
        this._msg("🔒 Fatto");
        input.value = "";
      } catch (err2) {
        this._msg(err2.message || String(err2), true);
      }
    } finally {
      btn.disabled = false;
    }
  }

  async _unban(ip, btn) {
    if (!confirm(`Sbloccare ${ip}?`)) return;
    btn.disabled = true;
    try {
      await this._hass.callService("gatekeeper_ip", "unban", { ip });
      this._msg(`🔓 Sbloccato: ${ip}`);
    } catch (err) {
      this._msg(err.message || String(err), true);
      btn.disabled = false;
    }
  }
}

if (!customElements.get("gatekeeper-ip-card")) {
  customElements.define("gatekeeper-ip-card", GatekeeperIpCard);
  window.customCards = window.customCards || [];
  window.customCards.push({
    type: "gatekeeper-ip-card",
    name: "Gatekeeper IP",
    description: "IP bannati, ban manuale e sblocco, login falliti e storico",
    preview: true,
  });
}
