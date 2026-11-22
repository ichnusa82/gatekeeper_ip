# Changelog

## 1.2.0
🇬🇧
- Fully bilingual: the language follows Home Assistant (Italian, otherwise English) — Telegram alerts and buttons,
  device description, ban durations, unban list, history, dashboard card, sensor attribute labels,
  service error messages
- ⚠️ **Breaking:** sensor attributes renamed to English: `ip_bannati` → `banned`, `temporanei` → `timed`,
  `ip_ban_attivo` → `ip_ban_enabled`, `ultimo_ip` → `last_ip`, `ultimo_host` → `last_host`,
  `ultimo_tentativo` → `last_attempt`, `storico` → `history` (items: `time`, `action`, `ip`, `source`, `note`).
  Update your templates if you used them. The bundled card is already updated.
- Logs, backup file and `get_history` response keys in English
- Large attributes are no longer stored in the recorder database

🇮🇹
- Completamente bilingue: la lingua segue quella di Home Assistant (italiano, altrimenti inglese) — messaggi e
  pulsanti Telegram, dispositivo, durate, lista di sblocco, storico, card, nomi degli attributi dei sensori,
  messaggi di errore dei servizi
- ⚠️ **Attenzione:** attributi dei sensori rinominati in inglese (vedi sopra). Aggiorna i template se li usavi.
  La card inclusa è già aggiornata.
- Registro di sistema, file di backup e risposta di `get_history` in inglese
- Gli attributi più grandi non vengono più salvati nel database dello storico

## 1.1.1
🇬🇧 Telegram: after pressing a button the alert is updated with the result and the buttons are removed.

🇮🇹 Telegram: dopo aver premuto un pulsante il messaggio si aggiorna con l'esito e i pulsanti spariscono.

## 1.1.0
🇬🇧
- Detailed Telegram alert: time, browser/device, country with region and city, ISP, network type
  (mobile, fixed, datacenter/VPN), requested URL, attempts this week
- Telegram: `chat_id` instead of the deprecated `target` (removed in Home Assistant 2026.9)
- New fields in the `gatekeeper_ip_login_failed` event
- README in English and Italian

🇮🇹
- Messaggio Telegram dettagliato: ora, browser/dispositivo, paese con regione e città, provider, tipo di rete
  (mobile, fissa, datacenter/VPN), pagina richiesta, tentativi della settimana
- Telegram: `chat_id` al posto di `target`, deprecato (rimosso in Home Assistant 2026.9)
- Nuovi campi nell'evento `gatekeeper_ip_login_failed`
- README in inglese e italiano

## 1.0.0
🇬🇧 First release: IP whitelist, manual and timed bans, unban without restart, Telegram alerts with buttons,
IP geolocation, history, failed-login sensor and event, dashboard card, backup export/import.

🇮🇹 Prima pubblicazione: whitelist IP, ban manuali e a tempo, sblocco senza riavvio, avvisi Telegram con pulsanti,
posizione degli IP, storico, sensore ed evento dei login falliti, card per la dashboard, backup.
