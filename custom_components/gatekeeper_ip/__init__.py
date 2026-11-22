"""Gatekeeper IP: whitelist, ban manuali e temporanei, avvisi Telegram."""

from __future__ import annotations

import logging
import os

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import (
    ATTR_DURATION,
    ATTR_FILENAME,
    ATTR_IP,
    ATTR_LIMIT,
    ATTR_UNBAN,
    CARD_URL,
    DOMAIN,
    SERVICE_ADD,
    SERVICE_BAN,
    SERVICE_EXPORT,
    SERVICE_HISTORY,
    SERVICE_IMPORT,
    SERVICE_PURGE,
    SERVICE_REMOVE,
    SERVICE_UNBAN,
    VERSION,
)
from .manager import GatekeeperManager, history_items, parse_ip_list, parse_whitelist
from .texts import lang_of

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

type GatekeeperConfigEntry = ConfigEntry[GatekeeperManager]

IP_SCHEMA = vol.Schema({vol.Required(ATTR_IP): cv.string})
BAN_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_IP): cv.string,
        vol.Optional(ATTR_DURATION): cv.time_period,
    }
)
ADD_SCHEMA = vol.Schema(
    {vol.Required(ATTR_IP): cv.string, vol.Optional(ATTR_UNBAN, default=True): cv.boolean}
)
FILE_SCHEMA = vol.Schema({vol.Optional(ATTR_FILENAME): cv.string})
HISTORY_SCHEMA = vol.Schema(
    {vol.Optional(ATTR_LIMIT, default=50): vol.All(vol.Coerce(int), vol.Range(min=1, max=300))}
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Registra la card della dashboard (una volta sola)."""
    path = os.path.join(os.path.dirname(__file__), "www", "gatekeeper-ip-card.js")
    try:
        from homeassistant.components.http import StaticPathConfig  # noqa: PLC0415

        await hass.http.async_register_static_paths([StaticPathConfig(CARD_URL, path, False)])
    except ImportError:  # versioni vecchie di HA
        hass.http.register_static_path(CARD_URL, path, False)
    try:
        from homeassistant.components.frontend import add_extra_js_url  # noqa: PLC0415

        add_extra_js_url(hass, f"{CARD_URL}?v={VERSION}")
    except Exception as err:  # noqa: BLE001
        _LOGGER.warning("Dashboard card could not be registered automatically: %s", err)
    _async_register_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: GatekeeperConfigEntry) -> bool:
    manager = GatekeeperManager(hass, entry)
    await manager.async_setup()
    entry.runtime_data = manager
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: GatekeeperConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        await entry.runtime_data.async_unload()
    return unloaded


def _error(key: str, **placeholders: str) -> ServiceValidationError:
    """Errore tradotto (strings.json → exceptions)."""
    return ServiceValidationError(
        translation_domain=DOMAIN,
        translation_key=key,
        translation_placeholders={k: str(v) for k, v in placeholders.items()},
    )


def _manager(hass: HomeAssistant) -> GatekeeperManager:
    entries = hass.config_entries.async_loaded_entries(DOMAIN)
    if not entries:
        raise _error("not_loaded")
    return entries[0].runtime_data


def _nets(text: str) -> list[str]:
    try:
        return parse_whitelist(text)
    except ValueError as err:
        raise _error("invalid_network", value=text) from err


def _async_register_services(hass: HomeAssistant) -> None:
    async def ban(call: ServiceCall) -> dict:
        try:
            entries = parse_ip_list(call.data[ATTR_IP])
        except ValueError as err:
            raise _error("invalid_entry", entry=str(err)) from err
        if not entries:
            raise _error("no_ip")
        return await _manager(hass).async_ban(
            entries, call.data.get(ATTR_DURATION), source="service"
        )

    async def unban(call: ServiceCall) -> dict:
        manager = _manager(hass)
        removed: list[str] = []
        for net in _nets(call.data[ATTR_IP]):
            removed += await manager.async_unban(net, source="service")
        return {"removed": removed}

    async def purge(call: ServiceCall) -> dict:
        return {"removed": await _manager(hass).async_purge_whitelisted()}

    async def add(call: ServiceCall) -> dict:
        added = await _manager(hass).async_whitelist_add(
            _nets(call.data[ATTR_IP]), unban=call.data[ATTR_UNBAN], source="service"
        )
        return {"added": added}

    async def remove(call: ServiceCall) -> dict:
        removed = await _manager(hass).async_whitelist_remove(
            _nets(call.data[ATTR_IP]), source="service"
        )
        return {"removed": removed}

    async def export(call: ServiceCall) -> dict:
        return await _manager(hass).async_export(call.data.get(ATTR_FILENAME), source="service")

    async def import_(call: ServiceCall) -> dict:
        try:
            return await _manager(hass).async_import(call.data.get(ATTR_FILENAME), source="service")
        except FileNotFoundError as err:
            raise _error("file_not_found", file=str(err)) from err
        except ValueError as err:
            raise _error("invalid_file", error=str(err)) from err

    async def history(call: ServiceCall) -> dict:
        items = _manager(hass).data["history"][-call.data[ATTR_LIMIT] :]
        return {"history": history_items(items, lang_of(hass))}

    opt = SupportsResponse.OPTIONAL
    hass.services.async_register(DOMAIN, SERVICE_BAN, ban, BAN_SCHEMA, opt)
    hass.services.async_register(DOMAIN, SERVICE_UNBAN, unban, IP_SCHEMA, opt)
    hass.services.async_register(DOMAIN, SERVICE_PURGE, purge, None, opt)
    hass.services.async_register(DOMAIN, SERVICE_ADD, add, ADD_SCHEMA, opt)
    hass.services.async_register(DOMAIN, SERVICE_REMOVE, remove, IP_SCHEMA, opt)
    hass.services.async_register(DOMAIN, SERVICE_EXPORT, export, FILE_SCHEMA, opt)
    hass.services.async_register(DOMAIN, SERVICE_IMPORT, import_, FILE_SCHEMA, opt)
    hass.services.async_register(
        DOMAIN, SERVICE_HISTORY, history, HISTORY_SCHEMA, SupportsResponse.ONLY
    )
