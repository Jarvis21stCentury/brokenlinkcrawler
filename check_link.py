import httpx
from dataclasses import dataclass
from constants import request_timeout_seconds, max_redirect_hops, user_agent

@dataclass
class LinkCheckResult:
    status_code: int | None
    status: str
    redirect_chain: list
    error_message: str | None

class HopOutcome:
    def __init__(self, is_final, result= None, next_url = None):
        self.is_final = is_final
        self.result = result
        self.next_url = next_url

def build_headers():
    return {"User-Agent": user_agent}

def is_redirect_status(code):
    return 300 <= code < 400

def is_error_status(code):
    return code >= 400

async def check_link(client, url):
    chain = []
    current = url
    hop = 0

    while hop < max_redirect_hops:
        hop += 1
        outcome = await attempt_head_check(client, current, chain, hop)
        if outcome.is_final:
            return outcome.result
        current = outcome.next_url

    return LinkCheckResult(None, "broken", chain, "too many redirects")

async def attempt_head_check(client, current, chain, hop):
    try:
        res = await client.head(
            current,
            timeout = request_timeout_seconds,
            follow_redirects = False,
            headers = build_headers(),
        )
    except httpx.TimeoutException:
        return await handle_failure(client, current, chain, hop, "timeout", "timed out")
    except Exception as e:
        return await handle_failure(client, current, chain, hop, "broken", str(e))

    return evaluate_response(res, current, chain)

def evaluate_response(res, current, chain):
    if is_redirect_status(res.status_code):
        return follow_redirect(res, current, chain)

    if is_error_status(res.status_code):
        return HopOutcome(True, LinkCheckResult(res.status_code, "broken", chain, None))

    final_status = "redirect" if chain else "ok"
    return HopOutcome(True, LinkCheckResult(res.status_code, final_status, chain, None))

def follow_redirect(res, current, chain):
    location = res.headers.get("location")
    if not location:
        result = LinkCheckResult(res.status_code, "broken", chain, "redirect w/ no location")
        return HopOutcome(True, result)

    chain.append(current)
    next_url = str(httpx.URL(current).join(location))

    if next_url in chain:
        result = LinkCheckResult(res.status_code, "broken", chain, "redirect loop")
        return HopOutcome(True, result)

    return HopOutcome(False, next_url=next_url)

async def handle_failure(client, current, chain, hop, status_label, message):
    if hop == 1:
        fallback = await try_get(client, current)
        if fallback:
            return HopOutcome(True, fallback)
    result = LinkCheckResult(None, status_label, chain, message)
    return HopOutcome(True, result)

async def try_get(client, url):
    try:
        response = await client.get(url, timeout=request_timeout_seconds, headers=build_headers())
    except Exception:
        return None

    if is_error_status(response.status_code):
        status = "broken"
    else:
        status = "ok"

    return LinkCheckResult(response.status_code, status, [], None)
