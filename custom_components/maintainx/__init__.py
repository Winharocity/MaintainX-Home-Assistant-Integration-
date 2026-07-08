"""The MaintainX integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_API_KEY, DASHBOARD_ICON, DASHBOARD_TITLE, DASHBOARD_URL, DOMAIN
from .coordinator import MaintainXApiClient, MaintainXCoordinator
from .dashboard import async_create_dashboard_config, async_setup_input_helpers, async_setup_dashboard_automations
from .services import async_setup_services, async_unload_services

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up MaintainX from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    api_key = entry.data[CONF_API_KEY]
    session = async_get_clientsession(hass)
    client = MaintainXApiClient(api_key, session)

    coordinator = MaintainXCoordinator(hass, client)
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register services
    await async_setup_services(hass)

    # Create input helpers (buttons, text fields, selects for the dashboard)
    await async_setup_input_helpers(hass)

    # Create automations for dashboard buttons
    await async_setup_dashboard_automations(hass)

    # Register the dashboard panel in the sidebar
    await async_create_dashboard_config(hass)

    try:
        hass.components.frontend.async_register_built_in_panel(
            component_name="lovelace",
            sidebar_title=DASHBOARD_TITLE,
            sidebar_icon=DASHBOARD_ICON,
            frontend_url_path=DASHBOARD_URL,
            config={"mode": "storage"},
            require_admin=False,
        )
        _LOGGER.info("MaintainX dashboard registered in sidebar")
    except Exception as err:
        _LOGGER.warning("Could not register MaintainX dashboard panel: %s", err)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    if not hass.data[DOMAIN]:
        async_unload_services(hass)

        # Remove sidebar panel
        try:
            hass.components.frontend.async_remove_panel(DASHBOARD_URL)
            _LOGGER.info("MaintainX dashboard removed from sidebar")
        except Exception:
            pass

        hass.data.pop(DOMAIN)

    return unload_ok
