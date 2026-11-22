/* Gatekeeper IP card — type: custom:gatekeeper-ip-card
 *
 * Opzioni / options (tutte facoltative / all optional):
 *   title: "Gatekeeper IP"
 *   show_history: true      # ultimi eventi / latest events
 *   history_items: 8
 *   show_ban_form: true     # campo per bannare / field to ban an IP
 *
 * La lingua segue quella di Home Assistant (italiano, altrimenti inglese).
 * The language follows Home Assistant (Italian, otherwise English).
 */
const I18N = {
  it: {
    durations: [["", "Permanente"], ["1", "1 ora"], ["24", "24 ore"], ["168", "7 giorni"], ["720", "30 giorni"]],
    placeholder: "IP da bannare, es. 45.12.33.7",
    ban: "🔒 Banna",
    unban: "🔓 Sblocca",
    banned_ips: "IP bannati",
    timed: "a tempo",
    failed: "login falliti 24h",
    latest: "Ultimi eventi",
    no_sensor: "Sensore di Gatekeeper IP non trovato",
    no_bans: "Nessun IP bannato 🎉",
    no_events: "Nessun evento",
    unknown_date: "data sconosciuta",
    until: "fino al",
    type_ip: "Scrivi un IP",
    msg_banned: "🔒 Bannato",
    msg_whitelisted: "IP in whitelist, non bannato",
    msg_already: "Già bannato",
    msg_done: "Fatto",
    msg_unbanned: "🔓 Sbloccato",
    confirm_unban: "Sbloccare {ip}?",
    description: "IP bannati, ban manuale e sblocco, login falliti e storico",
  },
  en: {
    durations: [["", "Permanent"], ["1", "1 hour"], ["24", "24 hours"], ["168", "7 days"], ["720", "30 days"]],
    placeholder: "IP to ban, e.g. 45.12.33.7",
    ban: "🔒 Ban",
    unban: "🔓 Unban",
    banned_ips: "banned IPs",
    timed: "timed",
    failed: "failed logins 24h",
    latest: "Latest events",
    no_sensor: "Gatekeeper IP sensor not found",
    no_bans: "No banned IPs 🎉",
    no_events: "No events",
    unknown_date: "unknown date",
    until: "until",
    type_ip: "Type an IP",
    msg_banned: "🔒 Banned",
    msg_whitelisted: "Whitelisted IP, not banned",
    msg_already: "Already banned",
    msg_done: "Done",
    msg_unbanned: "🔓 Unbanned",
    confirm_unban: "Unban {ip}?",
    description: "Banned IPs, manual ban and unban, failed logins and history",
  },
};

