import asyncio
import httpx
from typing import List, Set, Tuple, Callable, Coroutine, Any, Dict, Optional
from urllib.parse import urlparse
import time
import random

# Assuming utils.py is in the same directory
from .utils import get_robots_rules, normalize_url, extract_links

# Define a type hint for the callback function - now expects more data
ProcessDataCallback = Callable[[Dict[str, Any]], Coroutine[Any, Any, None]]

# --- Per-Domain Concurrency Control ---
# Dictionary to hold semaphores for each domain
_domain_semaphores: Dict[str, asyncio.Semaphore] = {}
_domain_semaphores_lock = asyncio.Lock()


async def get_domain_semaphore(
    url: str, max_concurrency_per_domain: int
) -> asyncio.Semaphore:
    """Gets or creates a semaphore for the given URL's domain."""
    try:
        domain = urlparse(url).netloc
        if not domain:  # Should not happen with normalized URLs, but safety first
            domain = "_invalid_"
    except ValueError:
        domain = "_invalid_"  # Handle potential parsing errors

    async with _domain_semaphores_lock:
        if domain not in _domain_semaphores:
            _domain_semaphores[domain] = asyncio.Semaphore(max_concurrency_per_domain)
        return _domain_semaphores[domain]


# --- Retry Configuration ---
MAX_RETRIES = 3
INITIAL_BACKOFF = 1.0  # seconds
MAX_BACKOFF = 4.0  # seconds
RETRY_STATUS_CODES = {500, 502, 503, 504, 408, 429}  # Status codes to retry on


