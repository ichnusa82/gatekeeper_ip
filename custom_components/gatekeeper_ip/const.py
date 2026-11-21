"""Costanti per Gatekeeper IP."""

DOMAIN = "gatekeeper_ip"
VERSION = "1.0.0"

# Opzioni
CONF_WHITELIST = "whitelist"
CONF_TELEGRAM = "telegram"
CONF_CHAT_ID = "chat_id"
CONF_GEO = "geo"
CONF_IPS = "ips"
CONF_DURATION = "duration"
CONF_FILENAME = "filename"

# File e storage
IP_BANS_FILE = "ip_bans.yaml"
ATTR_BANNED_AT = "banned_at"
STORAGE_KEY = f"{DOMAIN}.data"
STORAGE_VERSION = 1
HISTORY_MAX = 300
FAILED_MAX = 2000
GEO_CACHE_MAX = 1000
DEFAULT_EXPORT = "gatekeeper_ip_backup.yaml"

# Segnali / eventi
SIGNAL_UPDATED = f"{DOMAIN}_updated"
EVENT_LOGIN_FAILED = f"{DOMAIN}_login_failed"
NOTIFICATION_ID_LOGIN = "http-login"

# Geolocalizzazione (gratuita, senza chiave, max 45 richieste/min)
GEO_URL = (
    "http://ip-api.com/json/{ip}?fields=status,message,country,countryCode,city,isp,org&lang=it"
)

# Card
CARD_URL = "/gatekeeper_ip/gatekeeper-ip-card.js"

# Servizi
SERVICE_BAN = "ban"
SERVICE_UNBAN = "unban"
SERVICE_PURGE = "purge_whitelisted"
SERVICE_ADD = "add_to_whitelist"
SERVICE_REMOVE = "remove_from_whitelist"
SERVICE_EXPORT = "export"
SERVICE_IMPORT = "import"
SERVICE_HISTORY = "get_history"

ATTR_IP = "ip"
ATTR_UNBAN = "unban"
ATTR_DURATION = "duration"
ATTR_FILENAME = "filename"
ATTR_LIMIT = "limit"

# Durate proposte nel menu (minuti → etichetta)
DURATION_CHOICES = {
    "0": "Permanente",
    "60": "1 ora",
    "1440": "24 ore",
    "10080": "7 giorni",
    "43200": "30 giorni",
}

ACTION_LABELS = {
    "ban": "Bannato",
    "unban": "Sbloccato",
    "expired": "Ban scaduto",
    "ban_prevented": "Ban evitato (whitelist)",
    "whitelist_add": "Aggiunto alla whitelist",
    "whitelist_remove": "Tolto dalla whitelist",
    "export": "Esportazione",
    "import": "Importazione",
}

SOURCE_LABELS = {
    "auto": "automatico",
    "manual": "manuale",
    "telegram": "Telegram",
    "service": "servizio",
    "card": "card",
    "scadenza": "scadenza",
    "whitelist": "whitelist",
    "import": "importazione",
}
