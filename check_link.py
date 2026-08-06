import httpx
from dataclasses import dataclass
from constants import request_timeout_seconds, max_redirect_hops, user_agent

headers = {"User-Agent": user_agent}

# plenty of servers reject HEAD outright rather than answering it, so these
# codes mean "ask again with GET", not "the link is dead"
head_unsupported_codes = frozenset({403, 405, 501})


@dataclass
class LinkCheckResult:
    status_code: int | None
    status: str
    redirect_chain: list
    error_message: str | None
    final_url: str | None = None


async def check_link(client, url):
    chain = []
    current = url

    for hop in range(max_redirect_hops):
        try:
            res = await client.head(
                current,
                timeout=request_timeout_seconds,
                follow_redirects=False,
                headers=headers,
            )
        except Exception as exc:
            # a server that won't talk to HEAD at all still deserves one GET
            if hop == 0:
                fallback = await check_with_get(client, current, chain)
                if fallback is not None:
                    return fallback
            if isinstance(exc, httpx.TimeoutException):
                return LinkCheckResult(None, "timeout", chain, "timed out")
            return LinkCheckResult(None, "broken", chain, str(exc))

        if res.status_code in head_unsupported_codes:
            fallback = await check_with_get(client, current, chain)
            if fallback is not None:
                return fallback
            return LinkCheckResult(res.status_code, "broken", chain, None)

        if res.status_code >= 400:
            return LinkCheckResult(res.status_code, "broken", chain, None)

        if res.status_code < 300:
            status = "redirect" if chain else "ok"
            return LinkCheckResult(res.status_code, status, chain, None, current)

        location = res.headers.get("location")
        if not location:
            return LinkCheckResult(res.status_code, "broken", chain, "redirect w/ no location")

        chain.append(current)
        current = str(httpx.URL(current).join(location))
        if current in chain:
            return LinkCheckResult(res.status_code, "broken", chain, "redirect loop")

    return LinkCheckResult(None, "broken", chain, "too many redirects")


async def check_with_get(client, url, chain):
    """Retry a link with GET. Returns None if GET fails too, so the caller can
    fall back to whatever HEAD already told us."""
    try:
        res = await client.get(
            url,
            timeout=request_timeout_seconds,
            headers=headers,
            follow_redirects=True,
        )
    except Exception:
        return None

    full_chain = chain + [str(redirect.url) for redirect in res.history]
    if res.status_code >= 400:
        return LinkCheckResult(res.status_code, "broken", full_chain, None)

    status = "redirect" if full_chain else "ok"
    return LinkCheckResult(res.status_code, status, full_chain, None, str(res.url))
