<p align="center">
  <img src="images/icon.png" alt="Gatekeeper IP" width="128">
</p>

<h1 align="center">Gatekeeper IP</h1>

<p align="center">
  <b>🇬🇧 English</b> · <a href="README.it.md">🇮🇹 Italiano</a>
</p>

<p align="center">
  Whitelist, manual and timed bans, detailed Telegram alerts with action buttons and a dashboard card<br>
  for the IP ban feature of <b>Home Assistant</b>.
</p>

<p align="center">
  <a href="https://github.com/hacs/integration"><img src="https://img.shields.io/badge/HACS-Custom-orange.svg" alt="HACS Custom"></a>
  <img src="https://img.shields.io/github/v/release/ichnusa82/gatekeeper_ip" alt="Release">
  <img src="https://img.shields.io/github/license/ichnusa82/gatekeeper_ip" alt="License">
</p>

---

Home Assistant can ban IPs after too many failed logins, but it has no whitelist, you can't ban an
IP manually from the UI, and unbanning means editing `ip_bans.yaml` and restarting.
**Gatekeeper IP** adds all of that.

## ✨ Features

| | |
|---|---|
| ✅ **Whitelist** | Whitelisted IPs and networks (e.g. `192.168.1.0/24`) are never banned, even after wrong passwords |
| 🔒 **Manual ban** | Type an IP and it is blocked immediately, no restart. Date and time are added automatically |
| ⏱ **Timed bans** | 1 hour, 24 hours, 7 days, 30 days: the IP is unbanned automatically when it expires |
| 🔓 **Unban** | From the list of banned IPs, with date/time, expiry, country and ISP. No restart |
| 📲 **Telegram alerts** | On every failed login: time, IP, browser and device, location, ISP, network type, requested URL, attempts this week, plus **Ban · Ban 24h · Whitelist · Ignore** buttons |
| 🌍 **IP location** | Flag, country, region, city, ISP and network type (mobile, fixed, datacenter/VPN) |
| 📜 **History** | Log of bans, unbans, expiries and whitelist changes, with the source of each action |
| 📈 **Failed logins** | Sensor with the attempts of the last 24 hours and a data-rich event for automations |
| 🧩 **Card** | Built-in dashboard card: counters, ban, unban and latest events |
| 💾 **Backup** | Export and import whitelist, bans (with expiry) and history as a YAML file |

It works on the same `ip_bans.yaml` used by Home Assistant: automatic bans after too many failed
logins keep working as before.

> The user interface is translated in English and Italian. The Telegram alert text and the
> device description (e.g. "Safari su iPhone") are currently in Italian.

## 📦 Installation

### HACS (recommended)
1. HACS → ⋮ menu (top right) → **Custom repositories**
2. Repository: `https://github.com/ichnusa82/gatekeeper_ip` — Type: **Integration**
3. Search for **Gatekeeper IP** in HACS and install it
4. Restart Home Assistant

