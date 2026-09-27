"""HTTP GET with retries, used by the sync job."""
import random
import time
import urllib.error
import urllib.request

RETRY_STATUSES = {429, 502, 503, 504}


class FetchError(Exception):
    pass


def _delay(attempt, base, cap, retry_after=None):
    """Seconds to wait before the next attempt (attempt is 1-based)."""
    if retry_after is not None:
        return min(cap, retry_after)
    return random.uniform(0, min(cap, base * 2 ** (attempt - 1)))


def _retry_after(err):
    value = err.headers.get("Retry-After") if err.headers else None
    try:
        return float(value) if value is not None else None
    except ValueError:
        return None


def fetch(url, attempts=4, base=0.5, cap=8.0, timeout=10, sleep=time.sleep, opener=urllib.request.urlopen):
    """Return the response body as bytes, retrying transient failures.

    Retries on connection errors, timeouts, and RETRY_STATUSES. Any other HTTP error
    (e.g. 404) is raised immediately. After `attempts` tries, raises FetchError.
    """
    last = None
    for attempt in range(1, attempts + 1):
        retry_after = None
        try:
            with opener(url, timeout=timeout) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            if e.code not in RETRY_STATUSES:
                raise
            last, retry_after = e, _retry_after(e)
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            last = e
        if attempt < attempts:
            sleep(_delay(attempt, base, cap, retry_after))
    raise FetchError("gave up on %s after %d attempts: %s" % (url, attempts, last))
