<p align="center">
  <img src="images/icon.png" alt="Gatekeeper IP" width="128">
</p>

<h1 align="center">Gatekeeper IP</h1>

<p align="center">
  <a href="README.md">🇬🇧 English</a> · <b>🇮🇹 Italiano</b>
</p>

<p align="center">
  Whitelist, ban manuali e a tempo, avvisi Telegram dettagliati con pulsanti e card per la dashboard,<br>
  per il blocco degli indirizzi IP di <b>Home Assistant</b>.
</p>

<p align="center">
  <a href="https://github.com/hacs/integration"><img src="https://img.shields.io/badge/HACS-Custom-orange.svg" alt="HACS Custom"></a>
  <img src="https://img.shields.io/github/v/release/ichnusa82/gatekeeper_ip" alt="Release">
  <img src="https://img.shields.io/github/license/ichnusa82/gatekeeper_ip" alt="Licenza">
</p>

---

Home Assistant può bannare gli IP che sbagliano la password troppe volte, ma non ha una whitelist,
non permette di bannare un IP a mano dall'interfaccia e per sbloccarlo bisogna modificare
`ip_bans.yaml` e riavviare. **Gatekeeper IP** aggiunge tutto questo.

## ✨ Funzioni

| | |
|---|---|
| ✅ **Whitelist** | Gli IP e le reti in whitelist (es. `192.168.1.0/24`) non vengono mai bannati, anche se sbagliano la password |
| 🔒 **Ban manuale** | Scrivi l'IP e viene bloccato subito, senza riavvio. Data e ora vengono messe in automatico |
| ⏱ **Ban a tempo** | 1 ora, 24 ore, 7 giorni, 30 giorni: allo scadere l'IP viene sbloccato da solo |
| 🔓 **Sblocco** | Dalla lista degli IP bannati, con data/ora, scadenza, paese e provider. Senza riavvio |
| 📲 **Avvisi Telegram** | A ogni login fallito: ora, IP, browser e dispositivo, posizione, provider, tipo di rete, pagina richiesta, tentativi della settimana e i pulsanti **Banna · Banna 24 ore · Whitelist · Ignora** |
| 🌍 **Posizione dell'IP** | Bandiera, paese, regione, città, provider e tipo di rete (mobile, fissa, datacenter/VPN) |
| 📜 **Storico** | Registro di ban, sblocchi, scadenze e modifiche alla whitelist, con l'origine di ogni azione |
| 📈 **Login falliti** | Sensore con i tentativi delle ultime 24 ore ed evento ricco di dati per le automazioni |
| 🧩 **Card** | Card per la dashboard già inclusa: contatori, ban, sblocco e ultimi eventi |
| 💾 **Backup** | Esporta e importa whitelist, ban (con scadenze) e storico in un file YAML |

Funziona sullo stesso `ip_bans.yaml` usato da Home Assistant: i ban automatici dopo troppi tentativi
sbagliati continuano a funzionare come prima.

## 📦 Installazione

### Con HACS (consigliato)
1. HACS → menu ⋮ in alto a destra → **Repository personalizzati**
2. Repository: `https://github.com/ichnusa82/gatekeeper_ip` — Tipo: **Integrazione**
3. Cerca **Gatekeeper IP** in HACS e installa
4. Riavvia Home Assistant

### Manuale
1. Scarica l'ultima [release](https://github.com/ichnusa82/gatekeeper_ip/releases)
2. Copia la cartella `custom_components/gatekeeper_ip` in `/config/custom_components/`
3. Riavvia Home Assistant

### Configurazione
**Impostazioni → Dispositivi e servizi → Aggiungi integrazione → Gatekeeper IP**,
poi inserisci la whitelist (un IP o una rete per riga). Il valore proposto è `192.168.1.0/24`.

> **Requisito:** il blocco IP di Home Assistant deve essere attivo
> (Impostazioni → Rete → *Blocco degli indirizzi IP*, oppure `ip_ban_enabled: true` nella sezione `http:`).
> L'attributo `ip_ban_attivo` del sensore *IP bannati* indica se è attivo.

## ⚙️ Menu Configura

Dalla pagina dell'integrazione premi **Configura**:

- 🔒 **Banna IP manualmente** — un IP per riga e la durata (permanente o a tempo).
  Facoltativo: per una data diversa scrivila dopo l'IP, es. `45.12.33.7 21/11/2026 01:42`
- 🔓 **Sblocca IP bannati** — spunta gli IP da sbloccare
- ✅ **Modifica whitelist**
- ⚙️ **Impostazioni** — avvisi Telegram, Chat ID, posizione e provider degli IP
- 📤 **Esporta backup** / 📥 **Importa backup** — file YAML nella cartella `/config`

Gli IP in whitelist non si possono bannare; sono accettati solo singoli IP, non reti
(`ip_bans.yaml` non le supporta).

## 📲 Avvisi Telegram

Serve l'integrazione [Telegram Bot](https://www.home-assistant.io/integrations/telegram_bot/) già configurata.
Attivali da **Configura → Impostazioni** (il Chat ID è facoltativo: vuoto = chat predefinita).

A ogni login fallito da un IP **non** in whitelist arriva un messaggio così:

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

