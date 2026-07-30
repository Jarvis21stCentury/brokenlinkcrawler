import httpx
from bs4 import BeautifulSoup
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse, urlunparse
from constants import request_timeout_seconds, user_agent

skip_prefixes = ("mailto:", "tel:", "javascript:", "data:", "#")
html_content_type = "text/html"

@dataclass
class FetchedPage:
    url: str
    status_code: int | None
    html: str | None
    error: str | None


async def fetch_page(client, url):
    headers = {"user-agent": user_agent}
    try:
        response = await client.get(url, timeout=request_timeout_seconds, headers=headers, follow_redirects=True)
    except httpx.TimeoutException:
        return FetchedPage(url, None, None, "timeout")
    except httpx.ConnectError as e:
        return FetchedPage(url, None, None, "connect error: " + str(e))
    except Exception as e:
        return FetchedPage(url, None, None, str(e))

    content_type = response.headers.get("content-type", "")
    html = response.text if html_content_type in content_type else None
    return FetchedPage(url, response.status_code, html, None)


def extract_links(html, page_url):
    soup = BeautifulSoup(html, "html.parser")
    found_links = set()

    for anchor_tag in soup.find_all("a", href=True):
        href = anchor_tag["href"].strip()
        if not href or href.startswith(skip_prefixes):
            continue
        # drop the fragment so #section anchors don't get queued as separate pages
        absolute_url = urljoin(page_url, href)
        without_fragment = urlparse(absolute_url)._replace(fragment="")
        found_links.add(urlunparse(without_fragment))

    return list(found_links)


def safe_hostname(url):
    try:
        return urlparse(url).hostname
    except ValueError:
        return None


def is_internal_url(link, root_url):
    link_host = safe_hostname(link)
    root_host = safe_hostname(root_url)
    if link_host is None or root_host is None:
        return False
    return link_host == root_host


def count_internal_links(links, root_url):
    total = 0
    for link in links:
        if is_internal_url(link, root_url):
            total += 1
    return total
