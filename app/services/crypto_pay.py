from __future__ import annotations

from dataclasses import dataclass

import aiohttp


@dataclass(slots=True)
class CryptoInvoice:
    invoice_id: str
    pay_url: str


class CryptoPayClient:
    def __init__(self, token: str | None, api_url: str) -> None:
        self.token = token
        self.api_url = api_url.rstrip("/")

    @property
    def enabled(self) -> bool:
        return bool(self.token)

    async def create_invoice(self, asset: str, amount: float, description: str) -> CryptoInvoice | None:
        if not self.token:
            return None
        payload = {
            "asset": asset,
            "amount": f"{amount:.2f}",
            "description": description[:1024],
        }
        data = await self._request("createInvoice", payload)
        result = data.get("result") or {}
        invoice_id = str(result.get("invoice_id") or "")
        pay_url = str(result.get("pay_url") or result.get("bot_invoice_url") or "")
        if not invoice_id or not pay_url:
            return None
        return CryptoInvoice(invoice_id=invoice_id, pay_url=pay_url)

    async def is_invoice_paid(self, invoice_id: str) -> bool:
        if not self.token:
            return False
        data = await self._request("getInvoices", {"invoice_ids": invoice_id})
        result = data.get("result") or {}
        items = result.get("items") or []
        if not items:
            return False
        return str(items[0].get("status")) == "paid"

    async def _request(self, method: str, payload: dict[str, object]) -> dict[str, object]:
        headers = {"Crypto-Pay-API-Token": self.token or ""}
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.post(f"{self.api_url}/{method}", json=payload, timeout=20) as response:
                data = await response.json(content_type=None)
                if not data.get("ok"):
                    raise RuntimeError(str(data))
                return data
