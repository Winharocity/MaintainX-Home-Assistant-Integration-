"""Constants for the MaintainX integration."""
from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "maintainx"

CONF_API_KEY: Final = "api_key"

BASE_URL: Final = "https://api.getmaintainx.com/v1"

DEFAULT_SCAN_INTERVAL: Final = timedelta(minutes=5)

DASHBOARD_URL: Final = "maintainx-dashboard"
DASHBOARD_TITLE: Final = "MaintainX"
DASHBOARD_ICON: Final = "mdi:wrench-clock"

# Work Order Statuses
STATUS_OPEN: Final = "OPEN"
STATUS_IN_PROGRESS: Final = "IN_PROGRESS"
STATUS_ON_HOLD: Final = "ON_HOLD"
STATUS_DONE: Final = "DONE"

# Work Order Priorities
PRIORITY_NONE: Final = "NONE"
PRIORITY_LOW: Final = "LOW"
PRIORITY_MEDIUM: Final = "MEDIUM"
PRIORITY_HIGH: Final = "HIGH"
PRIORITY_CRITICAL: Final = "CRITICAL"

# Work Order Categories
CATEGORY_DAMAGE: Final = "DAMAGE"
CATEGORY_INSPECTION: Final = "INSPECTION"
CATEGORY_METER_READING: Final = "METER_READING"
CATEGORY_PREVENTIVE: Final = "PREVENTIVE"
CATEGORY_PROJECT: Final = "PROJECT"
CATEGORY_SAFETY: Final = "SAFETY"
CATEGORY_UPGRADE: Final = "UPGRADE"
CATEGORY_CORRECTIVE: Final = "CORRECTIVE"
CATEGORY_DEFAULT: Final = "DEFAULT"

# Service names
SERVICE_CREATE_WORK_ORDER: Final = "create_work_order"
SERVICE_UPDATE_WORK_ORDER: Final = "update_work_order"
SERVICE_COMPLETE_WORK_ORDER: Final = "complete_work_order"
SERVICE_ADD_COMMENT: Final = "add_comment"
SERVICE_SET_STATUS: Final = "set_status"

# Attributes
ATTR_WORK_ORDER_ID: Final = "work_order_id"
ATTR_TITLE: Final = "title"
ATTR_DESCRIPTION: Final = "description"
ATTR_PRIORITY: Final = "priority"
ATTR_CATEGORY: Final = "category"
ATTR_STATUS: Final = "status"
ATTR_ASSIGNEE_ID: Final = "assignee_id"
ATTR_ASSET_ID: Final = "asset_id"
ATTR_LOCATION_ID: Final = "location_id"
ATTR_COMMENT: Final = "comment"