async def _worker(
    worker_id: int,
    queue: asyncio.Queue[Tuple[str, int]],
    visited: Set[str],
    client: httpx.AsyncClient,
    max_depth: int,
    max_urls: int,
    max_page_size: int,
    crawl_delay: float,
    user_agent: str,
    process_data_callback: ProcessDataCallback | None,
    global_counter: List[int],
    max_concurrency_per_domain: int,
    allowed_domains: Set[str] | None,
    log_func: Callable[[str, str], None],  # Use log_func
):
    """Async worker to process URLs from the queue with per-domain limits and retries."""
    while True:
        try:
            url, depth = await queue.get()
            crawl_data = {
                "url": url,
                "depth": depth,
                "status_code": None,
                "content_type": None,
                "content_length": None,
                "elapsed": None,
                "text": None,
                "error": None,
            }

            if depth > max_depth:
                queue.task_done()
                continue

            # --- Robots.txt Check ---
            robots_rules = await get_robots_rules(
                url, client, log_func
            )  # Pass log_func
            if robots_rules and not robots_rules.is_allowed(user_agent, url):
                log_func(
                    f"Disallowed by robots.txt: {url}", "INFO"
                )  # Use log_func, INFO level
                crawl_data["error"] = "Disallowed by robots.txt"
                if process_data_callback:
                    await process_data_callback(crawl_data)
                queue.task_done()
                continue

            # --- Per-Domain Semaphore ---
            domain_semaphore = await get_domain_semaphore(
                url, max_concurrency_per_domain
            )

            # --- Retry Loop ---
            retries = 0
            backoff_time = INITIAL_BACKOFF
            last_exception = None

            while retries <= MAX_RETRIES:
                try:
                    async with domain_semaphore:
                        await asyncio.sleep(crawl_delay)
                        log_func(
                            f"Worker {worker_id}: Crawling (Depth {depth}, Attempt {retries+1}): {url}",
                            "DEBUG",
                        )  # Use log_func, DEBUG level
                        req_start_time = time.monotonic()

                        async with client.stream(
                            "GET", url, follow_redirects=True, timeout=15.0
                        ) as response:
                            crawl_data["status_code"] = response.status_code
                            crawl_data["content_type"] = response.headers.get(
                                "content-type", ""
                            ).lower()
                            crawl_data["content_length"] = int(
                                response.headers.get("content-length", 0)
                            )

                            if response.status_code in RETRY_STATUS_CODES:
                                raise httpx.HTTPStatusError(
                                    f"Retryable status code: {response.status_code}",
                                    request=response.request,
                                    response=response,
                                )

                            if "html" in crawl_data["content_type"] and (
                                crawl_data["content_length"] == 0
                                or crawl_data["content_length"] <= max_page_size * 1024
                            ):
                                content_bytes = await response.aread()
                                crawl_data["text"] = content_bytes.decode(
                                    response.encoding or "utf-8", errors="replace"
                                )[:max_page_size]
                                response.raise_for_status()
                                duration = time.monotonic() - req_start_time
                                crawl_data["elapsed"] = duration
                                log_func(
                                    f"Fetched {url:.40} ({response.status_code}) in {duration:.2f}s",
                                    "INFO",
                                )  # Use log_func, INFO level

                                if depth < max_depth:
                                    new_links = extract_links(
                                        crawl_data["text"], url, log_func
                                    )
                                    current_domain = urlparse(url).netloc
                                    for link in new_links:
                                        link_domain = urlparse(link).netloc
                                        if (
                                            allowed_domains is not None
                                            and link_domain not in allowed_domains
                                        ):
                                            continue

                                        if (
                                            link not in visited
                                            and global_counter[0] < max_urls
                                        ):
                                            async with _domain_semaphores_lock:
                                                if (
                                                    link_domain in _domain_semaphores
                                                    or len(_domain_semaphores) < 1000
                                                ):
                                                    visited.add(link)
                                                    await queue.put((link, depth + 1))
                                                    global_counter[0] += 1
                            else:
                                log_func(
                                    f"Skipping non-HTML or large content ({crawl_data['content_type']}, {crawl_data['content_length']} bytes): {url}",
                                    "DEBUG",
                                )  # Use log_func, DEBUG level
                                crawl_data["error"] = "Skipped: Non-HTML or too large"
                                crawl_data["elapsed"] = (
                                    time.monotonic() - req_start_time
                                )

                        break  # Successful request

                except (
                    httpx.HTTPStatusError,
                    httpx.RequestError,
                    httpx.TimeoutException,
                ) as e:
                    last_exception = e
                    should_retry = False
                    if (
                        isinstance(e, httpx.HTTPStatusError)
                        and e.response.status_code in RETRY_STATUS_CODES
                    ):
                        should_retry = True
                    elif isinstance(
                        e,
                        (
                            httpx.TimeoutException,
                            httpx.NetworkError,
                            httpx.ConnectTimeout,
                            httpx.ReadTimeout,
                        ),
                    ):
                        should_retry = True

                    if should_retry and retries < MAX_RETRIES:
                        retries += 1
                        log_func(
                            f"Retrying {url} (Attempt {retries}/{MAX_RETRIES}) after error: {e}. Waiting {backoff_time:.2f}s...",
                            "DEBUG",
                        )  # Use log_func, WARNING level
                        await asyncio.sleep(backoff_time + random.uniform(0, 0.5))
                        backoff_time = min(backoff_time * 2, MAX_BACKOFF)
                        continue
                    else:
                        log_func(
                            f"Failed fetching {url} after {retries} retries: {e}",
                            "DEBUG",
                        )  # Use log_func, ERROR level
                        crawl_data["error"] = f"Failed after {retries} retries: {e}"
                        break
                except Exception as e:
                    log_func(
                        f"Unexpected Error processing {url}: {e}", "ERROR"
                    )  # Use log_func, ERROR level
                    last_exception = e
                    crawl_data["error"] = f"Unexpected Error: {e}"
                    break

            if process_data_callback:
                await process_data_callback(crawl_data)

            queue.task_done()

        except asyncio.CancelledError:
            return
        except Exception as e:
            log_func(
                f"Worker {worker_id}: Critical error in main loop: {e}", "CRITICAL"
            )  # Use log_func, CRITICAL level
            try:
                queue.task_done()
            except ValueError:
                pass
            await asyncio.sleep(1)


