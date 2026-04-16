import httpx
from app.services.publishers.base import BasePublisher, PublishResult


class TelegramPublisher(BasePublisher):
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self._base = f"https://api.telegram.org/bot{bot_token}"

    def publish(self, text: str, media_keys: list[str], utm_params: dict) -> PublishResult:
        try:
            resp = httpx.post(
                f"{self._base}/sendMessage",
                json={"chat_id": self.chat_id, "text": text, "parse_mode": "HTML"},
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("ok"):
                return PublishResult(
                    success=True,
                    network_post_id=str(data["result"]["message_id"]),
                )
            return PublishResult(success=False, error=data.get("description", "Unknown error"))
        except Exception as e:
            return PublishResult(success=False, error=str(e))
