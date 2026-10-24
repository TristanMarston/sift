"""Listing photo URLs: ask each marketplace CDN for a small variant (shared by step 05 and the API thumbnails)."""
import re

# Each CDN's smallest variant that is still >= 224 px (the model's input), measured Oct 23: ~10x fewer bytes.
SMALL = [
    (re.compile(r"^(https://media-photos\.depop\.com/.+/)P\d+\.jpg$"), r"\1P5.jpg"),                   # 320 px
    (re.compile(r"^(https://di2ponv0v5otw\.cloudfront\.net/.+/)[lm]_([^/]+)$"), r"\1s_\2"),           # 285x380
    (re.compile(r"^(https://media-assets\.grailed\.com/[^?]+)$"), r"\1?w=320"),                       # 320 wide
]


def small_url(url: str) -> str:
    for pattern, repl in SMALL:
        if pattern.match(url):
            return pattern.sub(repl, url)
    return url
