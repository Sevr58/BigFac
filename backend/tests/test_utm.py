from app.services.utm import build_utm_params, append_utm_to_url


def test_build_utm_params_basic():
    params = build_utm_params(
        brand_name="Тест Бренд",
        network="instagram",
        format="reel",
        funnel_stage="tofu",
    )
    assert params["utm_source"] == "instagram"
    assert params["utm_medium"] == "reel"
    assert params["utm_campaign"] == "scf"
    assert params["utm_content"] == "tofu"
    assert len(params["utm_term"]) <= 30


def test_build_utm_params_custom_campaign():
    params = build_utm_params("Brand", "vk", "post", "bofu", campaign="april_promo")
    assert params["utm_campaign"] == "april_promo"


def test_append_utm_to_url_no_existing_params():
    result = append_utm_to_url(
        "https://example.com/page",
        {"utm_source": "vk", "utm_medium": "post"},
    )
    assert "utm_source=vk" in result
    assert "utm_medium=post" in result


def test_append_utm_to_url_preserves_existing_params():
    result = append_utm_to_url(
        "https://example.com/page?ref=email",
        {"utm_source": "telegram"},
    )
    assert "ref=email" in result
    assert "utm_source=telegram" in result


def test_append_utm_to_url_no_url_returns_empty():
    result = append_utm_to_url("", {"utm_source": "vk"})
    assert result == ""
