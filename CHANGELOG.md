# Changelog

## 1.1.0
- Nuovo messaggio Telegram: ora, browser e dispositivo, paese con regione e città, provider,
  tipo di rete (mobile, fissa, datacenter/VPN), pagina richiesta, tentativi della settimana
- Evento `gatekeeper_ip_login_failed` con i nuovi campi `attempts_week`, `device`, `user_agent`,
  `url`, `country_code`, `region`, `mobile`, `hosting`
- Paesi in inglese (es. "Italy"), come restituiti da ip-api.com
- I tentativi falliti restano in memoria 7 giorni (il sensore continua a contare le ultime 24 ore)

## 1.0.1
- Telegram: usato `chat_id` al posto di `target`, deprecato e rimosso in Home Assistant 2026.9 (resta come riserva per le versioni più vecchie)

## 1.0.0 — prima pubblicazione
- Whitelist di IP e reti che Home Assistant non banna mai
- Ban manuale dal menu Configura, dalla card o con il servizio `ban` (data e ora automatiche)
- Ban a tempo (1 ora, 24 ore, 7 giorni, 30 giorni) con sblocco automatico
- Sblocco dalla lista degli IP bannati, senza riavvio
- Avvisi Telegram sui login falliti con pulsanti Banna / Banna 24 ore / Whitelist / Ignora
- Paese, città e provider degli IP (ip-api.com, disattivabile)
- Storico di ban, sblocchi, scadenze e modifiche alla whitelist
- Sensori "IP bannati", "Login falliti 24 ore", "Ultimo evento" ed evento `gatekeeper_ip_login_failed`
- Card per la dashboard inclusa (`custom:gatekeeper-ip-card`)
- Esporta / importa backup
