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
        self._api_key = api_key
        self._session = session
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    async def async_validate_api_key(self) -> bool:
        try:
            async with self._session.get(
                f"{BASE_URL}/workorders?limit=1",
                headers=self._headers,
            ) as response:
                return response.status == 200
        except aiohttp.ClientError:
            return False

    async def async_get_work_orders(
        self, status: str | None = None, limit: int = 100, cursor: str | None = None
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"limit": limit}
        if status:
            params["status"] = status
        if cursor:
            params["cursor"] = cursor
        try:
            async with self._session.get(
                f"{BASE_URL}/workorders", headers=self._headers, params=params
            ) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Error fetching work orders: {err}") from err

    async def async_get_work_order(self, work_order_id: int) -> dict[str, Any] | None:
        try:
            async with self._session.get(
                f"{BASE_URL}/workorders/{work_order_id}", headers=self._headers
            ) as response:
                if response.status != 200:
                    return None
                data = await response.json()
                return data.get("workOrder", data)
        except Exception:
            return None

    async def async_create_work_order(self, data: dict[str, Any]) -> dict[str, Any]:
        try:
            async with self._session.post(
                f"{BASE_URL}/workorders", headers=self._headers, json=data
            ) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Error creating work order: {err}") from err

    async def async_update_work_order(self, work_order_id: int, data: dict[str, Any]) -> dict[str, Any]:
        try:
            async with self._session.patch(
                f"{BASE_URL}/workorders/{work_order_id}", headers=self._headers, json=data
            ) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Error updating work order: {err}") from err

    async def async_add_comment(self, work_order_id: int, comment: str) -> dict[str, Any]:
        try:
            async with self._session.post(
                f"{BASE_URL}/workorders/{work_order_id}/comments",
                headers=self._headers, json={"content": comment}
            ) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Error adding comment: {err}") from err

    async def async_get_assets(self, limit: int = 100) -> dict[str, Any]:
        try:
            async with self._session.get(
                f"{BASE_URL}/assets", headers=self._headers, params={"limit": limit}
            ) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError:
            return {"assets": []}

    async def async_get_locations(self, limit: int = 100) -> dict[str, Any]:
        try:
            async with self._session.get(
                f"{BASE_URL}/locations", headers=self._headers, params={"limit": limit}
            ) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError:
            return {"locations": []}

    async def async_get_users(self, limit: int = 100) -> dict[str, Any]:
        try:
            async with self._session.get(
                f"{BASE_URL}/users", headers=self._headers, params={"limit": limit}
            ) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError:
            return {"users": []}


