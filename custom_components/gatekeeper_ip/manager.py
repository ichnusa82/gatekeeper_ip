"""Nucleo di Gatekeeper IP.

- whitelist: impedisce a Home Assistant di bannare gli IP fidati
- ban manuali, anche temporanei, scritti in ip_bans.yaml
- storico di ban/sblocchi, tentativi di login falliti, geolocalizzazione
- avvisi Telegram con pulsanti, esportazione / importazione
"""

from __future__ import annotations

import asyncio
import contextlib
import html
import logging
import os
import re
from collections.abc import Callable, Iterable
from datetime import datetime, timedelta
from ipaddress import IPv4Address, IPv6Address, ip_address, ip_network
from typing import Any

import voluptuous as vol
import yaml
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.dispatcher import (
    async_dispatcher_connect,
    async_dispatcher_send,
)
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util
from homeassistant.util.yaml import dump

from .const import (
    ATTR_BANNED_AT,
    CONF_CHAT_ID,
    CONF_GEO,
    CONF_TELEGRAM,
    CONF_WHITELIST,
    DEFAULT_EXPORT,
    EVENT_LOGIN_FAILED,
    FAILED_MAX,
    GEO_CACHE_MAX,
    GEO_URL,
    HISTORY_MAX,
    IP_BANS_FILE,
    NOTIFICATION_ID_LOGIN,
    SIGNAL_UPDATED,
    STORAGE_KEY,
    STORAGE_VERSION,
)

_LOGGER = logging.getLogger(__name__)

IPAddr = IPv4Address | IPv6Address

# ============================================================== parsing input


def parse_whitelist(raw: str | Iterable[str] | None) -> list[str]:
    """Testo (righe / virgole) o lista → lista di reti CIDR valide.

    Solleva ValueError se una voce non è un IP o una rete valida.
    """
    if raw is None:
        return []
    if isinstance(raw, str):
        items = raw.replace(",", "\n").replace(";", "\n").splitlines()
    else:
        items = [str(i) for i in raw]
    result: list[str] = []
    for raw_item in items:
        item = raw_item.strip()
        if not item or item.startswith("#"):
            continue
        net = str(ip_network(item, strict=False))
        if net not in result:
            result.append(net)
    return result


_DATE_FORMATS = ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%d/%m/%Y")


def _local_tz():
    if hasattr(dt_util, "get_default_time_zone"):
        return dt_util.get_default_time_zone()
    return dt_util.DEFAULT_TIME_ZONE


def _parse_local_datetime(text: str) -> datetime:
    """'gg/mm/aaaa [hh:mm[:ss]]' in ora locale → datetime UTC."""
    text = " ".join(text.replace("-", "/").split())
    for fmt in _DATE_FORMATS:
        try:
            naive = datetime.strptime(text, fmt)
        except ValueError:
            continue
        return dt_util.as_utc(naive.replace(tzinfo=_local_tz()))
    raise ValueError(text)


def parse_ip_list(raw: str | Iterable[str] | None) -> list[tuple[str, datetime | None]]:
    """Righe 'IP [gg/mm/aaaa [hh:mm[:ss]]]' → [(ip, data UTC o None)].

    Solo singoli IP (ip_bans.yaml non accetta reti). Solleva ValueError
    con la voce non valida.
    """
    if raw is None:
        return []
    if isinstance(raw, str):
        items = raw.replace(",", "\n").replace(";", "\n").splitlines()
    else:
        items = [str(i) for i in raw]
    result: list[tuple[str, datetime | None]] = []
    seen: set[str] = set()
    for raw_item in items:
        item = raw_item.strip()
        if not item or item.startswith("#"):
            continue
        ip_text, _, date_text = item.partition(" ")
        try:
            ip = str(ip_address(ip_text.strip()))
            when = _parse_local_datetime(date_text) if date_text.strip() else None
        except ValueError as err:
            raise ValueError(item) from err
        if ip not in seen:
            seen.add(ip)
            result.append((ip, when))
    return result


# ================================================================ utilità


def parse_dt(value: Any) -> datetime | None:
    """datetime o stringa ISO → datetime con fuso (UTC se mancante)."""
    if value is None or value == "":
        return None
    if isinstance(value, str):
        value = dt_util.parse_datetime(value)
        if value is None:
            return None
    if not isinstance(value, datetime):
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=dt_util.UTC)
    return value


def fmt_local(value: Any) -> str | None:
    """→ 'gg/mm/aaaa hh:mm:ss' in ora locale."""
    when = parse_dt(value)
    if when is None:
        return None
    return dt_util.as_local(when).strftime("%d/%m/%Y %H:%M:%S")


