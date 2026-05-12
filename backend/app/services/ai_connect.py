"""
当系统 getaddrinfo 失败时，为 API 主机名解析 IPv4：

1) DNS-over-HTTPS（直连解析商字面 IP，application/dns-json）
2) 若仍失败：DNS over TCP/53（dnspython，解析器为字面 IP，不依赖本机 UDP DNS）

再以「连 IP + TLS SNI 仍为原主机名」访问 HTTPS（httpcore extensions["sni_hostname"]）。
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)


def _doh_opener() -> urllib.request.OpenerDirector:
    if settings.ai_http_trust_env:
        return urllib.request.build_opener()
    return urllib.request.build_opener(urllib.request.ProxyHandler({}))


def _doh_query_json(url: str, *, timeout: float = 4.0) -> dict[str, Any] | None:
    req = urllib.request.Request(
        url,
        headers={
            "accept": "application/dns-json",
            "user-agent": "Interview-Collector/1",
        },
    )
    try:
        with _doh_opener().open(req, timeout=timeout) as resp:
            raw = resp.read()
        return json.loads(raw.decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError, ValueError) as exc:
        logger.info("DoH query failed url=%s err=%s", url[:96], exc)
        return None


def _answers_from_doh(data: dict[str, Any]) -> list[dict[str, Any]]:
    ans = data.get("Answer")
    return ans if isinstance(ans, list) else []


def _dns_tcp_resolve_a(hostname: str) -> str | None:
    """经 TCP/53 向多个公共解析器（字面 IP）查询 A 记录，绕过本机失效的 UDP/DNS。"""
    try:
        import dns.exception
        import dns.rdatatype
        import dns.resolver
    except ImportError:
        logger.warning("dnspython 未安装，无法使用 DNS/TCP 回退；请 pip install -r requirements.txt")
        return None

    nameservers = (
        "223.5.5.5",
        "223.6.6.6",
        "114.114.114.114",
        "119.29.29.29",
        "180.76.76.76",
        "8.8.8.8",
    )
    for ns in nameservers:
        try:
            resolver = dns.resolver.Resolver(configure=False)
            resolver.nameservers = [ns]
            resolver.port = 53
            resolver.timeout = 2.5
            resolver.lifetime = 5.0
            answer = resolver.resolve(hostname, "A", tcp=True)
            for rr in answer:
                if rr.rdtype == dns.rdatatype.A:
                    ip = rr.to_text()
                    if ip:
                        logger.info(
                            "DNS/TCP resolved hostname=%s -> %s via ns=%s",
                            hostname,
                            ip,
                            ns,
                        )
                        return ip
        except (dns.exception.DNSException, OSError, TimeoutError, ValueError) as exc:
            logger.info("DNS/TCP query failed ns=%s host=%s err=%s", ns, hostname, exc)
            continue
        except Exception as exc:  # noqa: BLE001 — 回退路径需吞掉第三方库未声明异常
            logger.info("DNS/TCP query failed ns=%s host=%s err=%s", ns, hostname, exc)
            continue
    return None


def doh_resolve_ipv4(hostname: str) -> str | None:
    """
    先 DoH（Cloudflare / Google / Quad9 等字面 IP），再 DNS/TCP。
    对外仍沿用函数名 doh_resolve_ipv4，供测试 monkeypatch。
    """
    enc = urllib.parse.quote(hostname, safe="")
    # 与 Cloudflare 兼容的 application/dns-json GET（勿使用 223.5.5.5/dns-query，阿里公共解析非此 JSON 形态）
    endpoints = (
        f"https://1.0.0.1/dns-query?name={enc}&type=A",
        f"https://1.1.1.1/dns-query?name={enc}&type=A",
        f"https://9.9.9.9/dns-query?name={enc}&type=A",
        f"https://149.112.112.112/dns-query?name={enc}&type=A",
        f"https://8.8.8.8/resolve?name={enc}&type=A",
    )
    for ep in endpoints:
        data = _doh_query_json(ep, timeout=4.0)
        if not data:
            continue
        for a in _answers_from_doh(data):
            if a.get("type") == 1:
                ip = a.get("data")
                if isinstance(ip, str) and ip:
                    logger.info(
                        "DoH resolved hostname=%s -> %s (endpoint=%s)",
                        hostname,
                        ip,
                        urllib.parse.urlparse(ep).hostname or "?",
                    )
                    return ip

    return _dns_tcp_resolve_a(hostname)


def prepare_https_url_with_doh(url: str) -> tuple[str, dict[str, Any], dict[str, str]]:
    """
    若开启 AI_DOH_FALLBACK 且为 https，则尝试解析 A 记录并改写 URL 为连 IP；
    返回 (新 url, httpx extensions, 需合并进请求头的额外头)。
    """
    if not settings.ai_doh_fallback:
        return url, {}, {}
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        return url, {}, {}
    ip = doh_resolve_ipv4(parsed.hostname)
    if not ip:
        return url, {}, {}
    port = parsed.port
    if port and port != 443:
        netloc = f"{ip}:{port}"
    else:
        netloc = ip
    replaced = parsed._replace(netloc=netloc)
    new_url = urllib.parse.urlunparse(replaced)
    extensions: dict[str, Any] = {"sni_hostname": parsed.hostname}
    extra_headers = {"Host": parsed.hostname}
    return new_url, extensions, extra_headers