class MaintainXCoordinator(DataUpdateCoordinator):
    """Coordinator for MaintainX data."""

    def __init__(self, hass: HomeAssistant, client: MaintainXApiClient) -> None:
        super().__init__(
            hass, _LOGGER, name=DOMAIN, update_interval=DEFAULT_SCAN_INTERVAL
        )
        self.client = client
        self.work_orders: list[dict[str, Any]] = []
        self.assets: list[dict[str, Any]] = []
        self.locations: list[dict[str, Any]] = []
        self.users: list[dict[str, Any]] = []
        self._detail_cache: dict[int, dict[str, Any]] = {}
        self._fetch_cycle: int = 0
        self._dropdowns_updated: bool = False

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            # Step 1: Get all work orders from list endpoint
            all_work_orders = []
            cursor = None
            while True:
                result = await self.client.async_get_work_orders(limit=100, cursor=cursor)
                wos = result.get("workOrders", [])
                if not wos:
                    break
                all_work_orders.extend(wos)
                cursor = result.get("nextCursor")
                if not cursor:
                    break

            _LOGGER.debug("Fetched %d work orders from list", len(all_work_orders))

            # Step 2: Fetch details for max 3 uncached active work orders
            open_active = [
                wo for wo in all_work_orders
                if wo.get("status") in ("OPEN", "IN_PROGRESS")
            ]
            ids_to_fetch = [
                wo.get("id") for wo in open_active
                if wo.get("id") and wo.get("id") not in self._detail_cache
            ][:3]

            for wo_id in ids_to_fetch:
                await asyncio.sleep(2)
                detail = await self.client.async_get_work_order(wo_id)
                if detail and isinstance(detail, dict) and detail.get("id"):
                    self._detail_cache[wo_id] = detail

            # Step 3: Merge
            merged = []
            for wo in all_work_orders:
                wo_id = wo.get("id")
                if wo_id in self._detail_cache:
                    merged.append(self._detail_cache[wo_id])
                else:
                    merged.append(wo)

            self.work_orders = merged

            # Clean stale cache
            current_ids = {wo.get("id") for wo in all_work_orders}
            for k in [k for k in self._detail_cache if k not in current_ids]:
                del self._detail_cache[k]

            # Step 4: Rotate fetching assets/locations/users
            if self._fetch_cycle == 0:
                try:
                    await asyncio.sleep(2)
                    r = await self.client.async_get_assets()
                    self.assets = r.get("assets", [])
                except Exception:
                    pass
            elif self._fetch_cycle == 1:
                try:
                    await asyncio.sleep(2)
                    r = await self.client.async_get_locations()
                    self.locations = r.get("locations", [])
                except Exception:
                    pass
            elif self._fetch_cycle == 2:
                try:
                    await asyncio.sleep(2)
                    r = await self.client.async_get_users()
                    self.users = r.get("users", [])
                except Exception:
                    pass

            self._fetch_cycle = (self._fetch_cycle + 1) % 3

            # Step 5: Update dropdown selects with real data
            await self._update_dropdowns()

            # Step 6: Categorize
            open_orders = [wo for wo in merged if wo.get("status") == "OPEN"]
            in_progress = [wo for wo in merged if wo.get("status") == "IN_PROGRESS"]
            on_hold = [wo for wo in merged if wo.get("status") == "ON_HOLD"]
            done = [wo for wo in merged if wo.get("status") == "DONE"]

            _LOGGER.info(
                "MaintainX: %d total (%d open, %d active, %d hold, %d done)",
                len(merged), len(open_orders), len(in_progress), len(on_hold), len(done),
            )

            return {
                "work_orders": merged,
                "open_work_orders": open_orders,
                "in_progress_work_orders": in_progress,
                "on_hold_work_orders": on_hold,
                "done_work_orders": done,
                "total_count": len(merged),
                "open_count": len(open_orders),
                "in_progress_count": len(in_progress),
                "on_hold_count": len(on_hold),
                "done_count": len(done),
                "assets": self.assets,
                "locations": self.locations,
                "users": self.users,
            }
        except UpdateFailed:
            raise
        except Exception as err:
            _LOGGER.error("MaintainX update error: %s", err, exc_info=True)
            raise UpdateFailed(f"Error: {err}") from err

    async def _update_dropdowns(self) -> None:
        """Update the input_select dropdowns with real assets/locations/users."""
        try:
            # Update assignee dropdown
            if self.users:
                user_options = ["None"]
                for u in self.users:
                    name = u.get("displayName") or u.get("firstName", "") + " " + u.get("lastName", "")
                    name = name.strip()
                    uid = u.get("id")
                    if name and uid:
                        user_options.append(f"{name} (ID:{uid})")

                if len(user_options) > 1:
                    try:
                        await self.hass.services.async_call(
                            "input_select", "set_options",
                            {"entity_id": "input_select.maintainx_wo_assignee", "options": user_options},
                            blocking=True,
                        )
                    except Exception:
                        pass

            # Update asset dropdown
            if self.assets:
                asset_options = ["None"]
                for a in self.assets:
                    name = a.get("name", "Unknown")
                    aid = a.get("id")
                    if name and aid:
                        asset_options.append(f"{name} (ID:{aid})")

                if len(asset_options) > 1:
                    try:
                        await self.hass.services.async_call(
                            "input_select", "set_options",
                            {"entity_id": "input_select.maintainx_wo_asset", "options": asset_options},
                            blocking=True,
                        )
                    except Exception:
                        pass

            # Update location dropdown
            if self.locations:
                loc_options = ["None"]
                for loc in self.locations:
                    name = loc.get("name", "Unknown")
                    lid = loc.get("id")
                    if name and lid:
                        loc_options.append(f"{name} (ID:{lid})")

                if len(loc_options) > 1:
                    try:
                        await self.hass.services.async_call(
                            "input_select", "set_options",
                            {"entity_id": "input_select.maintainx_wo_location", "options": loc_options},
                            blocking=True,
                        )
                    except Exception:
                        pass

        except Exception as err:
            _LOGGER.debug("Could not update dropdowns: %s", err)
