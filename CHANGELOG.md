# Changelog

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
