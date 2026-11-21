"""Config flow e menu Configura di Gatekeeper IP."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    BooleanSelector,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
)

from .const import (
    CONF_CHAT_ID,
    CONF_DURATION,
    CONF_FILENAME,
    CONF_GEO,
    CONF_IPS,
    CONF_TELEGRAM,
    CONF_WHITELIST,
    DEFAULT_EXPORT,
    DOMAIN,
    DURATION_CHOICES,
)
from .manager import parse_ip_list, parse_whitelist

_LOGGER = logging.getLogger(__name__)

DEFAULT_WHITELIST = "192.168.1.0/24"


def _whitelist_schema(default: str) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_WHITELIST, default=default): TextSelector(
                TextSelectorConfig(multiline=True)
            )
        }
    )


def _validate(user_input: dict[str, Any]) -> tuple[list[str] | None, dict[str, str]]:
    try:
        return parse_whitelist(user_input[CONF_WHITELIST]), {}
    except ValueError:
        return None, {CONF_WHITELIST: "invalid_ip"}


def _err_text(err: Exception) -> str:
    return f"{type(err).__name__}: {err}"


class GatekeeperConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            networks, errors = _validate(user_input)
            if not errors:
                return self.async_create_entry(
                    title="Gatekeeper IP",
                    data={},
                    options={
                        CONF_WHITELIST: networks,
                        CONF_TELEGRAM: False,
                        CONF_CHAT_ID: "",
                        CONF_GEO: True,
                    },
                )
        default = user_input[CONF_WHITELIST] if user_input else DEFAULT_WHITELIST
        return self.async_show_form(
            step_id="user", data_schema=_whitelist_schema(default), errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return GatekeeperOptionsFlow()


class GatekeeperOptionsFlow(OptionsFlow):
    """Menu: whitelist, banna, sblocca, impostazioni, esporta, importa."""

    def _manager(self):
        return getattr(self.config_entry, "runtime_data", None)

    def _done(self) -> ConfigFlowResult:
        # opzioni invariate → nessun ricaricamento
        return self.async_create_entry(data=dict(self.config_entry.options))

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return self.async_show_menu(
            step_id="init",
            menu_options=["ban", "unban", "whitelist", "settings", "export", "import_file"],
        )

    # ------------------------------------------------------------- whitelist
    async def async_step_whitelist(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            networks, errors = _validate(user_input)
            if not errors:
                return self.async_create_entry(
                    data={**self.config_entry.options, CONF_WHITELIST: networks}
                )
            default = user_input[CONF_WHITELIST]
        else:
            default = "\n".join(self.config_entry.options.get(CONF_WHITELIST, []))
        return self.async_show_form(
            step_id="whitelist", data_schema=_whitelist_schema(default), errors=errors
        )

    # ------------------------------------------------------------------- ban
    async def async_step_ban(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        manager = self._manager()
        if manager is None:
            return self.async_abort(reason="not_loaded")
        errors: dict[str, str] = {}
        placeholders = {"ips": "", "error": ""}
        default_ips, default_duration = "", "0"
        if user_input is not None:
            default_ips = user_input[CONF_IPS]
            default_duration = user_input.get(CONF_DURATION, "0")
            try:
                entries = parse_ip_list(default_ips)
            except ValueError as err:
                errors[CONF_IPS] = "invalid_single_ip"
                placeholders["ips"] = str(err)
            else:
                whitelisted = [ip for ip, _ in entries if manager.is_whitelisted(ip)]
                if not entries:
                    errors[CONF_IPS] = "empty"
                elif whitelisted:
                    errors[CONF_IPS] = "whitelisted"
                    placeholders["ips"] = ", ".join(whitelisted)
                else:
                    minutes = int(default_duration or 0)
                    try:
                        await manager.async_ban(
                            entries, timedelta(minutes=minutes) if minutes else None, "manual"
                        )
                    except Exception as err:  # noqa: BLE001
                        _LOGGER.exception("Errore durante il ban manuale")
                        errors["base"] = "error"
                        placeholders["error"] = _err_text(err)
                    else:
                        return self._done()
        schema = vol.Schema(
            {
                vol.Required(CONF_IPS, default=default_ips): TextSelector(
                    TextSelectorConfig(multiline=True)
                ),
                vol.Required(CONF_DURATION, default=default_duration): SelectSelector(
                    SelectSelectorConfig(
                        options=[{"value": k, "label": v} for k, v in DURATION_CHOICES.items()],
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
            }
        )
        return self.async_show_form(
            step_id="ban", data_schema=schema, errors=errors, description_placeholders=placeholders
        )

    # --------------------------------------------------------------- sblocco
    async def async_step_unban(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        manager = self._manager()
        if manager is None:
            return self.async_abort(reason="not_loaded")
        try:
            if user_input is not None:
                for ip in user_input.get(CONF_IPS, []):
                    await manager.async_unban(ip, source="manual")
                return self._done()
            bans = await manager.async_refresh_bans()
        except Exception as err:  # noqa: BLE001
            _LOGGER.exception("Errore nello sblocco IP")
            return self.async_abort(
                reason="error", description_placeholders={"error": _err_text(err)}
            )
        if not bans:
            return self.async_abort(reason="no_bans")
        options = []
        for b in bans:
            parts = [f"{b['flag']} {b['ip']}".strip(), b["banned_at"] or "data sconosciuta"]
            if b["expires"]:
                parts.append(f"⏱ fino al {b['expires']}")
            if b["country"]:
                parts.append(b["country"] + (f" · {b['isp']}" if b["isp"] else ""))
            options.append({"value": b["ip"], "label": "  —  ".join(parts)})
        schema = vol.Schema(
            {
                vol.Required(CONF_IPS, default=[]): SelectSelector(
                    SelectSelectorConfig(
                        options=options, multiple=True, mode=SelectSelectorMode.LIST
                    )
                )
            }
        )
        return self.async_show_form(step_id="unban", data_schema=schema)

    # ----------------------------------------------------------- impostazioni
    async def async_step_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        opts = self.config_entry.options
        if user_input is not None:
            return self.async_create_entry(
                data={
                    **opts,
                    CONF_TELEGRAM: user_input[CONF_TELEGRAM],
                    CONF_CHAT_ID: (user_input.get(CONF_CHAT_ID) or "").strip(),
                    CONF_GEO: user_input[CONF_GEO],
                }
            )
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_TELEGRAM, default=opts.get(CONF_TELEGRAM, False)
                ): BooleanSelector(),
                vol.Optional(
                    CONF_CHAT_ID, description={"suggested_value": opts.get(CONF_CHAT_ID, "")}
                ): TextSelector(),
                vol.Required(CONF_GEO, default=opts.get(CONF_GEO, True)): BooleanSelector(),
            }
        )
        return self.async_show_form(step_id="settings", data_schema=schema)

    # ------------------------------------------------------- esporta / importa
    async def async_step_export(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        manager = self._manager()
        if manager is None:
            return self.async_abort(reason="not_loaded")
        if user_input is not None:
            try:
                res = await manager.async_export(user_input.get(CONF_FILENAME), source="manual")
            except Exception as err:  # noqa: BLE001
                _LOGGER.exception("Errore esportazione")
                return self.async_abort(
                    reason="error", description_placeholders={"error": _err_text(err)}
                )
            return self.async_abort(
                reason="exported",
                description_placeholders={
                    "file": res["file"],
                    "bans": str(res["bans"]),
                    "whitelist": str(res["whitelist"]),
                },
            )
        schema = vol.Schema({vol.Required(CONF_FILENAME, default=DEFAULT_EXPORT): TextSelector()})
        return self.async_show_form(step_id="export", data_schema=schema)

    async def async_step_import_file(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        manager = self._manager()
        if manager is None:
            return self.async_abort(reason="not_loaded")
        errors: dict[str, str] = {}
        placeholders = {"error": ""}
        if user_input is not None:
            try:
                res = await manager.async_import(user_input.get(CONF_FILENAME), source="manual")
            except FileNotFoundError:
                errors[CONF_FILENAME] = "file_not_found"
            except Exception as err:  # noqa: BLE001
                _LOGGER.exception("Errore importazione")
                errors["base"] = "error"
                placeholders["error"] = _err_text(err)
            else:
                return self.async_abort(
                    reason="imported",
                    description_placeholders={
                        "bans": str(len(res["bans_imported"])),
                        "already": str(len(res["already_banned"])),
                        "whitelist": str(len(res["whitelist_added"])),
                    },
                )
        schema = vol.Schema({vol.Required(CONF_FILENAME, default=DEFAULT_EXPORT): TextSelector()})
        return self.async_show_form(
            step_id="import_file",
            data_schema=schema,
            errors=errors,
            description_placeholders=placeholders,
        )
