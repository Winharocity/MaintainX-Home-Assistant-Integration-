"""DataUpdateCoordinator for MaintainX."""
from __future__ import annotations

import asyncio
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
        """Validate the API key."""
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

    async def async_get_work_order(self, work_order_id: int) -> dict[str, Any] | None:
        """Get a specific work order with full details."""
        try:
            async with self._session.get(
                f"{BASE_URL}/workorders/{work_order_id}",
                headers=self._headers,
            ) as response:
                if response.status == 429:
                    _LOGGER.debug("Rate limited fetching WO %s", work_order_id)
                    return None
                if response.status != 200:
                    return None
                data = await response.json()
                if "workOrder" in data:
                    return data["workOrder"]
                return data
        except Exception as err:
            _LOGGER.debug("Error fetching WO %s: %s", work_order_id, err)
            return None

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
            raise UpdateFailed(f"Error updating work order {work_order_id}: {err}") from err

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
            raise UpdateFailed(f"Error adding comment: {err}") from err

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
            _LOGGER.warning("Error fetching assets: %s", err)
            return {"assets": []}

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
            _LOGGER.warning("Error fetching locations: %s", err)
            return {"locations": []}

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
            _LOGGER.warning("Error fetching users: %s", err)
            return {"users": []}


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
        # Cache for detailed work orders so we don't refetch every cycle
        self._detail_cache: dict[int, dict[str, Any]] = {}

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from MaintainX API."""
        try:
            # Step 1: Get all work orders from list endpoint (this is fast, 1-2 API calls)
            all_work_orders = []
            cursor = None

            while True:
                result = await self.client.async_get_work_orders(
                    limit=100, cursor=cursor
                )
                work_orders = result.get("workOrders", [])
                if not work_orders:
                    break
                all_work_orders.extend(work_orders)
                cursor = result.get("nextCursor")
                if not cursor:
                    break

            _LOGGER.debug("Fetched %d work orders from list", len(all_work_orders))

            # Step 2: Fetch details for ONLY a few key work orders (max 3 per cycle)
            # Only fetch ones we haven't cached yet
            open_and_active = [
                wo for wo in all_work_orders
                if wo.get("status") in ("OPEN", "IN_PROGRESS")
            ]

            ids_to_fetch = []
            for wo in open_and_active:
                wo_id = wo.get("id")
                if wo_id and wo_id not in self._detail_cache:
                    ids_to_fetch.append(wo_id)

            # Only fetch 3 new details per update cycle to stay under rate limit
            ids_to_fetch = ids_to_fetch[:3]

            if ids_to_fetch:
                _LOGGER.debug("Fetching details for %d new work orders", len(ids_to_fetch))
                for wo_id in ids_to_fetch:
                    await asyncio.sleep(2)  # 2 second gap between requests
                    detail = await self.client.async_get_work_order(wo_id)
                    if detail and isinstance(detail, dict) and detail.get("id"):
                        self._detail_cache[wo_id] = detail

            # Step 3: Merge — use cached detail if available, otherwise list data
            merged_work_orders = []
            for wo in all_work_orders:
                wo_id = wo.get("id")
                if wo_id in self._detail_cache:
                    merged_work_orders.append(self._detail_cache[wo_id])
                else:
                    merged_work_orders.append(wo)

            self.work_orders = merged_work_orders

            # Clean cache — remove work orders that no longer exist
            current_ids = {wo.get("id") for wo in all_work_orders}
            stale_ids = [k for k in self._detail_cache if k not in current_ids]
            for k in stale_ids:
                del self._detail_cache[k]

            # Step 4: Fetch assets, locations, users (one per cycle to avoid rate limit)
            # Rotate which one we fetch each cycle
            cycle = getattr(self, "_fetch_cycle", 0)

            if cycle == 0:
                try:
                    await asyncio.sleep(2)
                    assets_result = await self.client.async_get_assets()
                    self.assets = assets_result.get("assets", [])
                except Exception:
                    pass
            elif cycle == 1:
                try:
                    await asyncio.sleep(2)
                    locations_result = await self.client.async_get_locations()
                    self.locations = locations_result.get("locations", [])
                except Exception:
                    pass
            elif cycle == 2:
                try:
                    await asyncio.sleep(2)
                    users_result = await self.client.async_get_users()
                    self.users = users_result.get("users", [])
                except Exception:
                    pass

            self._fetch_cycle = (cycle + 1) % 3

            # Step 5: Categorize
            open_orders = [wo for wo in merged_work_orders if wo.get("status") == "OPEN"]
            in_progress_orders = [wo for wo in merged_work_orders if wo.get("status") == "IN_PROGRESS"]
            on_hold_orders = [wo for wo in merged_work_orders if wo.get("status") == "ON_HOLD"]
            done_orders = [wo for wo in merged_work_orders if wo.get("status") == "DONE"]

            _LOGGER.info(
                "MaintainX: %d total (%d open, %d active, %d hold, %d done) | %d cached details",
                len(merged_work_orders),
                len(open_orders),
                len(in_progress_orders),
                len(on_hold_orders),
                len(done_orders),
                len(self._detail_cache),
            )

            return {
                "work_orders": merged_work_orders,
                "open_work_orders": open_orders,
                "in_progress_work_orders": in_progress_orders,
                "on_hold_work_orders": on_hold_orders,
                "done_work_orders": done_orders,
                "total_count": len(merged_work_orders),
                "open_count": len(open_orders),
                "in_progress_count": len(in_progress_orders),
                "on_hold_count": len(on_hold_orders),
                "done_count": len(done_orders),
                "assets": self.assets,
                "locations": self.locations,
                "users": self.users,
            }
        except UpdateFailed:
            raise
        except Exception as err:
            _LOGGER.error("MaintainX update error: %s", err, exc_info=True)
            raise UpdateFailed(f"Error: {err}") from err
