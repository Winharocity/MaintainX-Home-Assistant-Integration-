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


def _safe_get(obj: Any, key: str, default: Any = None) -> Any:
    """Safely get a value from a dict or return default."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return default


def _extract_work_order_detail(wo: dict[str, Any]) -> dict[str, Any]:
    """Extract full detail from a work order for attributes."""
    if not wo or not isinstance(wo, dict):
        return {}

    # Assignees
    assignees_raw = wo.get("assignees", []) or []
    assignee_list = []
    for a in assignees_raw:
        if isinstance(a, dict):
            first = a.get("firstName", "") or ""
            last = a.get("lastName", "") or ""
            display = a.get("displayName", "") or f"{first} {last}".strip()
            assignee_list.append({
                "id": a.get("id"),
                "name": display if display else "Unknown",
                "email": a.get("email"),
                "type": a.get("type"),
            })

    # Categories
    categories = wo.get("categories", []) or []
    if isinstance(categories, str):
        categories = [categories]

    # Asset
    asset_raw = wo.get("asset")
    asset_info = None
    if isinstance(asset_raw, dict) and asset_raw:
        asset_info = {
            "id": asset_raw.get("id"),
            "name": asset_raw.get("name", "Unknown"),
            "description": asset_raw.get("description"),
            "serial_number": asset_raw.get("serialNumber"),
            "model": asset_raw.get("model"),
            "make": asset_raw.get("make"),
            "image_url": asset_raw.get("imageUrl"),
        }

    # Location
    location_raw = wo.get("location")
    location_info = None
    if isinstance(location_raw, dict) and location_raw:
        location_info = {
            "id": location_raw.get("id"),
            "name": location_raw.get("name", "Unknown"),
            "address": location_raw.get("address"),
        }

    # Files / Images
    files_raw = wo.get("files", []) or []
    images = []
    attachments = []
    for f in files_raw:
        if isinstance(f, dict):
            file_info = {
                "id": f.get("id"),
                "name": f.get("name", "file"),
                "url": f.get("url", ""),
                "content_type": f.get("contentType", ""),
                "created_at": f.get("createdAt"),
            }
            content_type = f.get("contentType", "") or ""
            if content_type.startswith("image/"):
                images.append(file_info)
            else:
                attachments.append(file_info)

    # Checklist / Procedures
    checklist_items = []
    procedures = wo.get("procedures", []) or []
    for proc in procedures:
        if isinstance(proc, dict):
            tasks = proc.get("tasks", proc.get("checklistItems", [])) or []
            for task in tasks:
                if isinstance(task, dict):
                    checklist_items.append({
                        "name": task.get("name", task.get("label", "Item")),
                        "completed": task.get("completed", task.get("checked", False)),
                        "type": task.get("type"),
                    })

    # Also check top-level checklistItems
    top_checklist = wo.get("checklistItems", []) or []
    for task in top_checklist:
        if isinstance(task, dict):
            checklist_items.append({
                "name": task.get("name", task.get("label", "Item")),
                "completed": task.get("completed", task.get("checked", False)),
                "type": task.get("type"),
            })

    # Parts
    parts_raw = wo.get("parts", []) or []
    parts_list = []
    for p in parts_raw:
        if isinstance(p, dict):
            parts_list.append({
                "id": p.get("id"),
                "name": p.get("name", "Part"),
                "quantity": p.get("quantity"),
                "unit_cost": p.get("unitCost"),
                "total_cost": p.get("totalCost"),
            })

    # Time logs
    time_raw = wo.get("timeLogs", []) or []
    time_list = []
    for t in time_raw:
        if isinstance(t, dict):
            user_data = t.get("user", {}) or {}
            time_list.append({
                "user": user_data.get("displayName", "Unknown") if isinstance(user_data, dict) else "Unknown",
                "duration_minutes": t.get("durationInMinutes"),
                "started_at": t.get("startedAt"),
                "ended_at": t.get("endedAt"),
                "hourly_rate": t.get("hourlyRate"),
            })

    # Created by
    created_by_raw = wo.get("createdByUser")
    created_by = None
    if isinstance(created_by_raw, dict):
        created_by = created_by_raw.get("displayName")

    return {
        "id": wo.get("id"),
        "title": wo.get("title", "Untitled"),
        "description": wo.get("description", ""),
        "status": wo.get("status", "UNKNOWN"),
        "priority": wo.get("priority", "NONE"),
        "categories": categories,
        "category": categories[0] if categories else None,
        "work_order_number": wo.get("number"),
        "created_at": wo.get("createdAt"),
        "updated_at": wo.get("updatedAt"),
        "completed_at": wo.get("completedAt"),
        "due_date": wo.get("dueDate"),
        "started_at": wo.get("startedAt"),
        "estimated_duration": wo.get("estimatedDuration"),
        "actual_duration": wo.get("actualDuration"),
        "assignees": assignee_list,
        "created_by": created_by,
        "asset": asset_info,
        "location": location_info,
        "images": images,
        "attachments": attachments,
        "checklist": checklist_items,
        "parts": parts_list,
        "time_logs": time_list,
        "total_cost": wo.get("totalCost"),
        "labor_cost": wo.get("laborCost"),
        "parts_cost": wo.get("partsCost"),
        "additional_cost": wo.get("additionalCost"),
    }


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up MaintainX sensor entities."""
    coordinator: MaintainXCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SensorEntity] = []

    for description in SENSOR_DESCRIPTIONS:
        entities.append(
            MaintainXCountSensor(coordinator, description, entry.entry_id)
        )

    entities.append(
        MaintainXRecentWorkOrdersSensor(coordinator, entry.entry_id)
    )

    if coordinator.data:
        active_orders = (
            coordinator.data.get("open_work_orders", [])
            + coordinator.data.get("in_progress_work_orders", [])
        )
        for wo in active_orders[:50]:
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
        """Handle updated data."""
        self.async_write_ha_state()

    @property
    def native_value(self) -> int:
        """Return the state."""
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
            work_order_list = []
            for wo in orders[:20]:
                work_order_list.append(_extract_work_order_detail(wo))
            return {"work_orders": work_order_list}

        return {}


class MaintainXRecentWorkOrdersSensor(CoordinatorEntity, SensorEntity):
    """Sensor showing recent work orders."""

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
        """Return the state."""
        if self.coordinator.data is None:
            return "No data"

        orders = self.coordinator.data.get("work_orders", [])
        if orders:
            return orders[0].get("title", "Unknown")
        return "No work orders"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the last 25 work orders with full detail."""
        if self.coordinator.data is None:
            return {}

        orders = self.coordinator.data.get("work_orders", [])
        work_order_list = []
        for wo in orders[:25]:
            work_order_list.append(_extract_work_order_detail(wo))

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
        """Return full work order details."""
        wo = self._get_work_order()
        if not wo:
            return {}
        return _extract_work_order_detail(wo)

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
