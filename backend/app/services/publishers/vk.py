import httpx
from app.services.publishers.base import BasePublisher, PublishResult


class VKPublisher(BasePublisher):
    _API = "https://api.vk.com/method"
    _VER = "5.199"

    def __init__(self, access_token: str, owner_id: str):
        self.access_token = access_token
        self.owner_id = owner_id  # negative for groups, e.g. "-123456"

    def publish(self, text: str, media_keys: list[str], utm_params: dict) -> PublishResult:
        try:
            resp = httpx.post(
                f"{self._API}/wall.post",
                params={
                    "owner_id": self.owner_id,
                    "message": text,
                    "access_token": self.access_token,
                    "v": self._VER,
                },
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            if "response" in data:
                return PublishResult(
                    success=True,
                    network_post_id=str(data["response"]["post_id"]),
                )
            error = data.get("error", {}).get("error_msg", "Unknown VK error")
            return PublishResult(success=False, error=error)
        except Exception as e:
            return PublishResult(success=False, error=str(e))
