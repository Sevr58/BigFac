from urllib.parse import urlencode, urlparse, urlunparse, parse_qs


def build_utm_params(
    brand_name: str,
    network: str,
    format: str,
    funnel_stage: str,
    campaign: str = "scf",
) -> dict:
    brand_slug = brand_name.lower()
    brand_slug = "".join(c if c.isalnum() else "_" for c in brand_slug)[:30]
    return {
        "utm_source": network.lower(),
        "utm_medium": format.lower().replace(" ", "_"),
        "utm_campaign": campaign,
        "utm_content": funnel_stage.lower(),
        "utm_term": brand_slug,
    }


def append_utm_to_url(url: str, utm_params: dict) -> str:
    if not url:
        return ""
    parsed = urlparse(url)
    existing = parse_qs(parsed.query)
    existing.update({k: [v] for k, v in utm_params.items()})
    flat = {k: v[0] for k, v in existing.items()}
    new_query = urlencode(flat)
    return urlunparse(parsed._replace(query=new_query))
