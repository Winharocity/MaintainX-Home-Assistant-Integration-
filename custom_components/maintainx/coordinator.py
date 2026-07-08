"""DataUpdateCoordinator for MaintainX."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import BASE_URL, DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class MaintainXApiClient:
    """API client for MaintainX."""

    def __init__(self, api_key: str, session: aiohttp.ClientSession) -> None:
        """Initialize the API client."""
        self._api_key = api_key
        self._session = session
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    async def async_validate_api_key(self) -> bool:
        """Validate the API key by making a test request."""
        try:
            async with self._session.get(
                f"{BASE_URL}/workorders?limit=1",
                headers=self._headers,
            ) as response:
                return response.status == 200
        except aiohttp.ClientError:
            return False

    async def async_get_work_orders(
        self,
        status: str | None = None,
        limit: int = 100,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        """Get work orders from MaintainX."""
        params: dict[str, Any] = {"limit": limit}
        if status:
            params["status"] = status
        if cursor:
            params["cursor"] = cursor

        try:
            async with self._session.get(
                f"{BASE_URL}/workorders",
                headers=self._headers,
                params=params,
            ) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Error fetching work orders: {err}") from err

    async def async_get_work_order(self, work_order_id: int) -> dict[str, Any]:
        """Get a specific work order."""
        try:
            async with self._session.get(
                f"{BASE_URL}/workorders/{work_order_id}",
                headers=self._headers,
            ) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as err:
            raise UpdateFailed(
                f"Error fetching work order {work_order_id}: {err}"
            ) from err

    async def async_create_work_order(self, data: dict[str, Any]) -> dict[str, Any]:
        """Create a new work order."""
        try:
            async with self._session.post(
                f"{BASE_URL}/workorders",
                headers=self._headers,
                json=data,
            ) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Error creating work order: {err}") from err

    async def async_update_work_order(
        self, work_order_id: int, data: dict[str, Any]
    ) -> dict[str, Any]:
        """Update an existing work order."""
        try:
            async with self._session.patch(
                f"{BASE_URL}/workorders/{work_order_id}",
                headers=self._headers,
                json=data,
            ) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as err:
            raise UpdateFailed(
                f"Error updating work order {work_order_id}: {err}"
            ) from err

    async def async_add_comment(
        self, work_order_id: int, comment: str
    ) -> dict[str, Any]:
        """Add a comment to a work order."""
        try:
            async with self._session.post(
                f"{BASE_URL}/workorders/{work_order_id}/comments",
                headers=self._headers,
                json={"content": comment},
            ) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as err:
            raise UpdateFailed(
                f"Error adding comment to work order {work_order_id}: {err}"
            ) from err

    async def async_get_assets(self, limit: int = 100) -> dict[str, Any]:
        """Get assets from MaintainX."""
        try:
            async with self._session.get(
                f"{BASE_URL}/assets",
                headers=self._headers,
                params={"limit": limit},
            ) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Error fetching assets: {err}") from err

    async def async_get_locations(self, limit: int = 100) -> dict[str, Any]:
        """Get locations from MaintainX."""
        try:
            async with self._session.get(
                f"{BASE_URL}/locations",
                headers=self._headers,
                params={"limit": limit},
            ) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Error fetching locations: {err}") from err

    async def async_get_users(self, limit: int = 100) -> dict[str, Any]:
        """Get users from MaintainX."""
        try:
            async with self._session.get(
                f"{BASE_URL}/users",
                headers=self._headers,
                params={"limit": limit},
            ) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Error fetching users: {err}") from err


class MaintainXCoordinator(DataUpdateCoordinator):
    """Coordinator for MaintainX data."""

    def __init__(self, hass: HomeAssistant, client: MaintainXApiClient) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=DEFAULT_SCAN_INTERVAL,
        )
        self.client = client
        self.work_orders: list[dict[str, Any]] = []
        self.assets: list[dict[str, Any]] = []
        self.locations: list[dict[str, Any]] = []
        self.users: list[dict[str, Any]] = []

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from MaintainX API."""
        try:
            # Fetch all work orders (paginate through all)
            all_work_orders = []
            cursor = None
            while True:
                result = await self.client.async_get_work_orders(
                    limit=100, cursor=cursor
                )
                work_orders = result.get("workOrders", [])
                all_work_orders.extend(work_orders)
                cursor = result.get("nextCursor")
                if not cursor:
                    break

            self.work_orders = all_work_orders

            # Fetch assets
            assets_result = await self.client.async_get_assets()
            self.assets = assets_result.get("assets", [])

            # Fetch locations
            locations_result = await self.client.async_get_locations()
            self.locations = locations_result.get("locations", [])

            # Fetch users
            users_result = await self.client.async_get_users()
            self.users = users_result.get("users", [])

            # Categorize work orders
            open_orders = [
                wo for wo in all_work_orders if wo.get("status") == "OPEN"
            ]
            in_progress_orders = [
                wo for wo in all_work_orders if wo.get("status") == "IN_PROGRESS"
            ]
            on_hold_orders = [
                wo for wo in all_work_orders if wo.get("status") == "ON_HOLD"
            ]
            done_orders = [
                wo for wo in all_work_orders if wo.get("status") == "DONE"
            ]

            return {
                "work_orders": all_work_orders,
                "open_work_orders": open_orders,
                "in_progress_work_orders": in_progress_orders,
                "on_hold_work_orders": on_hold_orders,
                "done_work_orders": done_orders,
                "total_count": len(all_work_orders),
                "open_count": len(open_orders),
                "in_progress_count": len(in_progress_orders),
                "on_hold_count": len(on_hold_orders),
                "done_count": len(done_orders),
                "assets": self.assets,
                "locations": self.locations,
                "users": self.users,
            }
        except Exception as err:
            raise UpdateFailed(f"Error communicating with MaintainX API: {err}") from err
