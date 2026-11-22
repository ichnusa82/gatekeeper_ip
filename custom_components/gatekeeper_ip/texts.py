"""Testi mostrati da Gatekeeper IP fuori dall'interfaccia standard di Home Assistant.

Messaggi Telegram, storico, durate, lista di sblocco: la lingua segue quella
impostata in Home Assistant (italiano se è italiano, altrimenti inglese).
"""

from __future__ import annotations

from typing import Any

TEXTS: dict[str, dict[str, str]] = {
    "it": {
        # storico: azioni
        "action_ban": "Bannato",
        "action_unban": "Sbloccato",
        "action_expired": "Ban scaduto",
        "action_ban_prevented": "Ban evitato (whitelist)",
        "action_whitelist_add": "Aggiunto alla whitelist",
        "action_whitelist_remove": "Tolto dalla whitelist",
        "action_export": "Esportazione",
        "action_import": "Importazione",
        # storico: origine
        "source_auto": "automatico",
        "source_manual": "manuale",
        "source_telegram": "Telegram",
        "source_service": "servizio",
        "source_card": "card",
        "source_scadenza": "scadenza",
        "source_whitelist": "whitelist",
        "source_import": "importazione",
        # storico: note
        "note_too_many": "troppi tentativi falliti",
        "note_in_whitelist": "IP in whitelist",
        "note_timed": "per {duration} (fino al {expires})",
        "note_import": "{file}: {bans} ban, {nets} reti in whitelist",
        "note_file": "{file}",
        # durate
        "dur_day": "giorno",
        "dur_days": "giorni",
        "dur_hour": "ora",
        "dur_hours": "ore",
        "dur_min": "min",
        "dur_less": "meno di un minuto",
        # elenchi
        "unknown_date": "data sconosciuta",
        "until": "fino al {date}",
        "local_network": "Rete locale",
        # dispositivo
        "ua_on": "{browser} su {device}",
        "ua_app": "App Home Assistant",
        # Telegram
        "tg_title": "LOGIN FALLITO HOME ASSISTANT",
        "tg_mobile": "Rete mobile",
        "tg_fixed": "Rete fissa",
        "tg_hosting": "Datacenter / VPN / proxy",
        "tg_attempts": "Tentativi questa settimana: {n}",
        "btn_ban": "Banna",
        "btn_ban24": "Banna 24 ore",
        "btn_whitelist": "Whitelist",
        "btn_ignore": "Ignora",
        "res_banned": "{ip} bannato",
        "res_banned24": "{ip} bannato per 24 ore",
        "res_whitelisted": "{ip} è in whitelist: non bannato",
        "res_already": "{ip} era già bannato",
        "res_whitelist_added": "{ip} aggiunto alla whitelist",
        "res_ignored": "Ignorato",
    },
    "en": {
        "action_ban": "Banned",
        "action_unban": "Unbanned",
        "action_expired": "Ban expired",
        "action_ban_prevented": "Ban prevented (whitelist)",
        "action_whitelist_add": "Added to whitelist",
        "action_whitelist_remove": "Removed from whitelist",
        "action_export": "Export",
        "action_import": "Import",
        "source_auto": "automatic",
        "source_manual": "manual",
        "source_telegram": "Telegram",
        "source_service": "service",
        "source_card": "card",
        "source_scadenza": "expiry",
        "source_whitelist": "whitelist",
        "source_import": "import",
        "note_too_many": "too many failed logins",
        "note_in_whitelist": "IP is whitelisted",
        "note_timed": "for {duration} (until {expires})",
        "note_import": "{file}: {bans} bans, {nets} whitelist networks",
        "note_file": "{file}",
        "dur_day": "day",
        "dur_days": "days",
        "dur_hour": "hour",
        "dur_hours": "hours",
        "dur_min": "min",
        "dur_less": "less than a minute",
        "unknown_date": "unknown date",
        "until": "until {date}",
        "local_network": "Local network",
        "ua_on": "{browser} on {device}",
        "ua_app": "Home Assistant app",
        "tg_title": "HOME ASSISTANT FAILED LOGIN",
        "tg_mobile": "Mobile network",
        "tg_fixed": "Fixed line",
        "tg_hosting": "Datacenter / VPN / proxy",
        "tg_attempts": "Attempts this week: {n}",
        "btn_ban": "Ban",
        "btn_ban24": "Ban 24h",
        "btn_whitelist": "Whitelist",
        "btn_ignore": "Ignore",
        "res_banned": "{ip} banned",
        "res_banned24": "{ip} banned for 24 hours",
        "res_whitelisted": "{ip} is whitelisted: not banned",
        "res_already": "{ip} was already banned",
        "res_whitelist_added": "{ip} added to the whitelist",
        "res_ignored": "Ignored",
    },
}


def lang_of(hass: Any) -> str:
    """'it' se Home Assistant è in italiano, altrimenti 'en'."""
    language = str(getattr(getattr(hass, "config", None), "language", None) or "en").lower()
    return "it" if language.startswith("it") else "en"


def t(lang: str, key: str, **params: Any) -> str:
    text = TEXTS.get(lang, TEXTS["en"]).get(key) or TEXTS["en"].get(key, key)
    return text.format(**params) if params else text


def action_label(lang: str, action: str | None) -> str:
    return t(lang, f"action_{action}") if f"action_{action}" in TEXTS["en"] else str(action or "")


def source_label(lang: str, source: str | None) -> str:
    if not source:
        return ""
    return t(lang, f"source_{source}") if f"source_{source}" in TEXTS["en"] else str(source)
