"""Services for the MaintainX integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall, callback
import homeassistant.helpers.config_validation as cv

from .const import (
    ATTR_ASSET_ID,
    ATTR_ASSIGNEE_ID,
    ATTR_CATEGORY,
    ATTR_COMMENT,
    ATTR_DESCRIPTION,
    ATTR_LOCATION_ID,
    ATTR_PRIORITY,
    ATTR_STATUS,
    ATTR_TITLE,
    ATTR_WORK_ORDER_ID,
    CATEGORY_CORRECTIVE,
    CATEGORY_DAMAGE,
    CATEGORY_DEFAULT,
    CATEGORY_INSPECTION,
    CATEGORY_METER_READING,
    CATEGORY_PREVENTIVE,
    CATEGORY_PROJECT,
    CATEGORY_SAFETY,
    CATEGORY_UPGRADE,
    DOMAIN,
    PRIORITY_CRITICAL,
    PRIORITY_HIGH,
    PRIORITY_LOW,
    PRIORITY_MEDIUM,
    PRIORITY_NONE,
    SERVICE_ADD_COMMENT,
    SERVICE_COMPLETE_WORK_ORDER,
    SERVICE_CREATE_WORK_ORDER,
    SERVICE_UPDATE_WORK_ORDER,
    STATUS_DONE,
    STATUS_IN_PROGRESS,
    STATUS_ON_HOLD,
    STATUS_OPEN,
)

_LOGGER = logging.getLogger(__name__)

CREATE_WORK_ORDER_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_TITLE): cv.string,
        vol.Optional(ATTR_DESCRIPTION, default=""): cv.string,
        vol.Optional(ATTR_PRIORITY, default=PRIORITY_NONE): vol.In(
            [PRIORITY_NONE, PRIORITY_LOW, PRIORITY_MEDIUM, PRIORITY_HIGH, PRIORITY_CRITICAL]
        ),
        vol.Optional(ATTR_CATEGORY, default=CATEGORY_DEFAULT): vol.In(
            [
                CATEGORY_DAMAGE,
                CATEGORY_INSPECTION,
                CATEGORY_METER_READING,
                CATEGORY_PREVENTIVE,
                CATEGORY_PROJECT,
                CATEGORY_SAFETY,
                CATEGORY_UPGRADE,
                CATEGORY_CORRECTIVE,
                CATEGORY_DEFAULT,
            ]
        ),
        vol.Optional(ATTR_ASSIGNEE_ID): cv.positive_int,
        vol.Optional(ATTR_ASSET_ID): cv.positive_int,
        vol.Optional(ATTR_LOCATION_ID): cv.positive_int,
    }
)

UPDATE_WORK_ORDER_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_WORK_ORDER_ID): cv.positive_int,
        vol.Optional(ATTR_TITLE): cv.string,
        vol.Optional(ATTR_DESCRIPTION): cv.string,
        vol.Optional(ATTR_PRIORITY): vol.In(
            [PRIORITY_NONE, PRIORITY_LOW, PRIORITY_MEDIUM, PRIORITY_HIGH, PRIORITY_CRITICAL]
        ),
        vol.Optional(ATTR_STATUS): vol.In(
            [STATUS_OPEN, STATUS_IN_PROGRESS, STATUS_ON_HOLD, STATUS_DONE]
        ),
        vol.Optional(ATTR_CATEGORY): vol.In(
            [
                CATEGORY_DAMAGE,
                CATEGORY_INSPECTION,
                CATEGORY_METER_READING,
                CATEGORY_PREVENTIVE,
                CATEGORY_PROJECT,
                CATEGORY_SAFETY,
                CATEGORY_UPGRADE,
                CATEGORY_CORRECTIVE,
                CATEGORY_DEFAULT,
            ]
        ),
        vol.Optional(ATTR_ASSIGNEE_ID): cv.positive_int,
        vol.Optional(ATTR_ASSET_ID): cv.positive_int,
        vol.Optional(ATTR_LOCATION_ID): cv.positive_int,
    }
)

COMPLETE_WORK_ORDER_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_WORK_ORDER_ID): cv.positive_int,
    }
)

ADD_COMMENT_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_WORK_ORDER_ID): cv.positive_int,
        vol.Required(ATTR_COMMENT): cv.string,
    }
)


async def async_setup_services(hass: HomeAssistant) -> None:
    """Set up MaintainX services."""

    async def async_create_work_order(call: ServiceCall) -> None:
        """Create a new work order in MaintainX."""
        data: dict[str, Any] = {
            "title": call.data[ATTR_TITLE],
            "description": call.data.get(ATTR_DESCRIPTION, ""),
            "priority": call.data.get(ATTR_PRIORITY, PRIORITY_NONE),
            "categories": [call.data.get(ATTR_CATEGORY, CATEGORY_DEFAULT)],
        }

        if ATTR_ASSIGNEE_ID in call.data:
            data["assignees"] = [{"type": "USER", "id": call.data[ATTR_ASSIGNEE_ID]}]

        if ATTR_ASSET_ID in call.data:
            data["assetId"] = call.data[ATTR_ASSET_ID]

        if ATTR_LOCATION_ID in call.data:
            data["locationId"] = call.data[ATTR_LOCATION_ID]

        # Get the coordinator from any entry (supports single config entry)
        for entry_id, coordinator in hass.data[DOMAIN].items():
            try:
                result = await coordinator.client.async_create_work_order(data)
                _LOGGER.info(
                    "Created MaintainX work order: %s (ID: %s)",
                    call.data[ATTR_TITLE],
                    result.get("workOrder", {}).get("id", "unknown"),
                )
                # Refresh data
                await coordinator.async_request_refresh()
            except Exception as err:
                _LOGGER.error("Failed to create work order: %s", err)
                raise
            break

    async def async_update_work_order(call: ServiceCall) -> None:
        """Update an existing work order in MaintainX."""
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
        if ATTR_ASSIGNEE_ID in call.data:
            data["assignees"] = [{"type": "USER", "id": call.data[ATTR_ASSIGNEE_ID]}]
        if ATTR_ASSET_ID in call.data:
            data["assetId"] = call.data[ATTR_ASSET_ID]
        if ATTR_LOCATION_ID in call.data:
            data["locationId"] = call.data[ATTR_LOCATION_ID]

        for entry_id, coordinator in hass.data[DOMAIN].items():
            try:
                await coordinator.client.async_update_work_order(work_order_id, data)
                _LOGGER.info("Updated MaintainX work order ID: %s", work_order_id)
                await coordinator.async_request_refresh()
            except Exception as err:
                _LOGGER.error(
                    "Failed to update work order %s: %s", work_order_id, err
                )
                raise
            break

    async def async_complete_work_order(call: ServiceCall) -> None:
        """Mark a work order as complete."""
        work_order_id = call.data[ATTR_WORK_ORDER_ID]

        for entry_id, coordinator in hass.data[DOMAIN].items():
            try:
                await coordinator.client.async_update_work_order(
                    work_order_id, {"status": STATUS_DONE}
                )
                _LOGGER.info("Completed MaintainX work order ID: %s", work_order_id)
                await coordinator.async_request_refresh()
            except Exception as err:
                _LOGGER.error(
                    "Failed to complete work order %s: %s", work_order_id, err
                )
                raise
            break

    async def async_add_comment(call: ServiceCall) -> None:
        """Add a comment to a work order."""
        work_order_id = call.data[ATTR_WORK_ORDER_ID]
        comment = call.data[ATTR_COMMENT]

        for entry_id, coordinator in hass.data[DOMAIN].items():
            try:
                await coordinator.client.async_add_comment(work_order_id, comment)
                _LOGGER.info(
                    "Added comment to MaintainX work order ID: %s", work_order_id
                )
            except Exception as err:
                _LOGGER.error(
                    "Failed to add comment to work order %s: %s",
                    work_order_id,
                    err,
                )
                raise
            break

    hass.services.async_register(
        DOMAIN,
        SERVICE_CREATE_WORK_ORDER,
        async_create_work_order,
        schema=CREATE_WORK_ORDER_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_UPDATE_WORK_ORDER,
        async_update_work_order,
        schema=UPDATE_WORK_ORDER_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_COMPLETE_WORK_ORDER,
        async_complete_work_order,
        schema=COMPLETE_WORK_ORDER_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_ADD_COMMENT,
        async_add_comment,
        schema=ADD_COMMENT_SCHEMA,
    )


@callback
def async_unload_services(hass: HomeAssistant) -> None:
    """Unload MaintainX services."""
    hass.services.async_remove(DOMAIN, SERVICE_CREATE_WORK_ORDER)
    hass.services.async_remove(DOMAIN, SERVICE_UPDATE_WORK_ORDER)
    hass.services.async_remove(DOMAIN, SERVICE_COMPLETE_WORK_ORDER)
    hass.services.async_remove(DOMAIN, SERVICE_ADD_COMMENT)
