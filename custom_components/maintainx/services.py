"""Services for the MaintainX integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall, callback
import homeassistant.helpers.config_validation as cv

from .const import (
    ATTR_ASSET_ID, ATTR_ASSIGNEE_ID, ATTR_CATEGORY, ATTR_COMMENT,
    ATTR_DESCRIPTION, ATTR_LOCATION_ID, ATTR_PRIORITY, ATTR_STATUS,
    ATTR_TITLE, ATTR_WORK_ORDER_ID, DOMAIN,
    PRIORITY_NONE, PRIORITY_LOW, PRIORITY_MEDIUM, PRIORITY_HIGH, PRIORITY_CRITICAL,
    CATEGORY_DAMAGE, CATEGORY_INSPECTION, CATEGORY_METER_READING, CATEGORY_PREVENTIVE,
    CATEGORY_PROJECT, CATEGORY_SAFETY, CATEGORY_UPGRADE, CATEGORY_CORRECTIVE, CATEGORY_DEFAULT,
    SERVICE_ADD_COMMENT, SERVICE_COMPLETE_WORK_ORDER, SERVICE_CREATE_WORK_ORDER,
    SERVICE_UPDATE_WORK_ORDER, SERVICE_SET_STATUS,
)

_LOGGER = logging.getLogger(__name__)

ALL_PRIORITIES = [PRIORITY_NONE, PRIORITY_LOW, PRIORITY_MEDIUM, PRIORITY_HIGH, PRIORITY_CRITICAL]
ALL_CATEGORIES = [CATEGORY_DAMAGE, CATEGORY_INSPECTION, CATEGORY_METER_READING, CATEGORY_PREVENTIVE,
                  CATEGORY_PROJECT, CATEGORY_SAFETY, CATEGORY_UPGRADE, CATEGORY_CORRECTIVE, CATEGORY_DEFAULT]
ALL_STATUSES = ["OPEN", "IN_PROGRESS", "ON_HOLD", "DONE"]
ALL_ASSET_STATUSES = ["ONLINE", "OFFLINE", "IGNORE"]


async def async_setup_services(hass: HomeAssistant) -> None:
    """Set up MaintainX services."""

    async def async_create_work_order(call: ServiceCall) -> None:
        data: dict[str, Any] = {
            "title": call.data[ATTR_TITLE],
            "description": call.data.get(ATTR_DESCRIPTION, ""),
            "priority": call.data.get(ATTR_PRIORITY, PRIORITY_NONE),
            "categories": [call.data.get(ATTR_CATEGORY, CATEGORY_DEFAULT)],
        }
        if ATTR_ASSIGNEE_ID in call.data and call.data[ATTR_ASSIGNEE_ID]:
            try:
                data["assignees"] = [{"type": "USER", "id": int(call.data[ATTR_ASSIGNEE_ID])}]
            except (ValueError, TypeError):
                pass
        if ATTR_ASSET_ID in call.data and call.data[ATTR_ASSET_ID]:
            try:
                data["assetId"] = int(call.data[ATTR_ASSET_ID])
            except (ValueError, TypeError):
                pass
        if ATTR_LOCATION_ID in call.data and call.data[ATTR_LOCATION_ID]:
            try:
                data["locationId"] = int(call.data[ATTR_LOCATION_ID])
            except (ValueError, TypeError):
                pass
        if "due_date" in call.data and call.data["due_date"]:
            data["dueDate"] = call.data["due_date"]

        for entry_id, coordinator in hass.data[DOMAIN].items():
            result = await coordinator.client.async_create_work_order(data)
            _LOGGER.info("Created MaintainX WO: %s", call.data[ATTR_TITLE])
            await coordinator.async_request_refresh()
            break

    async def async_update_work_order(call: ServiceCall) -> None:
        work_order_id = call.data[ATTR_WORK_ORDER_ID]
        data: dict[str, Any] = {}
        if ATTR_TITLE in call.data:
            data["title"] = call.data[ATTR_TITLE]
        if ATTR_DESCRIPTION in call.data:
            data["description"] = call.data[ATTR_DESCRIPTION]
        if ATTR_PRIORITY in call.data:
            data["priority"] = call.data[ATTR_PRIORITY]
        if ATTR_STATUS in call.data:
            data["status"] = call.data[ATTR_STATUS]
        if ATTR_CATEGORY in call.data:
            data["categories"] = [call.data[ATTR_CATEGORY]]
        if ATTR_ASSIGNEE_ID in call.data and call.data[ATTR_ASSIGNEE_ID]:
            try:
                data["assignees"] = [{"type": "USER", "id": int(call.data[ATTR_ASSIGNEE_ID])}]
            except (ValueError, TypeError):
                pass
        if ATTR_ASSET_ID in call.data and call.data[ATTR_ASSET_ID]:
            try:
                data["assetId"] = int(call.data[ATTR_ASSET_ID])
            except (ValueError, TypeError):
                pass
        if ATTR_LOCATION_ID in call.data and call.data[ATTR_LOCATION_ID]:
            try:
                data["locationId"] = int(call.data[ATTR_LOCATION_ID])
            except (ValueError, TypeError):
                pass

        for entry_id, coordinator in hass.data[DOMAIN].items():
            await coordinator.client.async_update_work_order(work_order_id, data)
            _LOGGER.info("Updated MaintainX WO: %s", work_order_id)
            await coordinator.async_request_refresh()
            break

    async def async_complete_work_order(call: ServiceCall) -> None:
        work_order_id = call.data[ATTR_WORK_ORDER_ID]
        for entry_id, coordinator in hass.data[DOMAIN].items():
            await coordinator.client.async_update_work_order(work_order_id, {"status": "DONE"})
            _LOGGER.info("Completed MaintainX WO: %s", work_order_id)
            await coordinator.async_request_refresh()
            break

    async def async_set_status(call: ServiceCall) -> None:
        work_order_id = call.data[ATTR_WORK_ORDER_ID]
        status = call.data[ATTR_STATUS]
        for entry_id, coordinator in hass.data[DOMAIN].items():
            await coordinator.client.async_update_work_order(work_order_id, {"status": status})
            _LOGGER.info("Set MaintainX WO %s to %s", work_order_id, status)
            await coordinator.async_request_refresh()
            break

    async def async_set_asset_status(call: ServiceCall) -> None:
        asset_id = call.data["asset_id"]
        status = call.data["status"]
        for entry_id, coordinator in hass.data[DOMAIN].items():
            await coordinator.client.async_set_asset_status(asset_id, status)
            _LOGGER.info("Set MaintainX Asset %s to %s", asset_id, status)
            # Force the coordinator to bypass the cycle and fetch assets immediately
            coordinator._force_asset_refresh = True
            await coordinator.async_request_refresh()
            break

    async def async_add_comment(call: ServiceCall) -> None:
        work_order_id = call.data[ATTR_WORK_ORDER_ID]
        comment = call.data[ATTR_COMMENT]
        for entry_id, coordinator in hass.data[DOMAIN].items():
            await coordinator.client.async_add_comment(work_order_id, comment)
            _LOGGER.info("Added comment to MaintainX WO: %s", work_order_id)
            break

    hass.services.async_register(DOMAIN, SERVICE_CREATE_WORK_ORDER, async_create_work_order,
        schema=vol.Schema({
            vol.Required(ATTR_TITLE): cv.string,
            vol.Optional(ATTR_DESCRIPTION, default=""): cv.string,
            vol.Optional(ATTR_PRIORITY, default=PRIORITY_NONE): vol.In(ALL_PRIORITIES),
            vol.Optional(ATTR_CATEGORY, default=CATEGORY_DEFAULT): vol.In(ALL_CATEGORIES),
            vol.Optional(ATTR_ASSIGNEE_ID): vol.Any(cv.positive_int, cv.string, None),
            vol.Optional(ATTR_ASSET_ID): vol.Any(cv.positive_int, cv.string, None),
            vol.Optional(ATTR_LOCATION_ID): vol.Any(cv.positive_int, cv.string, None),
            vol.Optional("due_date"): cv.string,
        }))

    hass.services.async_register(DOMAIN, SERVICE_UPDATE_WORK_ORDER, async_update_work_order,
        schema=vol.Schema({
            vol.Required(ATTR_WORK_ORDER_ID): cv.positive_int,
            vol.Optional(ATTR_TITLE): cv.string,
            vol.Optional(ATTR_DESCRIPTION): cv.string,
            vol.Optional(ATTR_PRIORITY): vol.In(ALL_PRIORITIES),
            vol.Optional(ATTR_STATUS): vol.In(ALL_STATUSES),
            vol.Optional(ATTR_CATEGORY): vol.In(ALL_CATEGORIES),
            vol.Optional(ATTR_ASSIGNEE_ID): vol.Any(cv.positive_int, cv.string, None),
            vol.Optional(ATTR_ASSET_ID): vol.Any(cv.positive_int, cv.string, None),
            vol.Optional(ATTR_LOCATION_ID): vol.Any(cv.positive_int, cv.string, None),
            vol.Optional("due_date"): cv.string,
        }))

    hass.services.async_register(DOMAIN, SERVICE_COMPLETE_WORK_ORDER, async_complete_work_order,
        schema=vol.Schema({vol.Required(ATTR_WORK_ORDER_ID): cv.positive_int}))

    hass.services.async_register(DOMAIN, SERVICE_SET_STATUS, async_set_status,
        schema=vol.Schema({
            vol.Required(ATTR_WORK_ORDER_ID): cv.positive_int,
            vol.Required(ATTR_STATUS): vol.In(ALL_STATUSES),
        }))

    hass.services.async_register(DOMAIN, "set_asset_status", async_set_asset_status,
        schema=vol.Schema({
            vol.Required("asset_id"): cv.positive_int,
            vol.Required("status"): vol.In(ALL_ASSET_STATUSES),
        }))

    hass.services.async_register(DOMAIN, SERVICE_ADD_COMMENT, async_add_comment,
        schema=vol.Schema({
            vol.Required(ATTR_WORK_ORDER_ID): cv.positive_int,
            vol.Required(ATTR_COMMENT): cv.string,
        }))


@callback
def async_unload_services(hass: HomeAssistant) -> None:
    for s in [SERVICE_CREATE_WORK_ORDER, SERVICE_UPDATE_WORK_ORDER,
              SERVICE_COMPLETE_WORK_ORDER, SERVICE_SET_STATUS, "set_asset_status", SERVICE_ADD_COMMENT]:
        hass.services.async_remove(DOMAIN, s)
