"""Sensori: IP bannati, login falliti (24 ore), ultimo evento con storico."""

from __future__ import annotations

from collections import Counter
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import GatekeeperConfigEntry
from .const import ACTION_LABELS, DOMAIN, SIGNAL_UPDATED, SOURCE_LABELS
from .manager import GatekeeperManager, fmt_local

HISTORY_IN_ATTRIBUTES = 40


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GatekeeperConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    manager = entry.runtime_data
    async_add_entities(
        [
            BannedIpsSensor(entry, manager),
            FailedLoginsSensor(entry, manager),
            LastEventSensor(entry, manager),
        ]
    )


def describe(event: dict[str, Any]) -> str:
    action = ACTION_LABELS.get(event.get("action"), event.get("action") or "")
    text = f"{action} {event.get('ip') or ''}".strip()
    source = SOURCE_LABELS.get(event.get("source"), event.get("source"))
    if source:
        text += f" ({source})"
    return text[:255]


class _Base(SensorEntity):
    _attr_has_entity_name = True
    _attr_should_poll = False
    _key = ""

    def __init__(self, entry: GatekeeperConfigEntry, manager: GatekeeperManager) -> None:
        self._manager = manager
        self._attr_unique_id = f"{entry.entry_id}_{self._key}"
        self._attr_translation_key = self._key
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Gatekeeper IP",
            "manufacturer": "ichnusa82",
            "entry_type": "service",
        }

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(async_dispatcher_connect(self.hass, SIGNAL_UPDATED, self._refresh))

    @callback
    def _refresh(self) -> None:
        self.async_write_ha_state()


class BannedIpsSensor(_Base):
    _key = "banned_ips"
    _attr_icon = "mdi:shield-lock"
    _attr_native_unit_of_measurement = "IP"
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> int:
        return len(self._manager.bans)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        bans = self._manager.bans
        return {
            "integration": DOMAIN,
            "bans": bans,
            "ip_bannati": {
                b["ip"]: " · ".join(
                    x
                    for x in (
                        b["banned_at"],
                        f"fino al {b['expires']}" if b["expires"] else None,
                        f"{b['flag']} {b['country']}".strip() if b["country"] else None,
                        b["isp"],
                    )
                    if x
                )
                for b in bans
            },
            "temporanei": sum(1 for b in bans if b["expires"]),
            "whitelist": self._manager.whitelist,
            "ip_ban_attivo": self._manager.ban_enabled,
            "telegram": self._manager.telegram_enabled,
        }


class FailedLoginsSensor(_Base):
    _key = "failed_logins"
    _attr_icon = "mdi:account-alert"
    _attr_native_unit_of_measurement = "tentativi"
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> int:
        return len(self._manager.failed_24h)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        failed = self._manager.failed_24h
        last = failed[-1] if failed else {}
        return {
            "integration": DOMAIN,
            "per_ip": dict(Counter(f.get("ip") for f in failed).most_common(20)),
            "ultimo_ip": last.get("ip"),
            "ultimo_host": last.get("host"),
            "ultimo_tentativo": fmt_local(last.get("time")),
        }


class LastEventSensor(_Base):
    _key = "last_event"
    _attr_icon = "mdi:history"

    @property
    def native_value(self) -> str | None:
        history = self._manager.data["history"]
        return describe(history[-1]) if history else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        items = self._manager.data["history"][-HISTORY_IN_ATTRIBUTES:]
        return {
            "integration": DOMAIN,
            "storico": [
                {
                    "quando": fmt_local(h.get("time")),
                    "azione": ACTION_LABELS.get(h.get("action"), h.get("action")),
                    "ip": h.get("ip"),
                    "origine": SOURCE_LABELS.get(h.get("source"), h.get("source")),
                    "nota": h.get("note") or "",
                }
                for h in reversed(items)
            ],
        }
