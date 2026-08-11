from collections import Counter
from urllib.parse import urlparse
from queries import get_all_links_for_job

report_filters = ("all", "internal", "external")


def build_report(job_id, filter_by="all"):
    all_links = get_all_links_for_job(job_id)

    broken = [link for link in all_links if link.status in ("broken", "timeout")]
    redirects = [link for link in all_links if link.status == "redirect"]
    long_redirects = [link for link in redirects if len(link.redirect_chain) > 1]
    internal = [link for link in broken if link.is_internal]
    external = [link for link in broken if not link.is_internal]

    if filter_by == "internal":
        selected = internal
    elif filter_by == "external":
        selected = external
    else:
        selected = broken

    grouped = {}
    for link in selected:
        grouped.setdefault(link.source_page, []).append(link)

    worst_pages = [{"page": page, "count": len(links)} for page, links in grouped.items()]
    worst_pages.sort(key=lambda row: row["count"], reverse=True)

    return {
        "summary": {
            "total_checked": len(all_links),
            "total_broken": len(broken),
            "total_redirects": len(redirects),
            "total_long_redirects": len(long_redirects),
            "broken_internal_count": len(internal),
            "broken_external_count": len(external),
        },
        "worst_pages": worst_pages[:5],
        "grouped_broken": {page: [as_dict(link) for link in links] for page, links in grouped.items()},
        "redirect_chains": [as_dict(link) for link in long_redirects],
        "external_domains": dict(Counter(domain_of(link.target_url) for link in external)),
    }


def domain_of(url):
    try:
        return urlparse(url).hostname or "unknown"
    except ValueError:
        return "unknown"


def as_dict(link):
    return {
        "target_url": link.target_url,
        "is_internal": link.is_internal,
        "status_code": link.status_code,
        "status": link.status,
        "redirect_chain": link.redirect_chain,
        "error_message": link.error_message,
    }
