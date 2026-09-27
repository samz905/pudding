"""Small text helpers."""
import re
import unicodedata


def make_slug(title):
    """'Hello, World!' -> 'hello-world'."""
    s = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s or "untitled"


def word_count(text):
    return len(text.split())
