import httpx
from app.services.publishers.base import BasePublisher, PublishResult

_GRAPH = "https://graph.facebook.com/v19.0"


class InstagramPublisher(BasePublisher):
    def __init__(self, page_access_token: str, instagram_account_id: str):
        self.token = page_access_token
        self.ig_id = instagram_account_id

    def publish(self, text: str, media_keys: list[str], utm_params: dict) -> PublishResult:
        """Two-step Meta Graph API publish: create container, then publish it."""
        try:
            create_resp = httpx.post(
                f"{_GRAPH}/{self.ig_id}/media",
                params={
                    "caption": text,
                    "access_token": self.token,
                    "media_type": "IMAGE",
                },
                timeout=30,
            )
            create_resp.raise_for_status()
            container_id = create_resp.json().get("id")
            if not container_id:
                return PublishResult(success=False, error="Instagram returned no container id")

            pub_resp = httpx.post(
                f"{_GRAPH}/{self.ig_id}/media_publish",
                params={
                    "creation_id": container_id,
                    "access_token": self.token,
                },
                timeout=30,
            )
            pub_resp.raise_for_status()
            post_id = pub_resp.json().get("id")
            return PublishResult(success=True, network_post_id=str(post_id))
        except Exception as e:
            return PublishResult(success=False, error=str(e))
