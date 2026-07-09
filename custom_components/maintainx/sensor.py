"""Sensor platform for MaintainX integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import MaintainXCoordinator

_LOGGER = logging.getLogger(__name__)

SENSOR_DESCRIPTIONS = [
    SensorEntityDescription(key="total_work_orders", name="MaintainX Total Work Orders", icon="mdi:clipboard-list", state_class=SensorStateClass.MEASUREMENT, native_unit_of_measurement="jobs"),
    SensorEntityDescription(key="open_work_orders", name="MaintainX Open Work Orders", icon="mdi:clipboard-alert", state_class=SensorStateClass.MEASUREMENT, native_unit_of_measurement="jobs"),
    SensorEntityDescription(key="in_progress_work_orders", name="MaintainX In Progress Work Orders", icon="mdi:clipboard-play", state_class=SensorStateClass.MEASUREMENT, native_unit_of_measurement="jobs"),
    SensorEntityDescription(key="on_hold_work_orders", name="MaintainX On Hold Work Orders", icon="mdi:clipboard-clock", state_class=SensorStateClass.MEASUREMENT, native_unit_of_measurement="jobs"),
    SensorEntityDescription(key="done_work_orders", name="MaintainX Completed Work Orders", icon="mdi:clipboard-check", state_class=SensorStateClass.MEASUREMENT, native_unit_of_measurement="jobs"),
]


def _extract_wo(wo):
    if not wo or not isinstance(wo, dict):
        return {}

    assignees = []
    for a in (wo.get("assignees", []) or []):
        if isinstance(a, dict):
            name = (a.get("displayName") or f"{a.get('firstName', '')} {a.get('lastName', '')}").strip() or "Unknown"
            assignees.append({"id": a.get("id"), "name": name, "email": a.get("email")})

    categories = wo.get("categories", []) or []
    if isinstance(categories, str):
        categories = [categories]

    asset = None
    ar = wo.get("asset")
    if isinstance(ar, dict) and ar:
        asset = {"id": ar.get("id"), "name": ar.get("name", "Unknown"), "serial_number": ar.get("serialNumber"),
                 "model": ar.get("model"), "make": ar.get("make"), "image_url": ar.get("imageUrl"),
                 "status": ar.get("status")}

    location = None
    lr = wo.get("location")
    if isinstance(lr, dict) and lr:
        location = {"id": lr.get("id"), "name": lr.get("name", "Unknown"), "address": lr.get("address")}

    images = []
    for f in (wo.get("files", []) or []):
        if isinstance(f, dict) and (f.get("contentType", "") or "").startswith("image/"):
            images.append({"name": f.get("name", "photo"), "url": f.get("url", "")})
    if wo.get("imageUrl"):
        images.append({"name": "Image", "url": wo["imageUrl"]})

    checklist = []
    for proc in (wo.get("procedures", []) or []):
        if isinstance(proc, dict):
            for task in (proc.get("tasks", proc.get("checklistItems", [])) or []):
                if isinstance(task, dict):
                    checklist.append({"name": task.get("name", task.get("label", "Item")),
                                      "completed": task.get("completed", task.get("checked", False))})
    for task in (wo.get("checklistItems", []) or []):
        if isinstance(task, dict):
            checklist.append({"name": task.get("name", task.get("label", "Item")),
                              "completed": task.get("completed", task.get("checked", False))})

    parts = [{"name": p.get("name", "Part"), "quantity": p.get("quantity")} for p in (wo.get("parts", []) or []) if isinstance(p, dict)]

    cb = wo.get("createdByUser")
    created_by = cb.get("displayName") if isinstance(cb, dict) else None

    return {
        "id": wo.get("id"), "title": wo.get("title", "Untitled"), "description": wo.get("description", ""),
        "status": wo.get("status", "UNKNOWN"), "priority": wo.get("priority", "NONE"),
        "categories": categories, "category": categories[0] if categories else None,
        "created_at": wo.get("createdAt"), "updated_at": wo.get("updatedAt"),
        "completed_at": wo.get("completedAt"), "due_date": wo.get("dueDate"),
        "assignees": assignees, "created_by": created_by,
        "asset": asset, "location": location, "images": images,
        "checklist": checklist, "parts": parts,
        "total_cost": wo.get("totalCost"),
    }


def _extract_asset(a):
    if not a or not isinstance(a, dict):
        return {}

    categories = a.get("categories", []) or []
    if isinstance(categories, str):
        categories = [categories]

    location = None
    lr = a.get("location")
    if isinstance(lr, dict) and lr:
        location = {"id": lr.get("id"), "name": lr.get("name", "Unknown")}

    return {
        "id": a.get("id"),
        "name": a.get("name", "Unknown"),
        "description": a.get("description", ""),
        "status": a.get("status", "UNKNOWN"),
        "serial_number": a.get("serialNumber"),
        "model": a.get("model"),
        "make": a.get("make"),
        "image_url": a.get("imageUrl"),
        "categories": categories,
        "category": categories[0] if categories else "Uncategorized",
        "location": location,
        "is_online": a.get("status") not in ("OFFLINE", "OUT_OF_SERVICE", "DECOMMISSIONED"),
        "barcode": a.get("barcode"),
        "area": a.get("area"),
        "created_at": a.get("createdAt"),
        "updated_at": a.get("updatedAt"),
    }


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []

    for desc in SENSOR_DESCRIPTIONS:
        entities.append(MaintainXCountSensor(coordinator, desc, entry.entry_id))

    entities.append(MaintainXRecentSensor(coordinator, entry.entry_id))
    entities.append(MaintainXAssetsSensor(coordinator, entry.entry_id))

    if coordinator.data:
        active = coordinator.data.get("open_work_orders", []) + coordinator.data.get("in_progress_work_orders", [])
        for wo in active[:10]:
            entities.append(MaintainXWOSensor(coordinator, wo, entry.entry_id))

        # Create individual asset sensors
        for asset in coordinator.data.get("assets", []):
            entities.append(MaintainXAssetSensor(coordinator, asset, entry.entry_id))

    async_add_entities(entities, True)


class MaintainXCountSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, description, entry_id):
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry_id}_{description.key}"
        self._attr_has_entity_name = True

    @callback
    def _handle_coordinator_update(self):
        self.async_write_ha_state()

    @property
    def native_value(self):
        if not self.coordinator.data:
            return 0
        m = {"total_work_orders": "total_count", "open_work_orders": "open_count",
             "in_progress_work_orders": "in_progress_count", "on_hold_work_orders": "on_hold_count",
             "done_work_orders": "done_count"}
        return self.coordinator.data.get(m.get(self.entity_description.key, ""), 0)

    @property
    def extra_state_attributes(self):
        if not self.coordinator.data:
            return {}
        m = {"total_work_orders": "work_orders", "open_work_orders": "open_work_orders",
             "in_progress_work_orders": "in_progress_work_orders", "on_hold_work_orders": "on_hold_work_orders",
             "done_work_orders": "done_work_orders"}
        key = m.get(self.entity_description.key)
        if key:
            return {"work_orders": [_extract_wo(wo) for wo in self.coordinator.data.get(key, [])[:20]]}
        return {}


class MaintainXRecentSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, entry_id):
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry_id}_recent_work_orders"
        self._attr_name = "MaintainX Recent Work Orders"
        self._attr_icon = "mdi:clipboard-text-clock"
        self._attr_has_entity_name = True

    @property
    def native_value(self):
        if not self.coordinator.data:
            return "No data"
        orders = self.coordinator.data.get("work_orders", [])
        return orders[0].get("title", "Unknown") if orders else "No work orders"

    @property
    def extra_state_attributes(self):
        if not self.coordinator.data:
            return {}
        orders = self.coordinator.data.get("work_orders", [])
        return {"recent_work_orders": [_extract_wo(wo) for wo in orders[:25]],
                "total_count": self.coordinator.data.get("total_count", 0)}


class MaintainXAssetsSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, entry_id):
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry_id}_assets"
        self._attr_name = "MaintainX Assets"
        self._attr_icon = "mdi:package-variant"
        self._attr_has_entity_name = True

    @property
    def native_value(self):
        if not self.coordinator.data:
            return 0
        return len(self.coordinator.data.get("assets", []))

    @property
    def extra_state_attributes(self):
        if not self.coordinator.data:
            return {}
        assets = self.coordinator.data.get("assets", [])
        asset_list = [_extract_asset(a) for a in assets]

        categories = {}
        for a in asset_list:
            cat = a.get("category", "Uncategorized")
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(a)

        online = len([a for a in asset_list if a.get("is_online")])
        offline = len(asset_list) - online

        return {
            "assets": asset_list,
            "categories": categories,
            "total_count": len(asset_list),
            "online_count": online,
            "offline_count": offline,
        }


class MaintainXWOSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, work_order, entry_id):
        super().__init__(coordinator)
        self._work_order_id = work_order.get("id")
        self._attr_unique_id = f"{entry_id}_wo_{self._work_order_id}"
        self._attr_name = f"MaintainX WO {self._work_order_id}"
        self._attr_has_entity_name = True
        self._work_order = work_order

    def _get_wo(self):
        if self.coordinator.data:
            for wo in self.coordinator.data.get("work_orders", []):
                if wo.get("id") == self._work_order_id:
                    return wo
        return self._work_order

    @property
    def native_value(self):
        wo = self._get_wo()
        return wo.get("status", "UNKNOWN") if wo else "UNKNOWN"

    @property
    def extra_state_attributes(self):
        wo = self._get_wo()
        return _extract_wo(wo) if wo else {}

    @property
    def icon(self):
        wo = self._get_wo()
        if wo:
            s = wo.get("status", "")
            return {"DONE": "mdi:clipboard-check", "IN_PROGRESS": "mdi:clipboard-play",
                    "ON_HOLD": "mdi:clipboard-clock", "OPEN": "mdi:clipboard-alert"}.get(s, "mdi:clipboard-text")
        return "mdi:clipboard-text"


class MaintainXAssetSensor(CoordinatorEntity, SensorEntity):
    """Sensor for an individual asset."""

    def __init__(self, coordinator, asset, entry_id):
        super().__init__(coordinator)
        self._asset_id = asset.get("id")
        self._attr_unique_id = f"{entry_id}_asset_{self._asset_id}"
        self._attr_name = f"MaintainX Asset {asset.get('name', 'Unknown')}"
        self._attr_has_entity_name = True
        self._asset = asset

    def _get_asset(self):
        if self.coordinator.data:
            for a in self.coordinator.data.get("assets", []):
                if a.get("id") == self._asset_id:
                    return a
        return self._asset

    @property
    def native_value(self):
        a = self._get_asset()
        if not a:
            return "Unknown"
        status = a.get("status", "")
        if status in ("OFFLINE", "OUT_OF_SERVICE", "DECOMMISSIONED"):
            return "Not Available"
        return "Ready"

    @property
    def extra_state_attributes(self):
        a = self._get_asset()
        if not a:
            return {}
        return _extract_asset(a)

    @property
    def icon(self):
        a = self._get_asset()
        if not a:
            return "mdi:package-variant"
        name = str(a.get("name", "")).lower()
        cats = " ".join(a.get("categories", []) or []).lower()
        combined = f"{name} {cats}"
        if any(w in combined for w in ["boat", "vessel", "yacht", "sail"]):
            return "mdi:sail-boat"
        elif any(w in combined for w in ["kayak", "canoe", "paddle"]):
            return "mdi:kayaking"
        elif any(w in combined for w in ["car", "vehicle", "truck"]):
            return "mdi:car"
        elif any(w in combined for w in ["engine", "motor", "outboard"]):
            return "mdi:engine"
        elif any(w in combined for w in ["trailer"]):
            return "mdi:truck-trailer"
        elif any(w in combined for w in ["tool"]):
            return "mdi:tools"
        elif any(w in combined for w in ["pump"]):
            return "mdi:water-pump"
        elif any(w in combined for w in ["hvac", "air", "aircon"]):
            return "mdi:air-conditioner"
        elif any(w in combined for w in ["printer"]):
            return "mdi:printer"
        elif any(w in combined for w in ["computer", "pc", "laptop"]):
            return "mdi:desktop-classic"
        return "mdi:package-variant"