function langOf(hass) {
  const l = String((hass && ((hass.locale && hass.locale.language) || hass.language)) || navigator.language || "en");
  return l.toLowerCase().startsWith("it") ? "it" : "en";
}

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
    const lang = langOf(hass);
    if (lang !== this._lang) {
      this._lang = lang;
      this._built = false;
      this._lastKey = undefined;
    }
    if (!this._built) this._build();
    this._update();
  }

  get _t() {
    return I18N[this._lang || "en"];
  }

  _find(attr) {
    if (!this._hass) return undefined;
    return Object.values(this._hass.states).find(
      (s) => s.attributes && s.attributes.integration === "gatekeeper_ip" && attr in s.attributes
    );
  }

  _build() {
    const c = this._config;
    const T = this._t;
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
            <input class="gk-input" />
            <select class="gk-dur">${T.durations.map(([v, l]) => `<option value="${v}">${l}</option>`).join("")}</select>
            <button class="gk-btn gk-ban"></button>
          </div>
          <div class="gk-msg"></div>
          <div class="gk-section gk-sec-bans"></div>
          <div class="gk-list"></div>
          <div class="gk-hist-wrap" ${c.show_history ? "" : 'style="display:none"'}>
            <div class="gk-section gk-sec-hist"></div>
            <div class="gk-history"></div>
          </div>
        </div>
      </ha-card>`;
    this.querySelector(".gk-title").textContent = c.title;
    this.querySelector(".gk-input").placeholder = T.placeholder;
    this.querySelector(".gk-ban").textContent = T.ban;
    this.querySelector(".gk-sec-bans").textContent = T.banned_ips;
    this.querySelector(".gk-sec-hist").textContent = T.latest;
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
    const T = this._t;
    const bansEnt = this._find("bans");
    const failedEnt = this._find("per_ip");
    const histEnt = this._find("history") || this._find("storico");
    const bans = bansEnt ? bansEnt.attributes.bans || [] : [];
    const temp = bans.filter((b) => b.expires).length;
    const failed = failedEnt ? failedEnt.state : "–";

    const history = histEnt ? histEnt.attributes.history || histEnt.attributes.storico || [] : [];
    const key = JSON.stringify([bans, failed, history]);
    if (key === this._lastKey) return;
    this._lastKey = key;

    this.querySelector(".gk-stats").innerHTML = `
      <div class="gk-stat"><b>${bans.length}</b><span>${T.banned_ips}</span></div>
      <div class="gk-stat"><b>${temp}</b><span>${T.timed}</span></div>
      <div class="gk-stat"><b>${this._esc(failed)}</b><span>${T.failed}</span></div>`;

    const list = this.querySelector(".gk-list");
    if (!bansEnt) {
      list.innerHTML = `<div class="gk-empty">${T.no_sensor}</div>`;
    } else if (!bans.length) {
      list.innerHTML = `<div class="gk-empty">${T.no_bans}</div>`;
    } else {
      list.innerHTML = bans
        .map((b) => {
          const where = [b.country, b.city].filter(Boolean).join(", ");
          const sub = [b.banned_at || T.unknown_date, where, b.isp].filter(Boolean).join(" · ");
          const exp = b.expires ? `<div class="gk-sub gk-temp">⏱ ${T.until} ${this._esc(b.expires)}</div>` : "";
          return `<div class="gk-row">
              <div class="gk-flag">${b.flag || "🌐"}</div>
              <div class="gk-info"><div class="gk-ip">${this._esc(b.ip)}</div>
                <div class="gk-sub" title="${this._esc(sub)}">${this._esc(sub)}</div>${exp}</div>
              <button class="gk-btn unban" data-ip="${this._esc(b.ip)}">${T.unban}</button>
            </div>`;
        })
        .join("");
    }

    if (this._config.show_history) {
      const items = history.slice(0, this._config.history_items);
      this.querySelector(".gk-history").innerHTML = items.length
        ? items
            .map(
              (h) => `<div class="gk-hist"><time>${this._esc(h.time ?? h.quando)}</time>
                <span>${this._esc(h.action ?? h.azione)} ${this._esc(h.ip || "")} <small>(${this._esc((h.source ?? h.origine) || "")})</small></span></div>`
            )
            .join("")
        : `<div class="gk-empty">${T.no_events}</div>`;
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
    const T = this._t;
    const input = this.querySelector(".gk-input");
    const ip = input.value.trim();
    if (!ip) return this._msg(T.type_ip, true);
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
      if (r.banned && r.banned.length) this._msg(`${T.msg_banned}: ${r.banned.join(", ")}`);
      else if (r.whitelisted && r.whitelisted.length) this._msg(`${T.msg_whitelisted}: ${r.whitelisted.join(", ")}`, true);
      else if (r.already_banned && r.already_banned.length) this._msg(`${T.msg_already}: ${r.already_banned.join(", ")}`);
      else this._msg(T.msg_done);
      input.value = "";
    } catch (err) {
      // fallback senza risposta (versioni vecchie di HA) / fallback without response
      try {
        await this._hass.callService("gatekeeper_ip", "ban", data);
        this._msg(`${T.msg_banned}: ${ip}`);
        input.value = "";
      } catch (err2) {
        this._msg(err2.message || String(err2), true);
      }
    } finally {
      btn.disabled = false;
    }
  }

  async _unban(ip, btn) {
    const T = this._t;
    if (!confirm(T.confirm_unban.replace("{ip}", ip))) return;
    btn.disabled = true;
    try {
      await this._hass.callService("gatekeeper_ip", "unban", { ip });
      this._msg(`${T.msg_unbanned}: ${ip}`);
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
    description: I18N[langOf(null)].description,
    preview: true,
  });
}
