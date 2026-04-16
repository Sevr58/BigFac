from unittest.mock import patch, MagicMock
from app.services.publishers.telegram import TelegramPublisher


def test_telegram_publish_success():
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "ok": True,
        "result": {"message_id": 42},
    }
    with patch("httpx.post", return_value=mock_resp) as mock_post:
        publisher = TelegramPublisher(bot_token="TEST_TOKEN", chat_id="-100123456")
        result = publisher.publish(
            text="Test post",
            media_keys=[],
            utm_params={"utm_source": "telegram"},
        )
    assert result.success is True
    assert result.network_post_id == "42"
    assert result.error is None
    mock_post.assert_called_once()
    call_kwargs = mock_post.call_args
    assert "sendMessage" in call_kwargs[0][0]


def test_telegram_publish_api_error():
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "ok": False,
        "description": "Bad Request: chat not found",
    }
    with patch("httpx.post", return_value=mock_resp):
        publisher = TelegramPublisher(bot_token="TOKEN", chat_id="bad_id")
        result = publisher.publish("text", [], {})
    assert result.success is False
    assert "chat not found" in result.error


def test_telegram_publish_network_exception():
    with patch("httpx.post", side_effect=Exception("connection refused")):
        publisher = TelegramPublisher(bot_token="TOKEN", chat_id="-100123")
        result = publisher.publish("text", [], {})
    assert result.success is False
    assert "connection refused" in result.error


from app.services.publishers.vk import VKPublisher
from app.services.publishers.instagram import InstagramPublisher


def test_vk_publish_success():
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"response": {"post_id": 99}}
    with patch("httpx.post", return_value=mock_resp):
        publisher = VKPublisher(access_token="VK_TOKEN", owner_id="-12345")
        result = publisher.publish("VK post text", [], {"utm_source": "vk"})
    assert result.success is True
    assert result.network_post_id == "99"


def test_vk_publish_api_error():
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "error": {"error_code": 5, "error_msg": "User authorization failed"}
    }
    with patch("httpx.post", return_value=mock_resp):
        publisher = VKPublisher(access_token="BAD", owner_id="-12345")
        result = publisher.publish("text", [], {})
    assert result.success is False
    assert "authorization failed" in result.error


def test_instagram_publish_success():
    mock_create = MagicMock()
    mock_create.raise_for_status = MagicMock()
    mock_create.json.return_value = {"id": "container_123"}

    mock_publish = MagicMock()
    mock_publish.raise_for_status = MagicMock()
    mock_publish.json.return_value = {"id": "post_456"}

    with patch("httpx.post", side_effect=[mock_create, mock_publish]):
        publisher = InstagramPublisher(
            page_access_token="PAGE_TOKEN",
            instagram_account_id="IG_ACCOUNT_ID",
        )
        result = publisher.publish("Caption text", [], {"utm_source": "instagram"})
    assert result.success is True
    assert result.network_post_id == "post_456"


def test_instagram_publish_no_container_id():
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {}  # no "id" key
    with patch("httpx.post", return_value=mock_resp):
        publisher = InstagramPublisher("TOKEN", "IG_ID")
        result = publisher.publish("text", [], {})
    assert result.success is False
    assert result.error is not None
