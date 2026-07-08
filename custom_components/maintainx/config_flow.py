"""Config flow for MaintainX integration."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_API_KEY, DOMAIN
from .coordinator import MaintainXApiClient

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_KEY): str,
    }
)


class MaintainXConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for MaintainX."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            api_key = user_input[CONF_API_KEY]

            # Validate the API key
            session = async_get_clientsession(self.hass)
            client = MaintainXApiClient(api_key, session)

            try:
                valid = await client.async_validate_api_key()
                if valid:
                    # Prevent duplicate entries
                    await self.async_set_unique_id(api_key[:16])
                    self._abort_if_unique_id_configured()

                    return self.async_create_entry(
                        title="MaintainX",
                        data=user_input,
                    )
                else:
                    errors["base"] = "invalid_auth"
            except aiohttp.ClientError:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_reauth(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle reauth."""
        return await self.async_step_user(user_input)
