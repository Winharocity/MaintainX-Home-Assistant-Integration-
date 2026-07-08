"""Dashboard setup for MaintainX."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

_LOGGER = logging.getLogger(__name__)


def generate_dashboard_yaml() -> str:
    """Generate the complete dashboard YAML content."""
    return '''title: MaintainX
views:

  ##############################################
  # TAB 1 — OVERVIEW
  ##############################################
  - title: Overview
    path: overview
    icon: mdi:view-dashboard
    badges: []
    cards:

      - type: markdown
        content: "# 🔧 MaintainX Dashboard"

      - type: horizontal-stack
        cards:
          - type: entity
            entity: sensor.maintainx_open_work_orders
            name: Open
            icon: mdi:clipboard-alert
          - type: entity
            entity: sensor.maintainx_in_progress_work_orders
            name: In Progress
            icon: mdi:clipboard-play
          - type: entity
            entity: sensor.maintainx_on_hold_work_orders
            name: On Hold
            icon: mdi:clipboard-clock
          - type: entity
            entity: sensor.maintainx_completed_work_orders
            name: Completed
            icon: mdi:clipboard-check

      - type: horizontal-stack
        cards:
          - type: gauge
            entity: sensor.maintainx_open_work_orders
            name: Open Jobs
            min: 0
            max: 50
            severity:
              green: 0
              yellow: 10
              red: 25
            needle: true
          - type: gauge
            entity: sensor.maintainx_in_progress_work_orders
            name: Active Jobs
            min: 0
            max: 50
            severity:
              green: 0
              yellow: 10
              red: 25
            needle: true

      - type: markdown
        content: >
          ## 📊 Summary


          | Status | Count |

          |--------|-------|

          | 🔴 Open | {{ states('sensor.maintainx_open_work_orders') }} |

          | 🟡 In Progress | {{ states('sensor.maintainx_in_progress_work_orders') }} |

          | 🟠 On Hold | {{ states('sensor.maintainx_on_hold_work_orders') }} |

          | 🟢 Completed | {{ states('sensor.maintainx_completed_work_orders') }} |

          | **Total** | **{{ states('sensor.maintainx_total_work_orders') }}** |

  ##############################################
  # TAB 2 — ACTIVE JOBS
  ##############################################
  - title: Active Jobs
    path: active-jobs
    icon: mdi:clipboard-list
    badges: []
    cards:

      - type: markdown
        title: 🔴 Open Work Orders
        content: >
          {% set orders = state_attr('sensor.maintainx_open_work_orders', 'work_orders') %}

          {% if orders and orders | length > 0 %}

          | # | Title | Priority | Created |

          |---|-------|----------|---------|

          {% for wo in orders[:20] %}

          | {{ wo.id }} | {{ wo.title }} | {% if wo.priority == 'CRITICAL' %}🔴{% elif wo.priority == 'HIGH' %}🟠{% elif wo.priority == 'MEDIUM' %}🟡{% elif wo.priority == 'LOW' %}🟢{% else %}⚪{% endif %} {{ wo.priority }} | {{ wo.created_at[:10] if wo.created_at else 'N/A' }} |

          {% endfor %}

          {% else %}

          ✅ No open work orders!

          {% endif %}

      - type: markdown
        title: 🟡 In Progress Work Orders
        content: >
          {% set orders = state_attr('sensor.maintainx_in_progress_work_orders', 'work_orders') %}

          {% if orders and orders | length > 0 %}

          | # | Title | Priority | Created |

          |---|-------|----------|---------|

          {% for wo in orders[:20] %}

          | {{ wo.id }} | {{ wo.title }} | {% if wo.priority == 'CRITICAL' %}🔴{% elif wo.priority == 'HIGH' %}🟠{% elif wo.priority == 'MEDIUM' %}🟡{% elif wo.priority == 'LOW' %}🟢{% else %}⚪{% endif %} {{ wo.priority }} | {{ wo.created_at[:10] if wo.created_at else 'N/A' }} |

          {% endfor %}

          {% else %}

          No work orders in progress

          {% endif %}

      - type: markdown
        title: 🟠 On Hold Work Orders
        content: >
          {% set orders = state_attr('sensor.maintainx_on_hold_work_orders', 'work_orders') %}

          {% if orders and orders | length > 0 %}

          | # | Title | Priority | Created |

          |---|-------|----------|---------|

          {% for wo in orders[:20] %}

          | {{ wo.id }} | {{ wo.title }} | {% if wo.priority == 'CRITICAL' %}🔴{% elif wo.priority == 'HIGH' %}🟠{% elif wo.priority == 'MEDIUM' %}🟡{% elif wo.priority == 'LOW' %}🟢{% else %}⚪{% endif %} {{ wo.priority }} | {{ wo.created_at[:10] if wo.created_at else 'N/A' }} |

          {% endfor %}

          {% else %}

          No work orders on hold

          {% endif %}

  ##############################################
  # TAB 3 — CREATE JOB
  ##############################################
  - title: Create Job
    path: create-job
    icon: mdi:clipboard-plus
    badges: []
    cards:

      - type: markdown
        content: >
          # ➕ Create New Work Order

          Fill in the details and press **Submit**.

      - type: entities
        title: Work Order Details
        show_header_toggle: false
        entities:
          - entity: input_text.maintainx_wo_title
            name: Title
            icon: mdi:format-title
          - entity: input_text.maintainx_wo_description
            name: Description
            icon: mdi:text
          - entity: input_select.maintainx_wo_priority
            name: Priority
            icon: mdi:alert-circle
          - entity: input_select.maintainx_wo_category
            name: Category
            icon: mdi:tag

      - type: button
        entity: input_button.maintainx_create_work_order
        name: Submit Work Order
        icon: mdi:send
        tap_action:
          action: toggle
        icon_height: 60px
        show_state: false

  ##############################################
  # TAB 4 — QUICK REPORT
  ##############################################
  - title: Quick Report
    path: quick-report
    icon: mdi:lightning-bolt
    badges: []
    cards:

      - type: markdown
        content: >
          # ⚡ Quick Report

          Tap a button to instantly create a work order.

      - type: horizontal-stack
        cards:
          - type: button
            entity: input_button.maintainx_report_printer
            name: Printer
            icon: mdi:printer-alert
            tap_action:
              action: toggle
            icon_height: 50px
            show_state: false
          - type: button
            entity: input_button.maintainx_report_hvac
            name: HVAC
            icon: mdi:hvac
            tap_action:
              action: toggle
            icon_height: 50px
            show_state: false
          - type: button
            entity: input_button.maintainx_report_plumbing
            name: Plumbing
            icon: mdi:water-pump
            tap_action:
              action: toggle
            icon_height: 50px
            show_state: false

      - type: horizontal-stack
        cards:
          - type: button
            entity: input_button.maintainx_report_electrical
            name: Electrical
            icon: mdi:flash-alert
            tap_action:
              action: toggle
            icon_height: 50px
            show_state: false
          - type: button
            entity: input_button.maintainx_report_safety
            name: Safety
            icon: mdi:shield-alert
            tap_action:
              action: toggle
            icon_height: 50px
            show_state: false
          - type: button
            entity: input_button.maintainx_report_general
            name: General
            icon: mdi:wrench
            tap_action:
              action: toggle
            icon_height: 50px
            show_state: false

  ##############################################
  # TAB 5 — ALL JOBS
  ##############################################
  - title: All Jobs
    path: all-jobs
    icon: mdi:clipboard-text-clock
    badges: []
    cards:

      - type: markdown
        title: 📋 Recent Work Orders
        content: >
          {% set orders = state_attr('sensor.maintainx_recent_work_orders', 'recent_work_orders') %}

          {% if orders and orders | length > 0 %}

          | ID | Title | Status | Priority | Created |

          |----|-------|--------|----------|---------|

          {% for wo in orders %}

          | {{ wo.id }} | {{ wo.title[:40] }} | {% if wo.status == 'OPEN' %}🔴{% elif wo.status == 'IN_PROGRESS' %}🟡{% elif wo.status == 'ON_HOLD' %}🟠{% elif wo.status == 'DONE' %}🟢{% else %}⚪{% endif %} {{ wo.status }} | {% if wo.priority == 'CRITICAL' %}🔴{% elif wo.priority == 'HIGH' %}🟠{% elif wo.priority == 'MEDIUM' %}🟡{% elif wo.priority == 'LOW' %}🟢{% else %}⚪{% endif %} {{ wo.priority }} | {{ wo.created_at[:10] if wo.created_at else 'N/A' }} |

          {% endfor %}

          {% else %}

          No work orders found

          {% endif %}

      - type: entities
        title: All Sensors
        entities:
          - sensor.maintainx_total_work_orders
          - sensor.maintainx_open_work_orders
          - sensor.maintainx_in_progress_work_orders
          - sensor.maintainx_on_hold_work_orders
          - sensor.maintainx_completed_work_orders
          - sensor.maintainx_recent_work_orders
'''


async def async_setup_input_helpers(hass: HomeAssistant) -> None:
    """Create input helpers for the dashboard form."""

    # --- input_text helpers ---
    text_store = Store(hass, 1, "input_text")
    text_data = await text_store.async_load() or {"items": []}
    if isinstance(text_data, list):
        text_data = {"items": text_data}
    items = text_data.get("items", [])
    existing_ids = {item["id"] for item in items}

    text_helpers = [
        {
            "id": "maintainx_wo_title",
            "name": "MaintainX WO Title",
            "icon": "mdi:format-title",
            "min": 0,
            "max": 255,
            "initial": "",
            "pattern": "",
            "mode": "text",
        },
        {
            "id": "maintainx_wo_description",
            "name": "MaintainX WO Description",
            "icon": "mdi:text",
            "min": 0,
            "max": 255,
            "initial": "",
            "pattern": "",
            "mode": "text",
        },
    ]

    changed = False
    for helper in text_helpers:
        if helper["id"] not in existing_ids:
            items.append(helper)
            changed = True

    if changed:
        text_data["items"] = items
        await text_store.async_save(text_data)

    # --- input_select helpers ---
    select_store = Store(hass, 1, "input_select")
    select_data = await select_store.async_load() or {"items": []}
    if isinstance(select_data, list):
        select_data = {"items": select_data}
    items = select_data.get("items", [])
    existing_ids = {item["id"] for item in items}

    select_helpers = [
        {
            "id": "maintainx_wo_priority",
            "name": "MaintainX WO Priority",
            "icon": "mdi:alert-circle",
            "options": ["NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"],
            "initial": "NONE",
        },
        {
            "id": "maintainx_wo_category",
            "name": "MaintainX WO Category",
            "icon": "mdi:tag",
            "options": [
                "DEFAULT", "CORRECTIVE", "PREVENTIVE", "DAMAGE",
                "INSPECTION", "SAFETY", "UPGRADE", "PROJECT", "METER_READING",
            ],
            "initial": "DEFAULT",
        },
    ]

    changed = False
    for helper in select_helpers:
        if helper["id"] not in existing_ids:
            items.append(helper)
            changed = True

    if changed:
        select_data["items"] = items
        await select_store.async_save(select_data)

    # --- input_button helpers ---
    button_store = Store(hass, 1, "input_button")
    button_data = await button_store.async_load() or {"items": []}
    if isinstance(button_data, list):
        button_data = {"items": button_data}
    items = button_data.get("items", [])
    existing_ids = {item["id"] for item in items}

    button_helpers = [
        {"id": "maintainx_create_work_order", "name": "MaintainX Create Work Order", "icon": "mdi:send"},
        {"id": "maintainx_report_printer", "name": "MaintainX Report Printer Issue", "icon": "mdi:printer-alert"},
        {"id": "maintainx_report_hvac", "name": "MaintainX Report HVAC Issue", "icon": "mdi:hvac"},
        {"id": "maintainx_report_plumbing", "name": "MaintainX Report Plumbing Issue", "icon": "mdi:water-pump"},
        {"id": "maintainx_report_electrical", "name": "MaintainX Report Electrical Issue", "icon": "mdi:flash-alert"},
        {"id": "maintainx_report_general", "name": "MaintainX Report General Maintenance", "icon": "mdi:wrench"},
        {"id": "maintainx_report_safety", "name": "MaintainX Report Safety Hazard", "icon": "mdi:shield-alert"},
    ]

    changed = False
    for helper in button_helpers:
        if helper["id"] not in existing_ids:
            items.append(helper)
            changed = True

    if changed:
        button_data["items"] = items
        await button_store.async_save(button_data)

    # Reload helper platforms
    for platform in ("input_text", "input_select", "input_button"):
        try:
            await hass.services.async_call(platform, "reload", blocking=True)
        except Exception:
            _LOGGER.debug("Could not reload %s", platform)


async def async_setup_dashboard_automations(hass: HomeAssistant) -> None:
    """Create automations for dashboard buttons."""
    store = Store(hass, 1, "automations")
    existing_data = await store.async_load() or []

    if isinstance(existing_data, dict):
        existing_automations = existing_data.get("data", [])
    else:
        existing_automations = existing_data

    existing_ids = {a.get("id") for a in existing_automations if isinstance(a, dict)}

    automations = _build_automations()

    changed = False
    for automation in automations:
        if automation["id"] not in existing_ids:
            existing_automations.append(automation)
            changed = True

    if changed:
        await store.async_save(existing_automations)
        try:
            await hass.services.async_call("automation", "reload", blocking=True)
        except Exception:
            _LOGGER.debug("Could not reload automations")


def _build_automations() -> list[dict[str, Any]]:
    """Return automation configs."""
    return [
        {
            "id": "maintainx_submit_work_order",
            "alias": "MaintainX: Submit Work Order Form",
            "description": "Creates a MaintainX work order from the dashboard form",
            "trigger": [{"platform": "state", "entity_id": "input_button.maintainx_create_work_order"}],
            "condition": [{"condition": "template", "value_template": "{{ states('input_text.maintainx_wo_title') | length > 0 }}"}],
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
                {"service": "input_text.set_value", "target": {"entity_id": "input_text.maintainx_wo_title"}, "data": {"value": ""}},
                {"service": "input_text.set_value", "target": {"entity_id": "input_text.maintainx_wo_description"}, "data": {"value": ""}},
                {"service": "input_select.select_option", "target": {"entity_id": "input_select.maintainx_wo_priority"}, "data": {"option": "NONE"}},
                {"service": "input_select.select_option", "target": {"entity_id": "input_select.maintainx_wo_category"}, "data": {"option": "DEFAULT"}},
                {"service": "persistent_notification.create", "data": {"title": "MaintainX", "message": "✅ Work order created!"}},
            ],
            "mode": "single",
        },
        _quick_report("maintainx_quick_report_printer", "input_button.maintainx_report_printer", "Printer Issue Reported", "Printer issue reported via HA", "MEDIUM", "CORRECTIVE", "🖨️ Printer issue reported!"),
        _quick_report("maintainx_quick_report_hvac", "input_button.maintainx_report_hvac", "HVAC Issue Reported", "HVAC issue reported via HA", "HIGH", "CORRECTIVE", "❄️ HVAC issue reported!"),
        _quick_report("maintainx_quick_report_plumbing", "input_button.maintainx_report_plumbing", "Plumbing Issue Reported", "Plumbing issue reported via HA", "HIGH", "CORRECTIVE", "🔧 Plumbing issue reported!"),
        _quick_report("maintainx_quick_report_electrical", "input_button.maintainx_report_electrical", "Electrical Issue Reported", "Electrical issue reported via HA", "HIGH", "CORRECTIVE", "⚡ Electrical issue reported!"),
        _quick_report("maintainx_quick_report_safety", "input_button.maintainx_report_safety", "Safety Hazard Reported", "SAFETY HAZARD reported via HA", "CRITICAL", "SAFETY", "🛡️ Safety hazard reported!"),
        _quick_report("maintainx_quick_report_general", "input_button.maintainx_report_general", "General Maintenance Request", "General maintenance via HA", "LOW", "DEFAULT", "🔧 Request submitted!"),
    ]


def _quick_report(auto_id, entity_id, title, desc, priority, category, msg):
    """Build a quick-report automation."""
    return {
        "id": auto_id,
        "alias": f"MaintainX: {title}",
        "trigger": [{"platform": "state", "entity_id": entity_id}],
        "action": [
            {"service": "maintainx.create_work_order", "data": {"title": title, "description": desc + " at {{ now().strftime('%Y-%m-%d %H:%M:%S') }}", "priority": priority, "category": category}},
            {"service": "persistent_notification.create", "data": {"title": "MaintainX", "message": msg}},
        ],
        "mode": "single",
    }
