"""Sensor platform for MaintainX integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import MaintainXCoordinator

_LOGGER = logging.getLogger(__name__)

SENSOR_DESCRIPTIONS: list[SensorEntityDescription] = [
    SensorEntityDescription(
        key="total_work_orders",
        name="MaintainX Total Work Orders",
        icon="mdi:clipboard-list",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="jobs",
    ),
    SensorEntityDescription(
        key="open_work_orders",
        name="MaintainX Open Work Orders",
        icon="mdi:clipboard-alert",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="jobs",
    ),
    SensorEntityDescription(
        key="in_progress_work_orders",
        name="MaintainX In Progress Work Orders",
        icon="mdi:clipboard-play",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="jobs",
    ),
    SensorEntityDescription(
        key="on_hold_work_orders",
        name="MaintainX On Hold Work Orders",
        icon="mdi:clipboard-clock",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="jobs",
    ),
    SensorEntityDescription(
        key="done_work_orders",
        name="MaintainX Completed Work Orders",
        icon="mdi:clipboard-check",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="jobs",
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up MaintainX sensor entities."""
    coordinator: MaintainXCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SensorEntity] = []

    # Add count sensors
    for description in SENSOR_DESCRIPTIONS:
        entities.append(
            MaintainXCountSensor(coordinator, description, entry.entry_id)
        )

    # Add the recent work orders list sensor
    entities.append(
        MaintainXRecentWorkOrdersSensor(coordinator, entry.entry_id)
    )

    # Add individual work order sensors for open/in-progress items
    if coordinator.data:
        active_orders = (
            coordinator.data.get("open_work_orders", [])
            + coordinator.data.get("in_progress_work_orders", [])
        )
        for wo in active_orders[:50]:  # Limit to 50 individual sensors
            entities.append(
                MaintainXWorkOrderSensor(coordinator, wo, entry.entry_id)
            )

    async_add_entities(entities, True)


class MaintainXCountSensor(CoordinatorEntity, SensorEntity):
    """Sensor showing counts of work orders by status."""

    def __init__(
        self,
        coordinator: MaintainXCoordinator,
        description: SensorEntityDescription,
        entry_id: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry_id}_{description.key}"
        self._attr_has_entity_name = True

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if self.coordinator.data is None:
            return

        key_map = {
            "total_work_orders": "total_count",
            "open_work_orders": "open_count",
            "in_progress_work_orders": "in_progress_count",
            "on_hold_work_orders": "on_hold_count",
            "done_work_orders": "done_count",
        }

        data_key = key_map.get(self.entity_description.key)
        if data_key:
            self._attr_native_value = self.coordinator.data.get(data_key, 0)

        self.async_write_ha_state()

    @property
    def native_value(self) -> int:
        """Return the state of the sensor."""
        if self.coordinator.data is None:
            return 0

        key_map = {
            "total_work_orders": "total_count",
            "open_work_orders": "open_count",
            "in_progress_work_orders": "in_progress_count",
            "on_hold_work_orders": "on_hold_count",
            "done_work_orders": "done_count",
        }

        data_key = key_map.get(self.entity_description.key)
        if data_key:
            return self.coordinator.data.get(data_key, 0)
        return 0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        if self.coordinator.data is None:
            return {}

        attrs: dict[str, Any] = {}

        key_map = {
            "total_work_orders": "work_orders",
            "open_work_orders": "open_work_orders",
            "in_progress_work_orders": "in_progress_work_orders",
            "on_hold_work_orders": "on_hold_work_orders",
            "done_work_orders": "done_work_orders",
        }

        data_key = key_map.get(self.entity_description.key)
        if data_key:
            orders = self.coordinator.data.get(data_key, [])
            # Include up to 20 work orders as attributes
            work_order_list = []
            for wo in orders[:20]:
                work_order_list.append(
                    {
                        "id": wo.get("id"),
                        "title": wo.get("title"),
                        "status": wo.get("status"),
                        "priority": wo.get("priority"),
                        "created_at": wo.get("createdAt"),
                        "updated_at": wo.get("updatedAt"),
                    }
                )
            attrs["work_orders"] = work_order_list

        return attrs


