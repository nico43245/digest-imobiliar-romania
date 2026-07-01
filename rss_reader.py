"""Citire și parsare feed-uri RSS imobiliare din surse românești."""

import feedparser
import logging
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

logger = logging.getLogger(__name__)

FEEDS = [
    {
        "url": "https://www.zf.ro/rss/constructii-imobiliare",
        "source": "Ziarul Financiar",
    },
    {
        "url": "https://www.realitatea.net/feeds/stiri-imobiliare.xml",
        "source": "Realitatea.net",
    },
    {
        "url": "https://www.economica.net/imobiliare/feed/",
        "source": "Economica.net",
    },
]


def _parse_date(entry) -> datetime | None:
    """Extrage data publicării dintr-un entry RSS, cu fallback pe câmpuri alternative."""
    for field in ("published", "updated"):
        raw = getattr(entry, field, None) or entry.get(field)
        if raw:
            try:
                dt = parsedate_to_datetime(raw)
                # Normalizare la UTC aware
                return dt.astimezone(timezone.utc)
            except Exception:
                pass

    # feedparser parsează uneori data în struct_time
    for field in ("published_parsed", "updated_parsed"):
        parsed = getattr(entry, field, None) or entry.get(field)
        if parsed:
            try:
                return datetime(*parsed[:6], tzinfo=timezone.utc)
            except Exception:
                pass

    return None


def _clean_html(text: str) -> str:
    """Elimină tag-uri HTML simple din descrieri."""
    import re
    return re.sub(r"<[^>]+>", "", text or "").strip()


def fetch_articles() -> list[dict]:
    """Citește toate feed-urile și returnează lista unificată de articole."""
    articles = []

    for feed_config in FEEDS:
        url = feed_config["url"]
        source = feed_config["source"]
        try:
            logger.info(f"Citesc feed-ul: {url}")
            feed = feedparser.parse(url)

            if feed.bozo and not feed.entries:
                # bozo=True înseamnă eroare de parsare, dar poate există totuși entries
                raise ValueError(f"Feed invalid sau inaccessibil: {feed.bozo_exception}")

            for entry in feed.entries:
                title = (entry.get("title") or "").strip()
                link = entry.get("link") or entry.get("id") or ""
                description = _clean_html(entry.get("summary") or entry.get("description") or "")
                published = _parse_date(entry)

                if not link or not title:
                    continue

                articles.append({
                    "title": title,
                    "url": link,
                    "published": published,
                    "description": description,
                    "source": source,
                })

            logger.info(f"  → {len(feed.entries)} articole găsite în {source}")

        except Exception as exc:
            logger.error(f"Eroare la citirea feed-ului {source} ({url}): {exc}")
            # Continuăm cu celelalte feed-uri

    return articles


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    articole = fetch_articles()
    print(f"\nTotal articole găsite: {len(articole)}")
    for a in articole[:5]:
        pub = a["published"].strftime("%Y-%m-%d %H:%M UTC") if a["published"] else "dată necunoscută"
        print(f"  [{a['source']}] {a['title'][:80]} ({pub})")
