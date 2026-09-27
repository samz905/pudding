"""Pull the latest feed and write it to feed.json."""
import sys

from net import fetch

if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "https://example.com/feed.json"
    with open("feed.json", "wb") as f:
        f.write(fetch(url))
