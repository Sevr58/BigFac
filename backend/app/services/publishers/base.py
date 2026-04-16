from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class PublishResult:
    success: bool
    network_post_id: Optional[str] = None
    error: Optional[str] = None


class BasePublisher(ABC):
    @abstractmethod
    def publish(
        self,
        text: str,
        media_keys: list[str],
        utm_params: dict,
    ) -> PublishResult:
        """Publish content to the social network. Returns PublishResult."""
        ...
