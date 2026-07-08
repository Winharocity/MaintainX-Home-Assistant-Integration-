# MaintainX Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

A full-featured Home Assistant integration for [MaintainX](https://www.getmaintainx.com/) that allows you to view all work orders (jobs), create new ones, and build automations around maintenance tasks.

## Features

- **View all work orders** with status, priority, category, assignees, and more
- **Count sensors** for Open, In Progress, On Hold, and Completed work orders
- **Individual work order sensors** for active jobs
- **Create work orders** via service calls (perfect for automations!)
- **Update work orders** — change status, priority, assignee, etc.
- **Complete work orders** with a single service call
- **Add comments** to existing work orders
- **Full automation support** — trigger MaintainX jobs from any HA event

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click the three dots menu → **Custom repositories**
3. Add this repository URL and select **Integration** as the category
4. Click **Install**
5. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/maintainx` folder to your Home Assistant `config/custom_components/` directory
2. Restart Home Assistant

## Configuration

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **MaintainX**
3. Enter your MaintainX API key
   - Find your API key in MaintainX: **Settings → API Keys**
4. Click **Submit**

## Sensors

| Sensor | Description |
|--------|-------------|
| `sensor.maintainx_total_work_orders` | Total number of work orders |
| `sensor.maintainx_open_work_orders` | Number of open work orders |
| `sensor.maintainx_in_progress_work_orders` | Number of in-progress work orders |
| `sensor.maintainx_on_hold_work_orders` | Number of on-hold work orders |
| `sensor.maintainx_completed_work_orders` | Number of completed work orders |
| `sensor.maintainx_recent_work_orders` | Most recent work order with list in attributes |
| `sensor.maintainx_wo_<id>` | Individual sensors for each active work order |

Each sensor includes detailed attributes with work order information.

## Services

### `maintainx.create_work_order`

Create a new work order in MaintainX.

| Field | Required | Description |
|-------|----------|-------------|
| `title` | ✅ | Title of the work order |
| `description` | ❌ | Detailed description |
| `priority` | ❌ | NONE, LOW, MEDIUM, HIGH, CRITICAL |
| `category` | ❌ | DAMAGE, INSPECTION, PREVENTIVE, CORRECTIVE, etc. |
| `assignee_id` | ❌ | MaintainX user ID |
| `asset_id` | ❌ | MaintainX asset ID |
| `location_id` | ❌ | MaintainX location ID |

### `maintainx.update_work_order`

Update an existing work order.

| Field | Required | Description |
|-------|----------|-------------|
| `work_order_id` | ✅ | ID of the work order |
| `title` | ❌ | New title |
| `description` | ❌ | New description |
| `priority` | ❌ | New priority |
| `status` | ❌ | OPEN, IN_PROGRESS, ON_HOLD, DONE |
| `category` | ❌ | New category |
| `assignee_id` | ❌ | New assignee |
| `asset_id` | ❌ | New asset |
| `location_id` | ❌ | New location |

### `maintainx.complete_work_order`

Mark a work order as complete.

| Field | Required | Description |
|-------|----------|-------------|
| `work_order_id` | ✅ | ID of the work order to complete |

### `maintainx.add_comment`

Add a comment to a work order.

| Field | Required | Description |
|-------|----------|-------------|
| `work_order_id` | ✅ | ID of the work order |
| `comment` | ✅ | Comment text |

## Automation Examples

### Example 1: Printer Ink Low — Create a MaintainX Job

```yaml
automation:
  - alias: "Printer Ink Low - Create MaintainX Work Order"
    description: "When the printer reports low ink, automatically create a maintenance job"
    trigger:
      - platform: state
        entity_id: sensor.printer_ink_level
        below: 10
    condition:
      - condition: template
        value_template: "{{ trigger.from_state.state | int > 10 }}"
    action:
      - service: maintainx.create_work_order
        data:
          title: "Printer Ink Replacement Needed"
          description: >
            The printer ink level has dropped below 10%.
            Current level: {{ states('sensor.printer_ink_level') }}%.
            Printer: {{ state_attr('sensor.printer_ink_level', 'friendly_name') }}
          priority: "HIGH"
          category: "CORRECTIVE"
      - service: notify.notify
        data:
          message: "MaintainX work order created: Printer ink is low ({{ states('sensor.printer_ink_level') }}%)"