class MaintainXRecentWorkOrdersSensor(CoordinatorEntity, SensorEntity):
    """Sensor showing recent work orders as a list."""

    def __init__(
        self,
        coordinator: MaintainXCoordinator,
        entry_id: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry_id}_recent_work_orders"
        self._attr_name = "MaintainX Recent Work Orders"
        self._attr_icon = "mdi:clipboard-text-clock"
        self._attr_has_entity_name = True

    @property
    def native_value(self) -> str:
        """Return the state — most recent work order title."""
        if self.coordinator.data is None:
            return "No data"

        orders = self.coordinator.data.get("work_orders", [])
        if orders:
            return orders[0].get("title", "Unknown")
        return "No work orders"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the last 25 work orders as attributes."""
        if self.coordinator.data is None:
            return {}

        orders = self.coordinator.data.get("work_orders", [])
        work_order_list = []
        for wo in orders[:25]:
            work_order_list.append(
                {
                    "id": wo.get("id"),
                    "title": wo.get("title"),
                    "status": wo.get("status"),
                    "priority": wo.get("priority"),
                    "category": (
                        wo.get("categories", [None])[0]
                        if wo.get("categories")
                        else None
                    ),
                    "created_at": wo.get("createdAt"),
                    "updated_at": wo.get("updatedAt"),
                    "completed_at": wo.get("completedAt"),
                    "due_date": wo.get("dueDate"),
                }
            )

        return {
            "recent_work_orders": work_order_list,
            "total_count": self.coordinator.data.get("total_count", 0),
        }


class MaintainXWorkOrderSensor(CoordinatorEntity, SensorEntity):
    """Sensor for an individual work order."""

    def __init__(
        self,
        coordinator: MaintainXCoordinator,
        work_order: dict[str, Any],
        entry_id: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._work_order_id = work_order.get("id")
        self._attr_unique_id = f"{entry_id}_wo_{self._work_order_id}"
        self._attr_name = f"MaintainX WO {self._work_order_id}"
        self._attr_icon = "mdi:clipboard-text"
        self._attr_has_entity_name = True
        self._work_order = work_order

    def _get_work_order(self) -> dict[str, Any] | None:
        """Find this work order in the coordinator data."""
        if self.coordinator.data is None:
            return self._work_order

        for wo in self.coordinator.data.get("work_orders", []):
            if wo.get("id") == self._work_order_id:
                return wo
        return self._work_order

    @property
    def native_value(self) -> str:
        """Return the work order status."""
        wo = self._get_work_order()
        if wo:
            return wo.get("status", "UNKNOWN")
        return "UNKNOWN"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return work order details as attributes."""
        wo = self._get_work_order()
        if not wo:
            return {}

        assignees = wo.get("assignees", [])
        assignee_names = [a.get("displayName", "Unknown") for a in assignees]

        return {
            "work_order_id": wo.get("id"),
            "title": wo.get("title"),
            "description": wo.get("description"),
            "status": wo.get("status"),
            "priority": wo.get("priority"),
            "categories": wo.get("categories", []),
            "assignees": assignee_names,
            "created_at": wo.get("createdAt"),
            "updated_at": wo.get("updatedAt"),
            "completed_at": wo.get("completedAt"),
            "due_date": wo.get("dueDate"),
            "asset_name": wo.get("asset", {}).get("name") if wo.get("asset") else None,
            "location_name": (
                wo.get("location", {}).get("name") if wo.get("location") else None
            ),
        }

    @property
    def icon(self) -> str:
        """Return icon based on status."""
        wo = self._get_work_order()
        if wo:
            status = wo.get("status", "")
            if status == "DONE":
                return "mdi:clipboard-check"
            elif status == "IN_PROGRESS":
                return "mdi:clipboard-play"
            elif status == "ON_HOLD":
                return "mdi:clipboard-clock"
            elif status == "OPEN":
                return "mdi:clipboard-alert"
        return "mdi:clipboard-text"
