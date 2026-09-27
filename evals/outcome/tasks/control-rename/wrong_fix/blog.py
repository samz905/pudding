"""Blog post helpers."""
from textutil import make_slug, word_count


def post_url(title, year):
    return "/%d/%s/" % (year, make_slug(title))


def reading_minutes(body):
    return max(1, round(word_count(body) / 200))