async def crawl(
    start_urls: List[str],
    log_func: Callable[[str, str], None],  # Use log_func
    max_depth: int = 2,
    max_urls: int = 100,
    max_concurrency_global: int = 10,  # Renamed for clarity
    max_concurrency_per_domain: int = 2,  # New setting
    crawl_delay: float = 0.25,  # Seconds between requests per worker per domain
    max_page_size: int = 1024 * 1024,  # Max characters to read per page (1MB)
    user_agent: str = "AethonCrawler/0.1 (+http://example.com/bot)",
    process_data_callback: ProcessDataCallback | None = None,
    stay_on_domain: bool = False,  # New configuration option
):
    """
    Asynchronously crawls web pages starting from a list of URLs.

    Args:
        start_urls: A list of initial URLs to crawl.
        max_depth: Maximum depth to follow links. 0 means only crawl start URLs.
        max_urls: Maximum total number of unique URLs to crawl.
        max_concurrency_global: Max number of total concurrent worker tasks.
        max_concurrency_per_domain: Max concurrent requests allowed to the same domain.
        crawl_delay: Minimum delay between requests to the same domain from each worker.
        max_page_size: Maximum content size (in characters) to process per page.
        user_agent: The User-Agent string to use for requests.
        process_data_callback: An async function to call with (url, html_content, depth)
                               for each successfully crawled page.
        stay_on_domain: If True, only follow links within the same domain(s)
                        as the start_urls. Defaults to False.
        log_func: A function to log messages with a given level.
    """
    queue: asyncio.Queue[Tuple[str, int]] = asyncio.Queue()
    visited: Set[str] = set()
    global_counter = [0]

    # --- Determine allowed domains if stay_on_domain is True ---
    allowed_domains: Set[str] | None = None
    if stay_on_domain:
        allowed_domains = set()
        for start_url in start_urls:
            try:
                domain = urlparse(start_url).netloc
                if domain:
                    allowed_domains.add(domain)
            except ValueError:
                log_func(
                    f"Could not parse domain from start URL: {start_url}", "WARNING"
                )  # Use log_func
        if not allowed_domains:
            log_func(
                "stay_on_domain is True, but no valid domains found in start_urls.",
                "WARNING",
            )  # Use log_func
        else:
            log_func(
                f"Restricting crawl to domains: {allowed_domains}", "INFO"
            )  # Use log_func

    # Clear domain semaphores from previous runs if any
    async with _domain_semaphores_lock:
        _domain_semaphores.clear()

    headers = {"User-Agent": user_agent}
    async with httpx.AsyncClient(
        headers=headers, http2=True, follow_redirects=True, timeout=20.0
    ) as client:

        # Initialize queue, visited set, and domain semaphores for start URLs
        for url in start_urls:
            normalized_url = normalize_url(url, url)
            if (
                normalized_url
                and normalized_url not in visited
                and global_counter[0] < max_urls
            ):
                # Check domain restriction *before* adding initial URLs
                if (
                    allowed_domains is not None
                    and urlparse(normalized_url).netloc not in allowed_domains
                ):
                    log_func(
                        f"Skipping start URL not in allowed domains: {normalized_url}",
                        "INFO",
                    )  # Use log_func
                    continue

                visited.add(normalized_url)
                await queue.put((normalized_url, 0))
                global_counter[0] += 1
                # Ensure semaphore exists for starting domains
                await get_domain_semaphore(normalized_url, max_concurrency_per_domain)

        workers = [
            asyncio.create_task(
                _worker(
                    i,
                    queue,
                    visited,
                    client,
                    max_depth,
                    max_urls,
                    max_page_size,
                    crawl_delay,
                    user_agent,
                    process_data_callback,
                    global_counter,
                    max_concurrency_per_domain,  # Pass new limit
                    allowed_domains,  # Pass the set of allowed domains
                    log_func,  # Pass log_func
                )
            )
            for i in range(max_concurrency_global)  # Use global limit here
        ]

        # Wait for the queue to be fully processed
        await queue.join()

        # Cancel worker tasks
        for worker in workers:
            worker.cancel()

        # Wait for workers to finish cancellation
        results = await asyncio.gather(*workers, return_exceptions=True)
        for i, result in enumerate(results):
            if isinstance(result, Exception) and not isinstance(
                result, asyncio.CancelledError
            ):
                log_func(
                    f"Worker {i} finished with error: {result}", "ERROR"
                )  # Use log_func

        log_func(
            f"Crawl finished. URLs added to queue: {global_counter[0]}. Unique URLs visited (approx): {len(visited)}",
            "INFO",
        )  # Use log_func
        # Clean up domain semaphores
        async with _domain_semaphores_lock:
            _domain_semaphores.clear()


# --- Example Usage ---
async def simple_processor(crawl_data: Dict[str, Any]):
    """Example callback to process crawled data."""
    print(
        f"  Processed (Depth {crawl_data['depth']}): {crawl_data['url']} ({len(crawl_data['text']) if crawl_data['text'] else 0} chars)"
    )
    # In a real scenario, you'd save content, extract data, etc.
    # e.g., await save_to_db(url, content)


async def main():
    start_time = time.time()
    print("--- Running crawl restricted to start domains ---")
    await crawl(
        start_urls=["https://crawler-test.com"],
        max_depth=3,
        max_urls=20000,
        max_concurrency_global=100,
        max_concurrency_per_domain=100,
        crawl_delay=0.25,
        process_data_callback=simple_processor,
        stay_on_domain=True,  # Enable domain restriction
        log_func=lambda msg, level: print(f"[{level}] {msg}"),  # Simple log function
    )
    print(f"Finished crawl in {time.time() - start_time:.2f} seconds")


if __name__ == "__main__":
    # ... existing dependency check ...
    try:
        import lxml  # Ensure lxml check is present if not already added
    except ImportError as e:
        print(f"Error: Missing dependency - {e.name}")
        print(
            "Please install required packages: pip install httpx robotexclusionrulesparser lxml"
        )
        exit(1)

    asyncio.run(main())

"""
start_urls=[
    "https://example.com",
    "https://httpbin.org/html",
    "https://httpbin.org/delay/1",
    "https://httpbin.org/status/503",
],
"""