- **🌍 browser e dispositivo** e **🔗 pagina richiesta** vengono letti dal registro di Home Assistant
- **📶 tipo di rete**: rete mobile, 🏠 rete fissa oppure 🖥 datacenter / VPN / proxy
- **🔢 tentativi**: dello stesso IP negli ultimi 7 giorni

Premuto un pulsante, il messaggio si aggiorna con l'esito. Per non intasare la chat arriva al
massimo un messaggio al minuto per lo stesso IP (i tentativi vengono comunque contati tutti).

## 🧩 Card per la dashboard

La card è inclusa e si registra da sola: non serve aggiungerla alle risorse.
**Modifica dashboard → Aggiungi scheda → cerca "Gatekeeper"**, oppure scheda manuale:

```yaml
type: custom:gatekeeper-ip-card
# opzioni facoltative
title: Gatekeeper IP
show_history: true     # ultimi eventi
history_items: 8
show_ban_form: true    # campo per bannare a mano
```

Mostra i contatori (IP bannati, a tempo, login falliti), un campo per bannare con la durata,
la lista degli IP con bandiera e pulsante **Sblocca**, e gli ultimi eventi.

## 📊 Sensori

I nomi delle entità qui sotto sono quelli con Home Assistant in italiano.

| Entità | Stato | Attributi principali |
|---|---|---|
| `sensor.gatekeeper_ip_ip_bannati` | numero di IP bannati | `bans`, `ip_bannati`, `temporanei`, `whitelist`, `ip_ban_attivo` |
| `sensor.gatekeeper_ip_login_falliti_24_ore` | login falliti nelle ultime 24 ore | `per_ip`, `ultimo_ip`, `ultimo_host`, `ultimo_tentativo` |
| `sensor.gatekeeper_ip_ultimo_evento` | ultimo ban/sblocco | `storico` (ultimi 40 eventi) |

## 🛠 Servizi

| Servizio | Descrizione |
|---|---|
| `gatekeeper_ip.ban` | Banna uno o più IP; `duration` facoltativa |
| `gatekeeper_ip.unban` | Sblocca un IP o tutti gli IP di una rete |
| `gatekeeper_ip.purge_whitelisted` | Sblocca tutti gli IP in whitelist |
| `gatekeeper_ip.add_to_whitelist` | Aggiunge un IP/rete alla whitelist (e lo sblocca) |
| `gatekeeper_ip.remove_from_whitelist` | Toglie un IP/rete dalla whitelist |
| `gatekeeper_ip.export` | Salva un backup in `/config` |
| `gatekeeper_ip.import` | Importa un backup da `/config` |
| `gatekeeper_ip.get_history` | Restituisce lo storico |

```yaml
action: gatekeeper_ip.ban
data:
  ip: "45.12.33.7"
  duration: "24:00:00"   # facoltativa
```

## 🤖 Automazioni

A ogni login fallito viene generato l'evento `gatekeeper_ip_login_failed` con:

| Campo | Contenuto |
|---|---|
| `ip`, `host` | indirizzo e nome dell'host |
| `whitelisted` | `true` se l'IP è in whitelist |
| `attempts_24h`, `attempts_week` | tentativi dello stesso IP nelle ultime 24 ore / 7 giorni |
| `device`, `user_agent` | es. "Safari su iPhone" e user agent completo |
| `url` | pagina richiesta |
| `country`, `country_code`, `region`, `city` | posizione (paesi in inglese, es. "Italy") |
| `isp`, `mobile`, `hosting` | provider, rete mobile, datacenter/VPN |

Esempio: ban per 7 giorni al terzo tentativo da un IP estero.

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

## ❓ Problemi frequenti

- **La card non compare o dice "custom element doesn't exist"** — ricarica la pagina con Ctrl+F5;
  nell'app: Impostazioni app → Debug → Svuota cache del frontend.
- **Dopo un aggiornamento vedo ancora la versione vecchia** — cancella la cartella
  `custom_components/gatekeeper_ip` (compresa `__pycache__`) prima di copiare quella nuova e fai un riavvio completo.
- **Tutti gli IP risultano uguali (es. `172.30.33.x`)** — Home Assistant è dietro un reverse proxy:
  configura `use_x_forwarded_for` e `trusted_proxies`, altrimenti Home Assistant vede l'IP del proxy.
- **Nel messaggio Telegram mancano browser e pagina** — vengono letti dal registro di Home Assistant:
  il logger `homeassistant.components.http.ban` deve essere almeno a livello `warning` (è il valore predefinito).
- **Ricevo due messaggi per ogni tentativo** — hai anche un'altra automazione che avvisa dei login falliti: disattivane una.

## 🔐 Privacy

- Se attivi *posizione e provider*, gli IP **esterni** vengono inviati al servizio gratuito
  [ip-api.com](https://ip-api.com) (risultato in cache per 30 giorni). Gli IP della rete locale non vengono inviati.
  Si disattiva da Configura → Impostazioni.
- Storico, tentativi falliti (ultimi 7 giorni) e cache restano in `/config/.storage/gatekeeper_ip.data`.

## 📝 Novità

Vedi il [CHANGELOG](CHANGELOG.md).

## 📄 Licenza

[MIT](LICENSE) © 2026 ichnusa82