def fmt_duration(delta: timedelta) -> str:
    minutes = int(delta.total_seconds() // 60)
    days, rest = divmod(minutes, 1440)
    hours, mins = divmod(rest, 60)
    parts = []
    if days:
        parts.append(f"{days} {'giorno' if days == 1 else 'giorni'}")
    if hours:
        parts.append(f"{hours} {'ora' if hours == 1 else 'ore'}")
    if mins:
        parts.append(f"{mins} min")
    return " ".join(parts) or "meno di un minuto"


def country_flag(code: str | None) -> str:
    if not code or len(code) != 2 or not code.isalpha():
        return ""
    return "".join(chr(0x1F1E6 + ord(c) - ord("A")) for c in code.upper())


def ip_sort_key(ip: str) -> tuple[int, int | str]:
    try:
        addr = ip_address(ip)
        return (addr.version, int(addr))
    except ValueError:
        return (9, ip)


def _to_iso(value: Any) -> str:
    when = parse_dt(value)
    return when.isoformat() if when else str(value)


def _read_yaml(path: str) -> Any:
    try:
        with open(path, encoding="utf-8") as file:
            return yaml.safe_load(file)
    except FileNotFoundError:
        return None


def _read_bans_file(path: str) -> dict:
    """ip_bans.yaml con PyYAML; file vuoto o malformato → {}."""
    try:
        data = _read_yaml(path)
    except yaml.YAMLError as err:
        _LOGGER.error("ip_bans.yaml non leggibile: %s", err)
        return {}
    return data if isinstance(data, dict) else {}


def _ban_module_key(name: str, fallback: str) -> Any:
    """AppKey del modulo http.ban (cambiano tra le versioni di HA)."""
    try:
        from homeassistant.components.http import ban  # noqa: PLC0415

        return getattr(ban, name)
    except (ImportError, AttributeError):
        return fallback


KEY_BAN_MANAGER = _ban_module_key("KEY_BAN_MANAGER", "ha_banned_ips_manager")
KEY_FAILED_LOGIN_ATTEMPTS = _ban_module_key("KEY_FAILED_LOGIN_ATTEMPTS", "ha_failed_login_attempts")

_LOGIN_MSG_RE = re.compile(r"from (.*?) \(([0-9A-Fa-f:.]+)\)")
_LOGIN_LOG_RE = re.compile(
    r"from (.*?) \(([0-9A-Fa-f:.]+)\)\. Requested URL: '(.*?)'\. \((.*)\)\s*$", re.S
)
BAN_LOGGER = "homeassistant.components.http.ban"


def describe_user_agent(ua: str | None) -> str | None:
    """User agent → 'Safari su iPhone', 'Chrome su Windows', 'App Home Assistant su Android'…"""
    if not ua or ua == "None":
        return None
    low = ua.lower()
    if "iphone" in low:
        device = "iPhone"
    elif "ipad" in low:
        device = "iPad"
    elif "android" in low:
        device = "Android"
    elif "windows" in low:
        device = "Windows"
    elif "macintosh" in low or "mac os x" in low:
        device = "Mac"
    elif "cros" in low:
        device = "ChromeOS"
    elif "linux" in low:
        device = "Linux"
    else:
        device = None

    if "home assistant/" in low or "homeassistant/" in low:
        browser = "App Home Assistant"
    elif "edg/" in low or "edga/" in low or "edgios/" in low:
        browser = "Edge"
    elif "opr/" in low or "opera" in low:
        browser = "Opera"
    elif "samsungbrowser" in low:
        browser = "Samsung Internet"
    elif "firefox/" in low or "fxios/" in low:
        browser = "Firefox"
    elif "chrome/" in low or "crios/" in low:
        browser = "Chrome"
    elif "safari/" in low or ("applewebkit" in low and device in ("iPhone", "iPad", "Mac")):
        browser = "Safari"
    elif low.startswith(("curl", "wget", "python", "go-http", "java", "okhttp", "postman")):
        return ua.split()[0][:60] + " (script)"
    else:
        browser = None

    if browser and device:
        return f"{browser} su {device}"
    return browser or device or ua[:80]


class _BanLogHandler(logging.Handler):
    """Legge dal log di HA l'URL richiesto e il browser di ogni login fallito."""

    def __init__(self, store: dict[str, dict[str, Any]]) -> None:
        super().__init__(logging.WARNING)
        self._store = store

    def emit(self, record: logging.LogRecord) -> None:
        try:
            match = _LOGIN_LOG_RE.search(record.getMessage())
            if not match:
                return
            ip = str(ip_address(match.group(2)))
            self._store[ip] = {"url": match.group(3), "ua": match.group(4)}
            while len(self._store) > 200:
                self._store.pop(next(iter(self._store)))
        except Exception:  # noqa: BLE001
            return


# ================================================================ manager


class GatekeeperManager:
    """Stato e logica dell'integrazione (una sola istanza)."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        opts = entry.options
        self.networks = [
            ip_network(n, strict=False) for n in parse_whitelist(opts.get(CONF_WHITELIST, []))
        ]
        self.telegram_enabled: bool = bool(opts.get(CONF_TELEGRAM, False))
        self.chat_id: str = str(opts.get(CONF_CHAT_ID, "") or "").strip()
        self.geo_enabled: bool = bool(opts.get(CONF_GEO, True))
        self.path = hass.config.path(IP_BANS_FILE)

        self._store: Store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self.data: dict[str, Any] = {
            "temp_bans": {},  # ip -> scadenza ISO (UTC)
            "history": [],  # [{time, action, ip, source, note}]
            "failed": [],  # [{time, ip, host}]
            "geo": {},  # ip -> {country, country_code, city, isp, time}
        }
        self.bans: list[dict[str, Any]] = []  # elenco pronto per sensori e card

        self._ban_manager: Any = None
        self._original_add_ban: Any = None
        self._unsubs: list[Callable[[], None]] = []
        self._last_telegram: dict[str, datetime] = {}
        self._geo_lock = asyncio.Lock()
        self._geo_task: asyncio.Task | None = None
        self._warned_no_telegram = False
        self._requests: dict[str, dict[str, Any]] = {}
        self._log_handler = _BanLogHandler(self._requests)

    # ------------------------------------------------------------ ciclo vita
    async def async_setup(self) -> None:
        stored = await self._store.async_load()
        if isinstance(stored, dict):
            for key, default in self.data.items():
                value = stored.get(key)
                if isinstance(value, type(default)):
                    self.data[key] = value

        self._attach()
        logging.getLogger(BAN_LOGGER).addHandler(self._log_handler)
        self._unsubs.append(lambda: logging.getLogger(BAN_LOGGER).removeHandler(self._log_handler))
        self._unsubs.append(self._listen_login_notifications())
        self._unsubs.append(
            self.hass.bus.async_listen("telegram_callback", self._on_telegram_callback)
        )
        self._unsubs.append(
            async_track_time_interval(self.hass, self._async_tick, timedelta(minutes=1))
        )

        await self.async_purge_whitelisted()
        await self._async_tick()

    async def async_unload(self) -> None:
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()
        if self._geo_task and not self._geo_task.done():
            self._geo_task.cancel()
        self._detach()
        await self._store.async_save(self.data)

    @callback
    def _save(self) -> None:
        self._store.async_delay_save(lambda: self.data, 2)

    @callback
    def _signal(self) -> None:
        async_dispatcher_send(self.hass, SIGNAL_UPDATED)

    # ----------------------------------------------------------------- storico
    @callback
    def log(self, action: str, ip: str | None = None, source: str = "", note: str = "") -> None:
        self.data["history"].append(
            {
                "time": dt_util.utcnow().isoformat(),
                "action": action,
                "ip": ip,
                "source": source,
                "note": note,
            }
        )
        del self.data["history"][:-HISTORY_MAX]
        self._save()
        self._signal()

    # --------------------------------------------------------------- whitelist
    def is_whitelisted(self, addr: str | IPAddr) -> bool:
        try:
            ip = ip_address(str(addr))
        except ValueError:
            return False
        if getattr(ip, "ipv4_mapped", None):
            ip = ip.ipv4_mapped
        return any(ip.version == net.version and ip in net for net in self.networks)

    @property
    def whitelist(self) -> list[str]:
        return [str(n) for n in self.networks]

    async def async_whitelist_add(
        self, nets: list[str], unban: bool = True, source: str = "manual"
    ) -> list[str]:
        """Aggiunge reti alla whitelist (l'integrazione poi si ricarica)."""
        nets = parse_whitelist(nets)
        current = self.whitelist
        new = [n for n in nets if n not in current]
        if unban:
            for net in nets:
                await self.async_unban(net, source=source)
        for net in new:
            self.log("whitelist_add", net, source)
        if new:
            await self._store.async_save(self.data)
            self.hass.config_entries.async_update_entry(
                self.entry, options={**self.entry.options, CONF_WHITELIST: current + new}
            )
        return new

    async def async_whitelist_remove(self, nets: list[str], source: str = "manual") -> list[str]:
        nets = parse_whitelist(nets)
        current = self.whitelist
        drop = [n for n in nets if n in current]
        for net in drop:
            self.log("whitelist_remove", net, source)
        if drop:
            await self._store.async_save(self.data)
            self.hass.config_entries.async_update_entry(
                self.entry,
                options={
                    **self.entry.options,
                    CONF_WHITELIST: [n for n in current if n not in drop],
                },
            )
        return drop

    # ---------------------------------------------------- aggancio ban manager
    @property
    def ban_enabled(self) -> bool:
        return self._ban_manager is not None

    def _app(self) -> Any:
        return getattr(getattr(self.hass, "http", None), "app", None)

    @callback
    def _attach(self) -> None:
        app = self._app()
        ban_manager = app.get(KEY_BAN_MANAGER) if app is not None else None
        if ban_manager is None:
            _LOGGER.warning(
                "Ban manager di Home Assistant non trovato (blocco IP disattivato?): "
                "la whitelist non ha effetto, i ban manuali valgono dal riavvio"
            )
            return
        self._ban_manager = ban_manager
        self._original_add_ban = ban_manager.async_add_ban
        manager = self

        async def async_add_ban_filtered(remote_addr: IPAddr) -> None:
            ip = str(remote_addr)
            if manager.is_whitelisted(ip):
                _LOGGER.warning("IP %s in whitelist: ban ignorato", ip)
                manager._reset_failed_attempts(remote_addr)
                manager.log("ban_prevented", ip, "auto", "troppi tentativi falliti")
                return
            await manager._original_add_ban(remote_addr)
            manager.log("ban", ip, "auto", "troppi tentativi falliti")
            await manager.async_refresh_bans()

        # attributo d'istanza: oscura il metodo di classe, rimovibile con delattr
        ban_manager.async_add_ban = async_add_ban_filtered

    @callback
    def _detach(self) -> None:
        if self._ban_manager is not None:
            with contextlib.suppress(AttributeError):
                delattr(self._ban_manager, "async_add_ban")
        self._ban_manager = None
        self._original_add_ban = None

    def _reset_failed_attempts(self, addr: IPAddr | str) -> None:
        app = self._app()
        attempts = app.get(KEY_FAILED_LOGIN_ATTEMPTS) if app is not None else None
        if attempts is None:
            return
        with contextlib.suppress(ValueError):
            attempts.pop(ip_address(str(addr)), None)

    # ------------------------------------------------------- lettura dei ban
    def _file_bans(self) -> dict[str, datetime | None]:
        data = _read_bans_file(self.path)
        return {
            str(ip): parse_dt(v.get(ATTR_BANNED_AT)) if isinstance(v, dict) else None
            for ip, v in data.items()
        }

    async def async_refresh_bans(self) -> list[dict[str, Any]]:
        """Ricostruisce l'elenco dei ban (file + memoria) con date, scadenze e geo."""
        merged = await self.hass.async_add_executor_job(self._file_bans)
        if self._ban_manager is not None:
            for ip, ban in self._ban_manager.ip_bans_lookup.items():
                when = getattr(ban, "banned_at", None)
                if when or str(ip) not in merged:
                    merged[str(ip)] = parse_dt(when)

        temp = self.data["temp_bans"]
        for ip in [ip for ip in temp if ip not in merged]:
            temp.pop(ip)
            self._save()

        bans = []
        for ip in sorted(merged, key=ip_sort_key):
            when = merged[ip]
            expires = parse_dt(temp.get(ip))
            geo = self.data["geo"].get(ip, {})
            bans.append(
                {
                    "ip": ip,
                    "banned_at": fmt_local(when),
                    "banned_at_iso": when.isoformat() if when else None,
                    "expires": fmt_local(expires),
                    "expires_iso": expires.isoformat() if expires else None,
                    "country": geo.get("country"),
                    "country_code": geo.get("country_code"),
                    "flag": country_flag(geo.get("country_code")),
                    "city": geo.get("city"),
                    "isp": geo.get("isp"),
                }
            )
        if bans != self.bans:
            self.bans = bans
            self._signal()
        if self.geo_enabled and any(b["ip"] not in self.data["geo"] for b in bans):
            self._start_geo_fill()
        return bans

    # ------------------------------------------------------------------- ban
    def _append_to_file(self, ip: str, when: datetime) -> None:
        with open(self.path, "a", encoding="utf-8") as out:
            out.write("\n" + dump({ip: {ATTR_BANNED_AT: when.isoformat()}}))

    def _add_to_memory(self, ip: str, when: datetime) -> None:
        if self._ban_manager is None:
            return
        try:
            from homeassistant.components.http.ban import IpBan  # noqa: PLC0415

            ban = IpBan(ip, when)
        except (ImportError, TypeError) as err:
            _LOGGER.debug("IpBan non disponibile (%s): ban attivo dal riavvio", err)
            return
        self._ban_manager.ip_bans_lookup[ban.ip_address] = ban

    async def async_ban(
        self,
        entries: list[tuple[str, datetime | None]] | list[str],
        duration: timedelta | None = None,
        source: str = "manual",
    ) -> dict[str, list[str]]:
        """Banna una lista di IP (data facoltativa), anche a tempo.

        Ritorna {"banned": [...], "whitelisted": [...], "already_banned": [...]}.
        """
        result: dict[str, list[str]] = {"banned": [], "whitelisted": [], "already_banned": []}
        already = {b["ip"] for b in await self.async_refresh_bans()}
        if duration is not None and duration.total_seconds() <= 0:
            duration = None
        for entry in entries:
            ip, when = (entry, None) if isinstance(entry, str) else entry
            ip = str(ip_address(str(ip)))
            if self.is_whitelisted(ip):
                result["whitelisted"].append(ip)
                continue
            if ip in already:
                result["already_banned"].append(ip)
                continue
            when = when or dt_util.utcnow()
            await self.hass.async_add_executor_job(self._append_to_file, ip, when)
            self._add_to_memory(ip, when)
            note = ""
            if duration:
                expires = dt_util.utcnow() + duration
                self.data["temp_bans"][ip] = expires.isoformat()
                note = f"per {fmt_duration(duration)} (fino al {fmt_local(expires)})"
            self.log("ban", ip, source, note)
            already.add(ip)
            result["banned"].append(ip)
        if result["banned"]:
            _LOGGER.warning("IP bannati (%s): %s", source, ", ".join(result["banned"]))
            self._save()
            await self.async_refresh_bans()
        return result

    # ---------------------------------------------------------------- sblocco
    def _edit_file(self, should_remove: Callable[[str], bool]) -> list[str]:
        """Toglie da ip_bans.yaml le voci scelte, senza toccare le altre."""
        if not os.path.isfile(self.path):
            return []
        data = _read_bans_file(self.path)
        removed = [str(ip) for ip in data if should_remove(str(ip))]
        if removed:
            kept = {
                str(ip): (
                    {ATTR_BANNED_AT: _to_iso(v.get(ATTR_BANNED_AT))}
                    if isinstance(v, dict) and v.get(ATTR_BANNED_AT)
                    else {}
                )
                for ip, v in data.items()
                if str(ip) not in removed
            }
            with open(self.path, "w", encoding="utf-8") as out:
                if kept:
                    out.write(yaml.safe_dump(kept, default_flow_style=False, allow_unicode=True))
        return removed

    def _remove_from_memory(self, should_remove: Callable[[str], bool]) -> list[str]:
        if self._ban_manager is None:
            return []
        lookup = self._ban_manager.ip_bans_lookup
        to_remove = [ip for ip in lookup if should_remove(str(ip))]
        for ip in to_remove:
            lookup.pop(ip, None)
            self._reset_failed_attempts(ip)
        return [str(ip) for ip in to_remove]

    async def _async_remove(self, should_remove: Callable[[str], bool]) -> list[str]:
        from_file = await self.hass.async_add_executor_job(self._edit_file, should_remove)
        from_mem = self._remove_from_memory(should_remove)
        removed = sorted(set(from_file) | set(from_mem), key=ip_sort_key)
        for ip in removed:
            self.data["temp_bans"].pop(ip, None)
        if removed:
            self._save()
            await self.async_refresh_bans()
        return removed

    async def async_unban(
        self, ip: str, source: str = "manual", action: str = "unban", note: str = ""
    ) -> list[str]:
        """Sblocca un IP o tutti gli IP di una rete CIDR."""
        net = ip_network(ip, strict=False)

        def match(addr: str) -> bool:
            try:
                a = ip_address(addr)
            except ValueError:
                return False
            return a.version == net.version and a in net

        removed = await self._async_remove(match)
        for addr in removed:
            self.log(action, addr, source, note)
        return removed

    async def async_purge_whitelisted(self) -> list[str]:
        removed = await self._async_remove(self.is_whitelisted)
        for addr in removed:
            self.log("unban", addr, "whitelist", "IP in whitelist")
        return removed

    # ------------------------------------------------------ attività periodica
    async def _async_tick(self, _now: datetime | None = None) -> None:
        now = dt_util.utcnow()
        expired = [
            ip for ip, exp in list(self.data["temp_bans"].items()) if (parse_dt(exp) or now) <= now
        ]
        for ip in expired:
            await self.async_unban(ip, source="scadenza", action="expired")
        if self._prune_failed():
            self._signal()
        await self.async_refresh_bans()

    # ------------------------------------------------------- login falliti
    def _prune_failed(self) -> bool:
        limit = dt_util.utcnow() - timedelta(days=7)
        before = len(self.data["failed"])
        self.data["failed"] = [
            f for f in self.data["failed"] if (parse_dt(f.get("time")) or limit) > limit
        ][-FAILED_MAX:]
        changed = len(self.data["failed"]) != before
        if changed:
            self._save()
        return changed

    def attempts_week(self, ip: str) -> int:
        """Tentativi falliti dello stesso IP negli ultimi 7 giorni."""
        limit = dt_util.utcnow() - timedelta(days=7)
        return sum(
            1
            for f in self.data["failed"]
            if f.get("ip") == ip and (parse_dt(f.get("time")) or limit) > limit
        )

    @property
    def failed_24h(self) -> list[dict[str, Any]]:
        limit = dt_util.utcnow() - timedelta(hours=24)
        return [f for f in self.data["failed"] if (parse_dt(f.get("time")) or limit) > limit]

    @callback
    def _listen_login_notifications(self) -> Callable[[], None]:
        """Ascolta la notifica 'Login attempt failed' creata da Home Assistant."""
        try:
            from homeassistant.components.persistent_notification import (  # noqa: PLC0415
                async_register_callback,
            )

            return async_register_callback(self.hass, self._on_notifications)
        except ImportError:
            return async_dispatcher_connect(
                self.hass, "persistent_notifications_updated", self._on_notifications
            )

    @callback
    def _on_notifications(self, update_type: Any, notifications: dict[str, Any]) -> None:
        kind = str(getattr(update_type, "value", update_type))
        if kind not in ("added", "updated"):
            return
        for notification_id, notification in notifications.items():
            if notification_id != NOTIFICATION_ID_LOGIN:
                continue
            match = _LOGIN_MSG_RE.search(str(notification.get("message", "")))
            if not match:
                continue
            host, ip = match.group(1), match.group(2)
            try:
                ip = str(ip_address(ip))
            except ValueError:
                continue
            self.hass.async_create_task(self._async_failed_login(ip, host))

    async def _async_failed_login(self, ip: str, host: str) -> None:
        now = dt_util.utcnow()
        req = self._requests.pop(ip, {})
        url, user_agent = req.get("url"), req.get("ua")
        device = describe_user_agent(user_agent)
        self.data["failed"].append(
            {"time": now.isoformat(), "ip": ip, "host": host, "url": url, "device": device}
        )
        self._prune_failed()
        self._save()
        self._signal()

        whitelisted = self.is_whitelisted(ip)
        attempts = sum(1 for f in self.failed_24h if f.get("ip") == ip)
        attempts_week = self.attempts_week(ip)
        geo = await self.async_geo(ip)
        self.hass.bus.async_fire(
            EVENT_LOGIN_FAILED,
            {
                "ip": ip,
                "host": host,
                "whitelisted": whitelisted,
                "attempts_24h": attempts,
                "attempts_week": attempts_week,
                "device": device,
                "user_agent": user_agent,
                "url": url,
                "country": geo.get("country"),
                "country_code": geo.get("country_code"),
                "region": geo.get("region"),
                "city": geo.get("city"),
                "isp": geo.get("isp"),
                "mobile": geo.get("mobile"),
                "hosting": geo.get("hosting"),
            },
        )
        if not self.telegram_enabled or whitelisted:
            return
        last = self._last_telegram.get(ip)
        if last and now - last < timedelta(seconds=60):
            return  # non intasare la chat con tentativi a raffica
        self._last_telegram[ip] = now
        await self._async_telegram_alert(ip, geo, attempts_week, device=device, url=url, when=now)

    # --------------------------------------------------------------- Telegram
    async def _tg(self, service: str, data: dict[str, Any]) -> bool:
        if not self.hass.services.has_service("telegram_bot", service):
            if not self._warned_no_telegram:
                _LOGGER.warning("telegram_bot.%s non disponibile: configura Telegram Bot", service)
                self._warned_no_telegram = True
            return False
        try:
            await self.hass.services.async_call("telegram_bot", service, data, blocking=True)
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("Errore Telegram (%s): %s", service, err)
            return False
        return True

    async def _async_telegram_alert(
        self,
        ip: str,
        geo: dict,
        attempts_week: int,
        *,
        device: str | None = None,
        url: str | None = None,
        when: datetime | None = None,
    ) -> None:
        esc = html.escape
        lines = [
            "⚠️ <b>LOGIN FALLITO HOME ASSISTANT</b>",
            f"🕐 {fmt_local(when or dt_util.utcnow())}",
            f"🌐 IP: <code>{esc(ip)}</code>",
        ]
        if device:
            lines.append(f"🌍 {esc(device)}")
        if geo.get("country"):
            place = geo["country"]
            if geo.get("country_code"):
                place += f" ({geo['country_code']})"
            local = ", ".join(x for x in (geo.get("city"), geo.get("region")) if x)
            if local:
                place += f" - {local}"
            lines.append(f"📍 {esc(place)}")
        if geo.get("isp"):
            lines.append(f"🏢 {esc(geo['isp'])}")
        if geo.get("hosting") or geo.get("proxy"):
            lines.append("🖥 Datacenter / VPN / proxy")
        elif geo.get("mobile"):
            lines.append("📶 Rete mobile")
        elif geo.get("mobile") is False:
            lines.append("🏠 Rete fissa")
        if url:
            lines.append(f"🔗 {esc(url)}")
        lines.append(f"🔢 Tentativi questa settimana: {attempts_week}")
        data: dict[str, Any] = {
            "message": "\n".join(lines),
            "parse_mode": "html",
            "inline_keyboard": [
                f"🔒 Banna:/gkban {ip}, ⏱ Banna 24 ore:/gkban24 {ip}",
                f"✅ Whitelist:/gkwl {ip}, 🙈 Ignora:/gkignore {ip}",
            ],
        }
        chat_id: int | None = None
        if self.chat_id:
            try:
                chat_id = int(self.chat_id)
            except ValueError:
                _LOGGER.warning("Chat ID Telegram non valido: %s", self.chat_id)
        if chat_id is None:
            await self._tg("send_message", data)
            return
        # "chat_id" è il parametro attuale; "target" è deprecato (rimosso in HA 2026.9)
        # ma resta come riserva per le versioni di Home Assistant che non hanno chat_id.
        if not self.hass.services.has_service("telegram_bot", "send_message"):
            await self._tg("send_message", data)  # registra l'avviso una volta
            return
        try:
            await self.hass.services.async_call(
                "telegram_bot", "send_message", {**data, "chat_id": [chat_id]}, blocking=True
            )
        except vol.Invalid:
            # versione di HA senza "chat_id": uso il vecchio "target"
            await self._tg("send_message", {**data, "target": [chat_id]})
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("Errore Telegram (send_message): %s", err)

    async def _on_telegram_callback(self, event: Event) -> None:
        command = str(event.data.get("data", ""))
        if not command.startswith("/gk"):
            return
        cmd, _, ip = command.partition(" ")
        try:
            ip = str(ip_address(ip.strip()))
        except ValueError:
            return

        if cmd in ("/gkban", "/gkban24"):
            duration = timedelta(hours=24) if cmd == "/gkban24" else None
            res = await self.async_ban([(ip, None)], duration, source="telegram")
            if res["banned"]:
                text = f"🔒 {ip} bannato" + (" per 24 ore" if duration else "")
            elif res["whitelisted"]:
                text = f"⚠️ {ip} è in whitelist: non bannato"
            else:
                text = f"ℹ️ {ip} era già bannato"
        elif cmd == "/gkwl":
            text = f"✅ {ip} aggiunto alla whitelist"
        elif cmd == "/gkignore":
            text = "🙈 Ignorato"
        else:
            return

        if event.data.get("id"):
            await self._tg(
                "answer_callback_query",
                {"callback_query_id": event.data["id"], "message": text},
            )
        message = event.data.get("message") or {}
        chat_id = event.data.get("chat_id") or (message.get("chat") or {}).get("id")
        if message.get("message_id") and chat_id:
            await self._tg(
                "edit_message",
                {
                    "message_id": message["message_id"],
                    "chat_id": chat_id,
                    "message": f"{message.get('text', '')}\n\n{text}",
                },
            )
        if cmd == "/gkwl":
            # ultimo: provoca il ricaricamento dell'integrazione
            await self.async_whitelist_add([ip], unban=True, source="telegram")

    # ----------------------------------------------------- geolocalizzazione
    async def async_geo(self, ip: str) -> dict[str, Any]:
        if not self.geo_enabled:
            return {}
        cache = self.data["geo"]
        cached = cache.get(ip)
        if (
            cached
            and "region" in cached
            and (parse_dt(cached.get("time")) or dt_util.utcnow())
            > dt_util.utcnow() - timedelta(days=30)
        ):
            return cached
        try:
            addr = ip_address(ip)
        except ValueError:
            return {}
        if not addr.is_global:
            info = {
                "country": "Rete locale",
                "country_code": None,
                "region": None,
                "city": None,
                "isp": None,
            }
        else:
            async with self._geo_lock:
                try:
                    session = async_get_clientsession(self.hass)
                    async with asyncio.timeout(8):
                        resp = await session.get(GEO_URL.format(ip=ip))
                        js = await resp.json(content_type=None)
                except Exception as err:  # noqa: BLE001
                    _LOGGER.debug("Geolocalizzazione %s non riuscita: %s", ip, err)
                    return cached or {}
                finally:
                    await asyncio.sleep(1.5)  # limite del servizio: 45 richieste/minuto
            if not isinstance(js, dict) or js.get("status") != "success":
                return cached or {}
            info = {
                "country": js.get("country"),
                "country_code": js.get("countryCode"),
                "region": js.get("regionName"),
                "city": js.get("city"),
                "isp": js.get("isp") or js.get("org"),
                "mobile": js.get("mobile"),
                "proxy": js.get("proxy"),
                "hosting": js.get("hosting"),
            }
        info["time"] = dt_util.utcnow().isoformat()
        cache[ip] = info
        while len(cache) > GEO_CACHE_MAX:
            cache.pop(next(iter(cache)))
        self._save()
        return info

    @callback
    def _start_geo_fill(self) -> None:
        if self._geo_task and not self._geo_task.done():
            return

        async def fill() -> None:
            for ban in list(self.bans):
                if ban["ip"] not in self.data["geo"]:
                    await self.async_geo(ban["ip"])
            await self.async_refresh_bans()

        self._geo_task = self.hass.async_create_background_task(fill(), f"{STORAGE_KEY}_geo")

    # ------------------------------------------------- esporta / importa
    def safe_path(self, filename: str | None) -> str:
        name = os.path.basename((filename or "").strip()) or DEFAULT_EXPORT
        if not name.endswith((".yaml", ".yml")):
            name += ".yaml"
        return self.hass.config.path(name)

    async def async_export(
        self, filename: str | None = None, source: str = "manual"
    ) -> dict[str, Any]:
        path = self.safe_path(filename)
        bans = await self.async_refresh_bans()
        content = {
            "gatekeeper_ip": 1,
            "esportato_il": fmt_local(dt_util.utcnow()),
            "whitelist": self.whitelist,
            "bans": [
                {"ip": b["ip"], "banned_at": b["banned_at_iso"]}
                | ({"expires": b["expires_iso"]} if b["expires_iso"] else {})
                for b in bans
            ],
            "history": self.data["history"],
        }

        def write() -> None:
            with open(path, "w", encoding="utf-8") as file:
                yaml.safe_dump(content, file, allow_unicode=True, sort_keys=False)

        await self.hass.async_add_executor_job(write)
        self.log("export", None, source, os.path.basename(path))
        return {"file": path, "bans": len(bans), "whitelist": len(self.whitelist)}

    async def async_import(
        self, filename: str | None = None, source: str = "manual"
    ) -> dict[str, Any]:
        path = self.safe_path(filename)
        try:
            content = await self.hass.async_add_executor_job(_read_yaml, path)
        except yaml.YAMLError as err:
            raise ValueError(f"file non valido: {err}") from err
        if content is None:
            raise FileNotFoundError(path)
        if not isinstance(content, dict):
            raise ValueError("file non valido")

        now = dt_util.utcnow()
        entries: list[tuple[str, datetime | None]] = []
        expiries: dict[str, datetime] = {}
        for item in content.get("bans") or []:
            raw_ip, when, expires = item, None, None
            if isinstance(item, dict):
                raw_ip = item.get("ip")
                when = parse_dt(item.get("banned_at"))
                expires = parse_dt(item.get("expires"))
            try:
                ip = str(ip_address(str(raw_ip).strip()))
            except ValueError:
                continue
            if expires and expires <= now:
                continue  # ban temporaneo già scaduto
            entries.append((ip, when))
            if expires:
                expiries[ip] = expires

        res = await self.async_ban(entries, None, source="import")
        for ip in res["banned"]:
            if ip in expiries:
                self.data["temp_bans"][ip] = expiries[ip].isoformat()

        # storico: aggiunge le voci mancanti
        known = {(h.get("time"), h.get("action"), h.get("ip")) for h in self.data["history"]}
        for h in content.get("history") or []:
            if isinstance(h, dict) and (h.get("time"), h.get("action"), h.get("ip")) not in known:
                self.data["history"].append(h)
        self.data["history"].sort(key=lambda h: str(h.get("time", "")))
        del self.data["history"][:-HISTORY_MAX]

        try:
            nets = parse_whitelist(content.get("whitelist") or [])
        except ValueError:
            nets = []
        new_nets = [n for n in nets if n not in self.whitelist]
        self.log(
            "import",
            None,
            source,
            f"{os.path.basename(path)}: {len(res['banned'])} ban, {len(new_nets)} reti whitelist",
        )
        await self.async_refresh_bans()
        if new_nets:
            await self.async_whitelist_add(new_nets, unban=False, source="import")
        return {
            "file": path,
            "bans_imported": res["banned"],
            "already_banned": res["already_banned"],
            "skipped_whitelisted": res["whitelisted"],
            "whitelist_added": new_nets,
        }
