"""Dashboard creation and management for MaintainX."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.lovelace import dashboard as lovelace_dashboard
from homeassistant.components.lovelace.const import (
    CONF_ICON,
    CONF_TITLE,
    CONF_URL_PATH,
    MODE_STORAGE,
)
from homeassistant.core import HomeAssistant, callback

from .const import (
    DASHBOARD_ICON,
    DASHBOARD_TITLE,
    DASHBOARD_URL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


def _build_dashboard_config() -> dict[str, Any]:
    """Build the full Lovelace dashboard configuration."""
    return {
        "views": [
            _build_overview_view(),
            _build_open_jobs_view(),
            _build_create_job_view(),
            _build_quick_report_view(),
            _build_all_jobs_view(),
        ]
    }


def _build_overview_view() -> dict[str, Any]:
    """Build the overview tab."""
    return {
        "title": "Overview",
        "path": "overview",
        "icon": "mdi:view-dashboard",
        "type": "sections",
        "sections": [
            {
                "type": "grid",
                "cards": [
                    {
                        "type": "heading",
                        "heading": "MaintainX Dashboard",
                        "heading_style": "title",
                        "icon": "mdi:wrench-clock",
                    },
                ],
            },
            {
                "type": "grid",
                "column_span": 4,
                "cards": [
                    {
                        "type": "entity",
                        "entity": "sensor.maintainx_open_work_orders",
                        "name": "Open",
                        "icon": "mdi:clipboard-alert",
                    },
                    {
                        "type": "entity",
                        "entity": "sensor.maintainx_in_progress_work_orders",
                        "name": "In Progress",
                        "icon": "mdi:clipboard-play",
                    },
                    {
                        "type": "entity",
                        "entity": "sensor.maintainx_on_hold_work_orders",
                        "name": "On Hold",
                        "icon": "mdi:clipboard-clock",
                    },
                    {
                        "type": "entity",
                        "entity": "sensor.maintainx_completed_work_orders",
                        "name": "Completed",
                        "icon": "mdi:clipboard-check",
                    },
                ],
            },
            {
                "type": "grid",
                "column_span": 4,
                "cards": [
                    {
                        "type": "gauge",
                        "entity": "sensor.maintainx_open_work_orders",
                        "name": "Open Jobs",
                        "min": 0,
                        "max": 50,
                        "severity": {
                            "green": 0,
                            "yellow": 10,
                            "red": 25,
                        },
                        "needle": True,
                    },
                    {
                        "type": "gauge",
                        "entity": "sensor.maintainx_in_progress_work_orders",
                        "name": "Active Jobs",
                        "min": 0,
                        "max": 50,
                        "severity": {
                            "green": 0,
                            "yellow": 10,
                            "red": 25,
                        },
                        "needle": True,
                    },
                ],
            },
            {
                "type": "grid",
                "column_span": 4,
                "cards": [
                    {
                        "type": "statistic",
                        "entity": "sensor.maintainx_total_work_orders",
                        "name": "Total Work Orders",
                        "stat_type": "state",
                        "period": {
                            "calendar": {"period": "day"},
                        },
                    },
                    {
                        "type": "markdown",
                        "content": (
                            "## 📊 Summary\n\n"
                            "| Status | Count |\n"
                            "|--------|-------|\n"
                            "| 🔴 Open | {{ states('sensor.maintainx_open_work_orders') }} |\n"
                            "| 🟡 In Progress | {{ states('sensor.maintainx_in_progress_work_orders') }} |\n"
                            "| 🟠 On Hold | {{ states('sensor.maintainx_on_hold_work_orders') }} |\n"
                            "| 🟢 Completed | {{ states('sensor.maintainx_completed_work_orders') }} |\n"
                            "| **Total** | **{{ states('sensor.maintainx_total_work_orders') }}** |\n"
                        ),
                    },
                ],
            },
        ],
    }


def _build_open_jobs_view() -> dict[str, Any]:
    """Build the open/active jobs tab."""
    return {
        "title": "Active Jobs",
        "path": "active-jobs",
        "icon": "mdi:clipboard-list",
        "type": "sections",
        "sections": [
            {
                "type": "grid",
                "cards": [
                    {
                        "type": "heading",
                        "heading": "Open Work Orders",
                        "heading_style": "title",
                        "icon": "mdi:clipboard-alert",
                    },
                ],
            },
            {
                "type": "grid",
                "column_span": 4,
                "cards": [
                    {
                        "type": "markdown",
                        "content": (
                            "{% set orders = state_attr('sensor.maintainx_open_work_orders', 'work_orders') %}\n"
                            "{% if orders and orders | length > 0 %}\n"
                            "| # | Title | Priority | Created |\n"
                            "|---|-------|----------|---------|\n"
                            "{% for wo in orders[:20] %}\n"
                            "| {{ wo.id }} | {{ wo.title }} | "
                            "{% if wo.priority == 'CRITICAL' %}🔴{% elif wo.priority == 'HIGH' %}🟠{% elif wo.priority == 'MEDIUM' %}🟡{% elif wo.priority == 'LOW' %}🟢{% else %}⚪{% endif %} "
                            "{{ wo.priority }} | {{ wo.created_at[:10] if wo.created_at else 'N/A' }} |\n"
                            "{% endfor %}\n"
                            "{% else %}\n"
                            "### ✅ No open work orders!\n"
                            "{% endif %}\n"
                        ),
                    },
                ],
            },
            {
                "type": "grid",
                "cards": [
                    {
                        "type": "heading",
                        "heading": "In Progress Work Orders",
                        "heading_style": "title",
                        "icon": "mdi:clipboard-play",
                    },
                ],
            },
            {
                "type": "grid",
                "column_span": 4,
                "cards": [
                    {
                        "type": "markdown",
                        "content": (
                            "{% set orders = state_attr('sensor.maintainx_in_progress_work_orders', 'work_orders') %}\n"
                            "{% if orders and orders | length > 0 %}\n"
                            "| # | Title | Priority | Created |\n"
                            "|---|-------|----------|---------|\n"
                            "{% for wo in orders[:20] %}\n"
                            "| {{ wo.id }} | {{ wo.title }} | "
                            "{% if wo.priority == 'CRITICAL' %}🔴{% elif wo.priority == 'HIGH' %}🟠{% elif wo.priority == 'MEDIUM' %}🟡{% elif wo.priority == 'LOW' %}🟢{% else %}⚪{% endif %} "
                            "{{ wo.priority }} | {{ wo.created_at[:10] if wo.created_at else 'N/A' }} |\n"
                            "{% endfor %}\n"
                            "{% else %}\n"
                            "### No work orders in progress\n"
                            "{% endif %}\n"
                        ),
                    },
                ],
            },
            {
                "type": "grid",
                "cards": [
                    {
                        "type": "heading",
                        "heading": "On Hold Work Orders",
                        "heading_style": "title",
                        "icon": "mdi:clipboard-clock",
                    },
                ],
            },
            {
                "type": "grid",
                "column_span": 4,
                "cards": [
                    {
                        "type": "markdown",
                        "content": (
                            "{% set orders = state_attr('sensor.maintainx_on_hold_work_orders', 'work_orders') %}\n"
                            "{% if orders and orders | length > 0 %}\n"
                            "| # | Title | Priority | Created |\n"
                            "|---|-------|----------|---------|\n"
                            "{% for wo in orders[:20] %}\n"
                            "| {{ wo.id }} | {{ wo.title }} | "
                            "{% if wo.priority == 'CRITICAL' %}🔴{% elif wo.priority == 'HIGH' %}🟠{% elif wo.priority == 'MEDIUM' %}🟡{% elif wo.priority == 'LOW' %}🟢{% else %}⚪{% endif %} "
                            "{{ wo.priority }} | {{ wo.created_at[:10] if wo.created_at else 'N/A' }} |\n"
                            "{% endfor %}\n"
                            "{% else %}\n"
                            "### No work orders on hold\n"
                            "{% endif %}\n"
                        ),
                    },
                ],
            },
        ],
    }


def _build_create_job_view() -> dict[str, Any]:
    """Build the create new job tab."""
    return {
        "title": "Create Job",
        "path": "create-job",
        "icon": "mdi:clipboard-plus",
        "type": "sections",
        "sections": [
            {
                "type": "grid",
                "cards": [
                    {
                        "type": "heading",
                        "heading": "Create New Work Order",
                        "heading_style": "title",
                        "icon": "mdi:clipboard-plus",
                    },
                ],
            },
            {
                "type": "grid",
                "column_span": 4,
                "cards": [
                    {
                        "type": "entities",
                        "title": "Work Order Details",
                        "show_header_toggle": False,
                        "entities": [
                            {
                                "entity": "input_text.maintainx_wo_title",
                                "name": "Title",
                                "icon": "mdi:format-title",
                            },
                            {
                                "entity": "input_text.maintainx_wo_description",
                                "name": "Description",
                                "icon": "mdi:text",
                            },
                            {
                                "entity": "input_select.maintainx_wo_priority",
                                "name": "Priority",
                                "icon": "mdi:alert-circle",
                            },
                            {
                                "entity": "input_select.maintainx_wo_category",
                                "name": "Category",
                                "icon": "mdi:tag",
                            },
                        ],
                    },
                ],
            },
            {
                "type": "grid",
                "column_span": 4,
                "cards": [
                    {
                        "type": "button",
                        "entity": "input_button.maintainx_create_work_order",
                        "name": "Submit Work Order",
                        "icon": "mdi:send",
                        "tap_action": {
                            "action": "toggle",
                        },
                        "icon_height": "60px",
                        "show_state": False,
                    },
                ],
            },
            {
                "type": "grid",
                "column_span": 4,
                "cards": [
                    {
                        "type": "markdown",
                        "content": (
                            "### 📝 How to Create a Work Order\n\n"
                            "1. Enter a **Title** for the work order\n"
                            "2. Add a **Description** with details\n"
                            "3. Select the **Priority** level\n"
                            "4. Choose a **Category**\n"
                            "5. Click **Submit Work Order**\n\n"
                            "The work order will be created in MaintainX automatically.\n\n"
                            "---\n"
                            "*You can also use the Quick Report buttons on the next tab "
                            "for common maintenance requests.*"
                        ),
                    },
                ],
            },
        ],
    }


def _build_quick_report_view() -> dict[str, Any]:
    """Build the quick report buttons tab."""
    return {
        "title": "Quick Report",
        "path": "quick-report",
        "icon": "mdi:lightning-bolt",
        "type": "sections",
        "sections": [
            {
                "type": "grid",
                "cards": [
                    {
                        "type": "heading",
                        "heading": "Quick Report an Issue",
                        "heading_style": "title",
                        "icon": "mdi:lightning-bolt",
                    },
                ],
            },
            {
                "type": "grid",
                "column_span": 4,
                "cards": [
                    {
                        "type": "markdown",
                        "content": (
                            "### ⚡ One-Tap Issue Reporting\n"
                            "Press any button below to instantly create a work order in MaintainX."
                        ),
                    },
                ],
            },
            {
                "type": "grid",
                "column_span": 4,
                "cards": [
                    {
                        "type": "button",
                        "entity": "input_button.maintainx_report_printer",
                        "name": "Printer Issue",
                        "icon": "mdi:printer-alert",
                        "tap_action": {"action": "toggle"},
                        "icon_height": "50px",
                        "show_state": False,
                    },
                    {
                        "type": "button",
                        "entity": "input_button.maintainx_report_hvac",
                        "name": "HVAC Issue",
                        "icon": "mdi:hvac",
                        "tap_action": {"action": "toggle"},
                        "icon_height": "50px",
                        "show_state": False,
                    },
                    {
                        "type": "button",
                        "entity": "input_button.maintainx_report_plumbing",
                        "name": "Plumbing Issue",
                        "icon": "mdi:water-pump",
                        "tap_action": {"action": "toggle"},
                        "icon_height": "50px",
                        "show_state": False,
                    },
                ],
            },
            {
                "type": "grid",
                "column_span": 4,
                "cards": [
                    {
                        "type": "button",
                        "entity": "input_button.maintainx_report_electrical",
                        "name": "Electrical Issue",
                        "icon": "mdi:flash-alert",
                        "tap_action": {"action": "toggle"},
                        "icon_height": "50px",
                        "show_state": False,
                    },
                    {
                        "type": "button",
                        "entity": "input_button.maintainx_report_safety",
                        "name": "Safety Hazard",
                        "icon": "mdi:shield-alert",
                        "tap_action": {"action": "toggle"},
                        "icon_height": "50px",
                        "show_state": False,
                    },
                    {
                        "type": "button",
                        "entity": "input_button.maintainx_report_general",
                        "name": "General Maintenance",
                        "icon": "mdi:wrench",
                        "tap_action": {"action": "toggle"},
                        "icon_height": "50px",
                        "show_state": False,
                    },
                ],
            },
        ],
    }


def _build_all_jobs_view() -> dict[str, Any]:
    """Build the all jobs / recent history tab."""
    return {
        "title": "All Jobs",
        "path": "all-jobs",
        "icon": "mdi:clipboard-text-clock",
        "type": "sections",
        "sections": [
            {
                "type": "grid",
                "cards": [
                    {
                        "type": "heading",
                        "heading": "Recent Work Orders",
                        "heading_style": "title",
                        "icon": "mdi:clipboard-text-clock",
                    },
                ],
            },
            {
                "type": "grid",
                "column_span": 4,
                "cards": [
                    {
                        "type": "markdown",
                        "content": (
                            "{% set orders = state_attr('sensor.maintainx_recent_work_orders', 'recent_work_orders') %}\n"
                            "{% if orders and orders | length > 0 %}\n"
                            "| ID | Title | Status | Priority | Category | Created |\n"
                            "|----|-------|--------|----------|----------|---------|\n"
                            "{% for wo in orders %}\n"
                            "| {{ wo.id }} | {{ wo.title[:40] }} | "
                            "{% if wo.status == 'OPEN' %}🔴{% elif wo.status == 'IN_PROGRESS' %}🟡{% elif wo.status == 'ON_HOLD' %}🟠{% elif wo.status == 'DONE' %}🟢{% else %}⚪{% endif %} "
                            "{{ wo.status }} | "
                            "{% if wo.priority == 'CRITICAL' %}🔴{% elif wo.priority == 'HIGH' %}🟠{% elif wo.priority == 'MEDIUM' %}🟡{% elif wo.priority == 'LOW' %}🟢{% else %}⚪{% endif %} "
                            "{{ wo.priority }} | {{ wo.category if wo.category else 'N/A' }} | "
                            "{{ wo.created_at[:10] if wo.created_at else 'N/A' }} |\n"
                            "{% endfor %}\n"
                            "{% else %}\n"
                            "### No work orders found\n"
                            "{% endif %}\n"
                        ),
                    },
                ],
            },
            {
                "type": "grid",
                "column_span": 4,
                "cards": [
                    {
                        "type": "entities",
                        "title": "Sensors",
                        "entities": [
                            "sensor.maintainx_total_work_orders",
                            "sensor.maintainx_open_work_orders",
                            "sensor.maintainx_in_progress_work_orders",
                            "sensor.maintainx_on_hold_work_orders",
                            "sensor.maintainx_completed_work_orders",
                            "sensor.maintainx_recent_work_orders",
                        ],
                    },
                ],
            },
        ],
    }


async def async_setup_dashboard(hass: HomeAssistant) -> None:
    """Create the MaintainX dashboard in the sidebar."""
    try:
        # Create input helpers for the create job form
        await _async_create_input_helpers(hass)

        # Create automations for the quick report buttons and form submission
        await _async_create_automations(hass)

        # Register the dashboard
        await _async_register_dashboard(hass)

    except Exception as err:
        _LOGGER.error("Failed to set up MaintainX dashboard: %s", err)


async def _async_create_input_helpers(hass: HomeAssistant) -> None:
    """Create input_text, input_select, and input_button helpers."""

    # input_text: Work Order Title
    try:
        await hass.services.async_call(
            "input_text",
            "reload",
            blocking=True,
        )
    except Exception:
        pass

    helpers_to_create = [
        {
            "domain": "input_text",
            "object_id": "maintainx_wo_title",
            "name": "MaintainX WO Title",
            "icon": "mdi:format-title",
            "max": 255,
            "initial": "",
        },
        {
            "domain": "input_text",
            "object_id": "maintainx_wo_description",
            "name": "MaintainX WO Description",
            "icon": "mdi:text",
            "max": 255,
            "initial": "",
        },
    ]

    selects_to_create = [
        {
            "domain": "input_select",
            "object_id": "maintainx_wo_priority",
            "name": "MaintainX WO Priority",
            "icon": "mdi:alert-circle",
            "options": ["NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"],
            "initial": "NONE",
        },
        {
            "domain": "input_select",
            "object_id": "maintainx_wo_category",
            "name": "MaintainX WO Category",
            "icon": "mdi:tag",
            "options": [
                "DEFAULT",
                "CORRECTIVE",
                "PREVENTIVE",
                "DAMAGE",
                "INSPECTION",
                "SAFETY",
                "UPGRADE",
                "PROJECT",
                "METER_READING",
            ],
            "initial": "DEFAULT",
        },
    ]

    buttons_to_create = [
        {
            "object_id": "maintainx_create_work_order",
            "name": "MaintainX Create Work Order",
            "icon": "mdi:send",
        },
        {
            "object_id": "maintainx_report_printer",
            "name": "MaintainX Report Printer Issue",
            "icon": "mdi:printer-alert",
        },
        {
            "object_id": "maintainx_report_hvac",
            "name": "MaintainX Report HVAC Issue",
            "icon": "mdi:hvac",
        },
        {
            "object_id": "maintainx_report_plumbing",
            "name": "MaintainX Report Plumbing Issue",
            "icon": "mdi:water-pump",
        },
        {
            "object_id": "maintainx_report_electrical",
            "name": "MaintainX Report Electrical Issue",
            "icon": "mdi:flash-alert",
        },
        {
            "object_id": "maintainx_report_general",
            "name": "MaintainX Report General Maintenance",
            "icon": "mdi:wrench",
        },
        {
            "object_id": "maintainx_report_safety",
            "name": "MaintainX Report Safety Hazard",
            "icon": "mdi:shield-alert",
        },
    ]

    # Create helpers using the helpers collection
    from homeassistant.helpers import collection, entity_registry

    er = entity_registry.async_get(hass)

    # Create input_text entities
    for helper in helpers_to_create:
        entity_id = f"input_text.{helper['object_id']}"
        if not er.async_get(entity_id):
            try:
                await hass.services.async_call(
                    "input_text",
                    "create" if hasattr(hass.services, "has_service") else "reload",
                    {
                        "name": helper["name"],
                        "icon": helper["icon"],
                        "max": helper.get("max", 255),
                        "initial": helper.get("initial", ""),
                    },
                    blocking=True,
                )
            except Exception:
                _LOGGER.debug("Will create %s via storage", entity_id)

    # Use the storage-based approach for helpers
    for helper in helpers_to_create:
        entity_id = f"input_text.{helper['object_id']}"
        if er.async_get(entity_id):
            continue
        await _create_input_text(hass, helper)

    for select in selects_to_create:
        entity_id = f"input_select.{select['object_id']}"
        if er.async_get(entity_id):
            continue
        await _create_input_select(hass, select)

    for button in buttons_to_create:
        entity_id = f"input_button.{button['object_id']}"
        if er.async_get(entity_id):
            continue
        await _create_input_button(hass, button)


async def _create_input_text(hass: HomeAssistant, config: dict) -> None:
    """Create an input_text helper via the websocket-style collection."""
    try:
        if "input_text" in hass.data:
            input_text_collection = None
            for key, val in hass.data["input_text"].items():
                if hasattr(val, "async_create_item"):
                    input_text_collection = val
                    break

            if input_text_collection:
                await input_text_collection.async_create_item(
                    {
                        "id": config["object_id"],
                        "name": config["name"],
                        "icon": config.get("icon"),
                        "max": config.get("max", 255),
                        "min": config.get("min", 0),
                        "initial": config.get("initial", ""),
                        "mode": "text",
                    }
                )
                return

        # Fallback: write to storage directly
        from homeassistant.helpers.storage import Store

        store = Store(hass, 1, "input_text")
        data = await store.async_load() or {"items": []}
        items = data.get("items", [])

        existing_ids = [item["id"] for item in items]
        if config["object_id"] not in existing_ids:
            items.append(
                {
                    "id": config["object_id"],
                    "name": config["name"],
                    "icon": config.get("icon", ""),
                    "max": config.get("max", 255),
                    "min": config.get("min", 0),
                    "initial": config.get("initial", ""),
                    "mode": "text",
                    "pattern": "",
                }
            )
            data["items"] = items
            await store.async_save(data)

    except Exception as err:
        _LOGGER.warning("Could not create input_text %s: %s", config["object_id"], err)


async def _create_input_select(hass: HomeAssistant, config: dict) -> None:
    """Create an input_select helper."""
    try:
        if "input_select" in hass.data:
            input_select_collection = None
            for key, val in hass.data["input_select"].items():
                if hasattr(val, "async_create_item"):
                    input_select_collection = val
                    break

            if input_select_collection:
                await input_select_collection.async_create_item(
                    {
                        "id": config["object_id"],
                        "name": config["name"],
                        "icon": config.get("icon"),
                        "options": config["options"],
                        "initial": config.get("initial"),
                    }
                )
                return

        from homeassistant.helpers.storage import Store

        store = Store(hass, 1, "input_select")
        data = await store.async_load() or {"items": []}
        items = data.get("items", [])

        existing_ids = [item["id"] for item in items]
        if config["object_id"] not in existing_ids:
            items.append(
                {
                    "id": config["object_id"],
                    "name": config["name"],
                    "icon": config.get("icon", ""),
                    "options": config["options"],
                    "initial": config.get("initial"),
                }
            )
            data["items"] = items
            await store.async_save(data)

    except Exception as err:
        _LOGGER.warning("Could not create input_select %s: %s", config["object_id"], err)


async def _create_input_button(hass: HomeAssistant, config: dict) -> None:
    """Create an input_button helper."""
    try:
        if "input_button" in hass.data:
            input_button_collection = None
            for key, val in hass.data["input_button"].items():
                if hasattr(val, "async_create_item"):
                    input_button_collection = val
                    break

            if input_button_collection:
                await input_button_collection.async_create_item(
                    {
                        "id": config["object_id"],
                        "name": config["name"],
                        "icon": config.get("icon"),
                    }
                )
                return

        from homeassistant.helpers.storage import Store

        store = Store(hass, 1, "input_button")
        data = await store.async_load() or {"items": []}
        items = data.get("items", [])

        existing_ids = [item["id"] for item in items]
        if config["object_id"] not in existing_ids:
            items.append(
                {
                    "id": config["object_id"],
                    "name": config["name"],
                    "icon": config.get("icon", ""),
                }
            )
            data["items"] = items
            await store.async_save(data)

    except Exception as err:
        _LOGGER.warning("Could not create input_button %s: %s", config["object_id"], err)


async def _async_create_automations(hass: HomeAssistant) -> None:
    """Create automations for the dashboard buttons."""
    from homeassistant.helpers.storage import Store

    automations = [
        {
            "id": "maintainx_submit_work_order",
            "alias": "MaintainX: Submit Work Order Form",
            "description": "Creates a MaintainX work order from the dashboard form",
            "trigger": [
                {
                    "platform": "state",
                    "entity_id": "input_button.maintainx_create_work_order",
                }
            ],
            "condition": [
                {
                    "condition": "template",
                    "value_template": "{{ states('input_text.maintainx_wo_title') | length > 0 }}",
                }
            ],
            "action": [
                {
                    "service": "maintainx.create_work_order",
                    "data": {
                        "title": "{{ states('input_text.maintainx_wo_title') }}",
                        "description": "{{ states('input_text.maintainx_wo_description') }}",
                        "priority": "{{ states('input_select.maintainx_wo_priority') }}",
                        "category": "{{ states('input_select.maintainx_wo_category') }}",
                    },
                },
                {
                    "service": "input_text.set_value",
                    "target": {"entity_id": "input_text.maintainx_wo_title"},
                    "data": {"value": ""},
                },
                {
                    "service": "input_text.set_value",
                    "target": {"entity_id": "input_text.maintainx_wo_description"},
                    "data": {"value": ""},
                },
                {
                    "service": "input_select.select_option",
                    "target": {"entity_id": "input_select.maintainx_wo_priority"},
                    "data": {"option": "NONE"},
                },
                {
                    "service": "input_select.select_option",
                    "target": {"entity_id": "input_select.maintainx_wo_category"},
                    "data": {"option": "DEFAULT"},
                },
                {
                    "service": "persistent_notification.create",
                    "data": {
                        "title": "MaintainX",
                        "message": "Work order created successfully!",
                    },
                },
            ],
            "mode": "single",
        },
        {
            "id": "maintainx_quick_report_printer",
            "alias": "MaintainX: Quick Report - Printer Issue",
            "description": "Quick report a printer issue to MaintainX",
            "trigger": [
                {
                    "platform": "state",
                    "entity_id": "input_button.maintainx_report_printer",
                }
            ],
            "action": [
                {
                    "service": "maintainx.create_work_order",
                    "data": {
                        "title": "Printer Issue Reported",
                        "description": "Printer issue reported via Home Assistant dashboard at {{ now().strftime('%Y-%m-%d %H:%M:%S') }}",
                        "priority": "MEDIUM",
                        "category": "CORRECTIVE",
                    },
                },
                {
                    "service": "persistent_notification.create",
                    "data": {
                        "title": "MaintainX",
                        "message": "🖨️ Printer issue reported successfully!",
                    },
                },
            ],
            "mode": "single",
        },
        {
            "id": "maintainx_quick_report_hvac",
            "alias": "MaintainX: Quick Report - HVAC Issue",
            "description": "Quick report an HVAC issue to MaintainX",
            "trigger": [
                {
                    "platform": "state",
                    "entity_id": "input_button.maintainx_report_hvac",
                }
            ],
            "action": [
                {
                    "service": "maintainx.create_work_order",
                    "data": {
                        "title": "HVAC Issue Reported",
                        "description": "HVAC issue reported via Home Assistant dashboard at {{ now().strftime('%Y-%m-%d %H:%M:%S') }}",
                        "priority": "HIGH",
                        "category": "CORRECTIVE",
                    },
                },
                {
                    "service": "persistent_notification.create",
                    "data": {
                        "title": "MaintainX",
                        "message": "❄️ HVAC issue reported successfully!",
                    },
                },
            ],
            "mode": "single",
        },
        {
            "id": "maintainx_quick_report_plumbing",
            "alias": "MaintainX: Quick Report - Plumbing Issue",
            "description": "Quick report a plumbing issue to MaintainX",
            "trigger": [
                {
                    "platform": "state",
                    "entity_id": "input_button.maintainx_report_plumbing",
                }
            ],
            "action": [
                {
                    "service": "maintainx.create_work_order",
                    "data": {
                        "title": "Plumbing Issue Reported",
                        "description": "Plumbing issue reported via Home Assistant dashboard at {{ now().strftime('%Y-%m-%d %H:%M:%S') }}",
                        "priority": "HIGH",
                        "category": "CORRECTIVE",
                    },
                },
                {
                    "service": "persistent_notification.create",
                    "data": {
                        "title": "MaintainX",
                        "message": "🔧 Plumbing issue reported successfully!",
                    },
                },
            ],
            "mode": "single",
        },
        {
            "id": "maintainx_quick_report_electrical",
            "alias": "MaintainX: Quick Report - Electrical Issue",
            "description": "Quick report an electrical issue to MaintainX",
            "trigger": [
                {
                    "platform": "state",
                    "entity_id": "input_button.maintainx_report_electrical",
                }
            ],
            "action": [
                {
                    "service": "maintainx.create_work_order",
                    "data": {
                        "title": "Electrical Issue Reported",
                        "description": "Electrical issue reported via Home Assistant dashboard at {{ now().strftime('%Y-%m-%d %H:%M:%S') }}",
                        "priority": "HIGH",
                        "category": "CORRECTIVE",
                    },
                },
                {
                    "service": "persistent_notification.create",
                    "data": {
                        "title": "MaintainX",
                        "message": "⚡ Electrical issue reported successfully!",
                    },
                },
            ],
            "mode": "single",
        },
        {
            "id": "maintainx_quick_report_safety",
            "alias": "MaintainX: Quick Report - Safety Hazard",
            "description": "Quick report a safety hazard to MaintainX",
            "trigger": [
                {
                    "platform": "state",
                    "entity_id": "input_button.maintainx_report_safety",
                }
            ],
            "action": [
                {
                    "service": "maintainx.create_work_order",
                    "data": {
                        "title": "Safety Hazard Reported",
                        "description": "SAFETY HAZARD reported via Home Assistant dashboard at {{ now().strftime('%Y-%m-%d %H:%M:%S') }}. Immediate attention required!",
                        "priority": "CRITICAL",
                        "category": "SAFETY",
                    },
                },
                {
                    "service": "persistent_notification.create",
                    "data": {
                        "title": "MaintainX",
                        "message": "🛡️ Safety hazard reported successfully!",
                    },
                },
            ],
            "mode": "single",
        },
        {
            "id": "maintainx_quick_report_general",
            "alias": "MaintainX: Quick Report - General Maintenance",
            "description": "Quick report general maintenance to MaintainX",
            "trigger": [
                {
                    "platform": "state",
                    "entity_id": "input_button.maintainx_report_general",
                }
            ],
            "action": [
                {
                    "service": "maintainx.create_work_order",
                    "data": {
                        "title": "General Maintenance Request",
                        "description": "General maintenance requested via Home Assistant dashboard at {{ now().strftime('%Y-%m-%d %H:%M:%S') }}",
                        "priority": "LOW",
                        "category": "DEFAULT",
                    },
                },
                {
                    "service": "persistent_notification.create",
                    "data": {
                        "title": "MaintainX",
                        "message": "🔧 General maintenance request submitted!",
                    },
                },
            ],
            "mode": "single",
        },
    ]

    # Save automations to storage
    store = Store(hass, 1, "automations")
    existing_data = await store.async_load() or []

    if isinstance(existing_data, dict):
        existing_automations = existing_data.get("data", [])
    else:
        existing_automations = existing_data

    existing_ids = {a.get("id") for a in existing_automations if isinstance(a, dict)}

    new_automations_added = False
    for automation in automations:
        if automation["id"] not in existing_ids:
            existing_automations.append(automation)
            new_automations_added = True

    if new_automations_added:
        await store.async_save(existing_automations)

        # Reload automations
        try:
            await hass.services.async_call(
                "automation", "reload", blocking=True
            )
        except Exception as err:
            _LOGGER.warning("Could not reload automations: %s", err)


async def _async_register_dashboard(hass: HomeAssistant) -> None:
    """Register the MaintainX dashboard in the Lovelace sidebar."""
    try:
        lovelace_config = _build_dashboard_config()

        # Use the Lovelace storage to create the dashboard
        from homeassistant.components.lovelace import (
            const as lovelace_const,
        )

        # Check if dashboard already exists
        dashboards = hass.data.get("lovelace_dashboards", {})
        if DASHBOARD_URL in dashboards:
            _LOGGER.debug("MaintainX dashboard already exists")
            return

        # Create dashboard via lovelace storage
        from homeassistant.helpers.storage import Store

        # Register the dashboard configuration
        dashboard_store = Store(
            hass, 1, f"lovelace.{DASHBOARD_URL}"
        )
        await dashboard_store.async_save(
            {"data": lovelace_config, "key": DASHBOARD_URL, "type": "storage"}
        )

        # Register the dashboard in the lovelace dashboards config
        dashboards_store = Store(hass, 1, "lovelace_dashboards")
        dashboards_data = await dashboards_store.async_load() or {"items": []}

        if isinstance(dashboards_data, list):
            items = dashboards_data
        else:
            items = dashboards_data.get("items", [])

        existing_urls = [d.get("url_path") for d in items if isinstance(d, dict)]
        if DASHBOARD_URL not in existing_urls:
            items.append(
                {
                    "id": DASHBOARD_URL,
                    "url_path": DASHBOARD_URL,
                    "title": DASHBOARD_TITLE,
                    "icon": DASHBOARD_ICON,
                    "show_in_sidebar": True,
                    "require_admin": False,
                    "mode": "storage",
                }
            )

            if isinstance(dashboards_data, list):
                await dashboards_store.async_save(items)
            else:
                dashboards_data["items"] = items
                await dashboards_store.async_save(dashboards_data)

            _LOGGER.info("MaintainX dashboard registered - restart may be needed")

            # Try to dynamically register the dashboard
            try:
                from homeassistant.components.lovelace.dashboard import (
                    LovelaceStorage,
                )

                new_dashboard = LovelaceStorage(hass, None, {
                    "id": DASHBOARD_URL,
                    "url_path": DASHBOARD_URL,
                    "title": DASHBOARD_TITLE,
                    "icon": DASHBOARD_ICON,
                    "show_in_sidebar": True,
                    "require_admin": False,
                    "mode": "storage",
                })

                if "lovelace_dashboards" not in hass.data:
                    hass.data["lovelace_dashboards"] = {}

                hass.data["lovelace_dashboards"][DASHBOARD_URL] = new_dashboard

                # Register panel in sidebar
                from homeassistant.components.frontend import (
                    async_register_built_in_panel,
                )

                hass.components.frontend.async_register_built_in_panel(
                    "lovelace",
                    DASHBOARD_TITLE,
                    DASHBOARD_ICON,
                    url_path=DASHBOARD_URL,
                    config={"mode": "storage"},
                    require_admin=False,
                )

                _LOGGER.info("MaintainX dashboard added to sidebar successfully")

            except Exception as err:
                _LOGGER.warning(
                    "Dashboard registered in storage but dynamic registration failed: %s. "
                    "A restart may be needed for the dashboard to appear.",
                    err,
                )

    except Exception as err:
        _LOGGER.error("Failed to register MaintainX dashboard: %s", err)


async def async_remove_dashboard(hass: HomeAssistant) -> None:
    """Remove the MaintainX dashboard from the sidebar."""
    try:
        from homeassistant.helpers.storage import Store

        # Remove dashboard config
        dashboard_store = Store(hass, 1, f"lovelace.{DASHBOARD_URL}")
        await dashboard_store.async_remove()

        # Remove from dashboards list
        dashboards_store = Store(hass, 1, "lovelace_dashboards")
        dashboards_data = await dashboards_store.async_load() or {"items": []}

        if isinstance(dashboards_data, list):
            items = [d for d in dashboards_data if d.get("url_path") != DASHBOARD_URL]
            await dashboards_store.async_save(items)
        else:
            items = dashboards_data.get("items", [])
            items = [d for d in items if d.get("url_path") != DASHBOARD_URL]
            dashboards_data["items"] = items
            await dashboards_store.async_save(dashboards_data)

        # Remove from runtime
        if "lovelace_dashboards" in hass.data:
            hass.data["lovelace_dashboards"].pop(DASHBOARD_URL, None)

        # Try to remove the panel
        try:
            hass.components.frontend.async_remove_panel(DASHBOARD_URL)
        except Exception:
            pass

        _LOGGER.info("MaintainX dashboard removed")

    except Exception as err:
        _LOGGER.error("Failed to remove MaintainX dashboard: %s", err)