### Manual
1. Download the latest [release](https://github.com/ichnusa82/gatekeeper_ip/releases)
2. Copy the `custom_components/gatekeeper_ip` folder into `/config/custom_components/`
3. Restart Home Assistant

### Setup
**Settings → Devices & services → Add integration → Gatekeeper IP**,
then enter the whitelist (one IP or network per line). The suggested value is `192.168.1.0/24`.

> **Requirement:** Home Assistant IP banning must be enabled
> (Settings → Network → *IP address banning*, or `ip_ban_enabled: true` in the `http:` section).
> The `ip_ban_attivo` attribute of the *Banned IPs* sensor shows whether it is active.

## ⚙️ Configure menu

On the integration page press **Configure**:

- 🔒 **Ban IPs manually** — one IP per line and the duration (permanent or timed).
  Optional: to set a different date, write it after the IP, e.g. `45.12.33.7 21/11/2026 01:42`
- 🔓 **Unban IPs** — tick the IPs to unban
- ✅ **Edit whitelist**
- ⚙️ **Settings** — Telegram alerts, Chat ID, IP location and ISP
- 📤 **Export backup** / 📥 **Import backup** — YAML file in the `/config` folder

Whitelisted IPs can't be banned; only single IPs are accepted, not networks
(`ip_bans.yaml` doesn't support them).

## 📲 Telegram alerts

Requires the [Telegram Bot](https://www.home-assistant.io/integrations/telegram_bot/) integration.
Enable them from **Configure → Settings** (Chat ID is optional: empty = default chat).

On every failed login from an IP **not** in the whitelist you get a message like this:

```
⚠️ LOGIN FALLITO HOME ASSISTANT
🕐 21/11/2026 19:06:34
🌐 IP: 93.38.176.139
🌍 Safari su iPhone
📍 Italy (IT) - Olgiate Comasco, Lombardy
🏢 Fastweb Networks
📶 Rete mobile
🔗 /auth/login_flow/c8f6c8c47fff17484de793c4536aa45e
🔢 Tentativi questa settimana: 10

[ 🔒 Banna ] [ ⏱ Banna 24 ore ]
[ ✅ Whitelist ] [ 🙈 Ignora ]
```

- **🌍 browser and device** and **🔗 requested URL** are read from the Home Assistant log
- **📶 network type**: mobile, 🏠 fixed line, or 🖥 datacenter / VPN / proxy
- **🔢 attempts**: from the same IP in the last 7 days

When you press a button, the message is updated with the result. To avoid flooding the chat, at
most one message per minute is sent for the same IP (all attempts are still counted).

## 🧩 Dashboard card

The card is bundled and registers itself: no need to add it to your resources.
**Edit dashboard → Add card → search "Gatekeeper"**, or use a manual card:

```yaml
type: custom:gatekeeper-ip-card
# optional
title: Gatekeeper IP
show_history: true     # latest events
history_items: 8
show_ban_form: true    # field to ban an IP manually
```

It shows the counters (banned IPs, timed bans, failed logins), a field to ban an IP with a duration,
the list of IPs with flag and **Unban** button, and the latest events.

## 📊 Sensors

Entity IDs depend on your Home Assistant language (English shown here).

| Entity | State | Main attributes |
|---|---|---|
| `sensor.gatekeeper_ip_banned_ips` | number of banned IPs | `bans`, `ip_bannati`, `temporanei`, `whitelist`, `ip_ban_attivo` |
| `sensor.gatekeeper_ip_failed_logins_24h` | failed logins in the last 24 hours | `per_ip`, `ultimo_ip`, `ultimo_host`, `ultimo_tentativo` |
| `sensor.gatekeeper_ip_last_event` | last ban/unban | `storico` (last 40 events) |

## 🛠 Services

| Service | Description |
|---|---|
| `gatekeeper_ip.ban` | Ban one or more IPs; optional `duration` |
| `gatekeeper_ip.unban` | Unban an IP or every IP in a network |
| `gatekeeper_ip.purge_whitelisted` | Unban all whitelisted IPs |
| `gatekeeper_ip.add_to_whitelist` | Add an IP/network to the whitelist (and unban it) |
| `gatekeeper_ip.remove_from_whitelist` | Remove an IP/network from the whitelist |
| `gatekeeper_ip.export` | Save a backup to `/config` |
| `gatekeeper_ip.import` | Import a backup from `/config` |
| `gatekeeper_ip.get_history` | Return the history |

```yaml
action: gatekeeper_ip.ban
data:
  ip: "45.12.33.7"
  duration: "24:00:00"   # optional
```

## 🤖 Automations

Every failed login fires the `gatekeeper_ip_login_failed` event with:

| Field | Content |
|---|---|
| `ip`, `host` | address and host name |
| `whitelisted` | `true` if the IP is whitelisted |
| `attempts_24h`, `attempts_week` | attempts from the same IP in the last 24 hours / 7 days |
| `device`, `user_agent` | e.g. "Safari su iPhone" and the full user agent |
| `url` | requested URL |
| `country`, `country_code`, `region`, `city` | location |
| `isp`, `mobile`, `hosting` | ISP, mobile network, datacenter/VPN |

Example: ban for 7 days at the third attempt from a foreign IP.

```yaml
triggers:
  - trigger: event
    event_type: gatekeeper_ip_login_failed
conditions:
  - condition: template
    value_template: >
      {{ not trigger.event.data.whitelisted
         and trigger.event.data.attempts_24h >= 3
         and trigger.event.data.country_code not in ['IT', None] }}
actions:
  - action: gatekeeper_ip.ban
    data:
      ip: "{{ trigger.event.data.ip }}"
      duration: "168:00:00"
```

## ❓ Troubleshooting

- **The card doesn't show up or says "custom element doesn't exist"** — reload the page with Ctrl+F5;
  in the app: App settings → Debug → Clear frontend cache.
- **After an update I still see the old version** — delete the `custom_components/gatekeeper_ip`
  folder (including `__pycache__`) before copying the new one, then do a full restart.
- **All IPs look the same (e.g. `172.30.33.x`)** — Home Assistant is behind a reverse proxy:
  configure `use_x_forwarded_for` and `trusted_proxies`, otherwise Home Assistant sees the proxy's IP.
- **Browser and URL are missing from the Telegram alert** — they are read from the Home Assistant log:
  the `homeassistant.components.http.ban` logger must be at `warning` level or lower (the default).
- **I get two messages for each attempt** — another automation of yours also notifies failed logins: disable one.

## 🔐 Privacy

- If *IP location* is enabled, **external** IPs are sent to the free [ip-api.com](https://ip-api.com)
  service (results cached for 30 days). Local network IPs are never sent.
  It can be disabled from Configure → Settings.
- History, failed logins (last 7 days) and cache are stored in `/config/.storage/gatekeeper_ip.data`.

## 📝 Changelog

See the [CHANGELOG](CHANGELOG.md) (in Italian).

## 📄 License

[MIT](LICENSE) © 2026 ichnusa82
