"""prepare_https_url_with_doh 行为（不发起外网请求）。"""

from __future__ import annotations


def test_prepare_https_doh_disabled_returns_same_url(monkeypatch: object) -> None:
    monkeypatch.setattr("app.services.ai_connect.settings.ai_doh_fallback", False)
    from app.services.ai_connect import prepare_https_url_with_doh

    url = "https://api.example.com/v1/chat/completions"
    u, ext, eh = prepare_https_url_with_doh(url)
    assert u == url
    assert ext == {}
    assert eh == {}


def test_prepare_https_doh_rewrites_when_resolve_returns_ip(monkeypatch: object) -> None:
    monkeypatch.setattr("app.services.ai_connect.settings.ai_doh_fallback", True)
    monkeypatch.setattr("app.services.ai_connect.doh_resolve_ipv4", lambda _h: "203.0.113.10")

    from app.services.ai_connect import prepare_https_url_with_doh

    u, ext, eh = prepare_https_url_with_doh("https://api.example.com/v1/chat/completions")
    assert u.startswith("https://203.0.113.10/")
    assert ext == {"sni_hostname": "api.example.com"}
    assert eh == {"Host": "api.example.com"}
