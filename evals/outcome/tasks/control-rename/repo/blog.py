"""Blog post helpers."""
from textutil import slugify_title, word_count


def post_url(title, year):
    return "/%d/%s/" % (year, slugify_title(title))


def reading_minutes(body):
    return max(1, round(word_count(body) / 200))
