"""The MaintainX integration."""
from __future__ import annotations

import logging
import os

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_API_KEY, DASHBOARD_ICON, DASHBOARD_TITLE, DASHBOARD_URL, DOMAIN
from .coordinator import MaintainXApiClient, MaintainXCoordinator
from .dashboard import async_setup_input_helpers, async_setup_dashboard_automations, generate_dashboard_yaml
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

    # Create input helpers
    await async_setup_input_helpers(hass)

    # Create automations for dashboard buttons
    await async_setup_dashboard_automations(hass)

    # Write the YAML dashboard file
    yaml_path = hass.config.path("maintainx_dashboard.yaml")
    if not os.path.exists(yaml_path):
        await hass.async_add_executor_job(_write_dashboard_yaml, yaml_path)
        _LOGGER.info("MaintainX dashboard YAML written to %s", yaml_path)

    # Register the panel in the sidebar
    try:
        hass.components.frontend.async_register_built_in_panel(
            component_name="lovelace",
            sidebar_title=DASHBOARD_TITLE,
            sidebar_icon=DASHBOARD_ICON,
            frontend_url_path=DASHBOARD_URL,
            config={
                "mode": "yaml",
                "filename": "maintainx_dashboard.yaml",
            },
            require_admin=False,
        )
        _LOGGER.info("MaintainX dashboard registered in sidebar")
    except Exception as err:
        _LOGGER.warning("Could not register MaintainX dashboard panel: %s", err)

    return True


def _write_dashboard_yaml(yaml_path: str) -> None:
    """Write the dashboard YAML file to disk."""
    content = generate_dashboard_yaml()
    with open(yaml_path, "w", encoding="utf-8") as f:
        f.write(content)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    if not hass.data[DOMAIN]:
        async_unload_services(hass)

        try:
            hass.components.frontend.async_remove_panel(DASHBOARD_URL)
            _LOGGER.info("MaintainX dashboard removed from sidebar")
        except Exception:
            pass

        hass.data.pop(DOMAIN)

    return unload_ok
