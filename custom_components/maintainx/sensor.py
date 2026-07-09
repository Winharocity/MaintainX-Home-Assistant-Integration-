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


def _extract_asset(a, all_work_orders=None):
    """Extract asset details and compute safety status."""
    if not a or not isinstance(a, dict):
        return {}

    categories = a.get("categories", []) or []
    if isinstance(categories, str):
        categories = [categories]

    location = None
    lr = a.get("location")
    if isinstance(lr, dict) and lr:
        location = {"id": lr.get("id"), "name": lr.get("name", "Unknown")}

    asset_id = a.get("id")
    asset_name = (a.get("name") or "").lower()
    asset_status = a.get("status", "")

    open_wos = []
    critical_wos = []
    high_wos = []
    safety_wos = []

    if all_work_orders and asset_id:
        for wo in all_work_orders:
            wo_status = wo.get("status", "")
            if wo_status not in ("OPEN", "IN_PROGRESS", "ON_HOLD"):
                continue

            matched = False

            # Method 1: nested asset object
            wo_asset = wo.get("asset")
            if isinstance(wo_asset, dict):
                if wo_asset.get("id") == asset_id:
                    matched = True

            # Method 2: assetId field
            if not matched and wo.get("assetId") == asset_id:
                matched = True

            # Method 3: match by asset name in title or description
            if not matched and asset_name and len(asset_name) > 3:
                wo_title = (wo.get("title") or "").lower()
                wo_desc = (wo.get("description") or "").lower()
                if asset_name in wo_title or asset_name in wo_desc:
                    matched = True

            if matched:
                priority = wo.get("priority", "NONE")
                cats = wo.get("categories", [])
                if isinstance(cats, str):
                    cats = [cats]

                wo_summary = {
                    "id": wo.get("id"),
                    "title": wo.get("title", "Untitled"),
                    "priority": priority,
                    "status": wo_status,
                    "description": wo.get("description", ""),
                    "categories": cats,
                }
                open_wos.append(wo_summary)

                if priority == "CRITICAL":
                    critical_wos.append(wo_summary)
                elif priority == "HIGH":
                    high_wos.append(wo_summary)

                if "SAFETY" in cats or "DAMAGE" in cats:
                    safety_wos.append(wo_summary)

    is_offline = asset_status in ("OFFLINE", "OUT_OF_SERVICE", "DECOMMISSIONED")
    has_critical = len(critical_wos) > 0
    has_high = len(high_wos) > 0
    has_safety_issue = len(safety_wos) > 0

    is_safe = not is_offline and not has_critical and not has_high and not has_safety_issue

    reasons = []
    if is_offline:
        reasons.append(f"Marked {asset_status.replace('_', ' ').title()}")
    if has_critical:
        for wo in critical_wos:
            reasons.append(f"🔴 CRITICAL: {wo['title']}")
    if has_high:
        for wo in high_wos:
            reasons.append(f"🟠 HIGH: {wo['title']}")
    if has_safety_issue:
        for wo in safety_wos:
            if wo not in critical_wos and wo not in high_wos:
                cat_label = "SAFETY" if "SAFETY" in wo["categories"] else "DAMAGE"
                reasons.append(f"⚠️ {cat_label}: {wo['title']}")

    return {
        "id": asset_id,
        "name": a.get("name", "Unknown"),
        "description": a.get("description", ""),
        "status": asset_status,
        "serial_number": a.get("serialNumber"),
        "model": a.get("model"),
        "make": a.get("make"),
        "image_url": a.get("imageUrl"),
        "categories": categories,
        "category": categories[0] if categories else "Uncategorized",
        "location": location,
        "is_safe": is_safe,
        "is_online": is_safe,
        "reasons": reasons,
        "open_work_orders": open_wos,
        "open_wo_count": len(open_wos),
        "critical_wo_count": len(critical_wos),
        "high_wo_count": len(high_wos),
        "safety_wo_count": len(safety_wos),
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
        all_wos = self.coordinator.data.get("work_orders", [])
        asset_list = [_extract_asset(a, all_wos) for a in assets]

        safe = len([a for a in asset_list if a.get("is_safe")])
        unsafe = len(asset_list) - safe

        return {
            "assets": asset_list,
            "total_count": len(asset_list),
            "safe_count": safe,
            "unsafe_count": unsafe,
            "online_count": safe,
            "offline_count": unsafe,
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

    def _get_asset_data(self):
        if self.coordinator.data:
            all_wos = self.coordinator.data.get("work_orders", [])
            for a in self.coordinator.data.get("assets", []):
                if a.get("id") == self._asset_id:
                    return _extract_asset(a, all_wos)
        return _extract_asset(self._asset, [])

    @property
    def native_value(self):
        data = self._get_asset_data()
        if not data:
            return "Unknown"
        return "Safe to Use" if data.get("is_safe") else "NOT SAFE"

    @property
    def extra_state_attributes(self):
        return self._get_asset_data() or {}

    @property
    def icon(self):
        data = self._get_asset_data()
        if not data:
            return "mdi:package-variant"
        name = str(data.get("name", "")).lower()
        cats = " ".join(data.get("categories", []) or []).lower()
        combined = f"{name} {cats}"
        if any(w in combined for w in ["boat", "vessel", "yacht", "sail", "boomerang", "ultimate", "rover"]):
            return "mdi:sail-boat"
        elif any(w in combined for w in ["kayak", "canoe", "paddle"]):
            return "mdi:kayaking"
        elif any(w in combined for w in ["car", "vehicle", "truck"]):
            return "mdi:car"
        elif any(w in combined for w in ["engine", "motor", "outboard"]):
            return "mdi:engine"
        elif any(w in combined for w in ["trailer"]):
            return "mdi:truck-trailer"
        elif any(w in combined for w in ["safety", "life", "jacket", "flare"]):
            return "mdi:shield-check"
        elif any(w in combined for w in ["tool"]):
            return "mdi:tools"
        elif any(w in combined for w in ["pump"]):
            return "mdi:water-pump"
        elif any(w in combined for w in ["printer"]):
            return "mdi:printer"
        return "mdi:package-variant"
