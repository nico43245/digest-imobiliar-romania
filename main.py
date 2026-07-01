"""Orchestrare principală: citire RSS → filtrare → rezumare → trimitere Telegram."""

import json
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from rss_reader import fetch_articles
from summarizer import summarize
from telegram_sender import send_message

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

SENT_ARTICLES_PATH = Path(__file__).parent / "sent_articles.json"
MAX_ARTICLES = 8

# Cuvinte cheie care cresc relevanța unui articol pentru un dezvoltator/agent imobiliar
RELEVANCE_KEYWORDS = [
    "preț", "prețuri", "apartament", "apartamente", "casă", "case",
    "proiect", "proiecte", "construcție", "construcții", "dezvoltator",
    "vânzare", "cumpărare", "tranzacție", "investiție", "piață",
    "reglementare", "lege", "autorizație", "teren", "birou", "birouri",
    "logistic", "comercial", "rezidențial", "chirie", "chirii",
    "ipotecă", "credit", "dobândă", "bnr", "analiză", "date",
]


def load_sent_articles() -> list[dict]:
    """Citește lista articolelor deja trimise din fișierul JSON."""
    if not SENT_ARTICLES_PATH.exists():
        return []
    try:
        with open(SENT_ARTICLES_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.error(f"Eroare la citirea {SENT_ARTICLES_PATH}: {e}. Se pornește cu listă goală.")
        return []


def save_sent_articles(sent: list[dict]) -> None:
    """Salvează lista actualizată de articole trimise."""
    try:
        with open(SENT_ARTICLES_PATH, "w", encoding="utf-8") as f:
            json.dump(sent, f, ensure_ascii=False, indent=2, default=str)
        logger.info(f"sent_articles.json actualizat ({len(sent)} articole total)")
    except OSError as e:
        logger.error(f"Eroare la salvarea {SENT_ARTICLES_PATH}: {e}")


def filter_new_articles(articles: list[dict], sent_urls: set[str]) -> list[dict]:
    """Păstrează doar articolele din ultimele 24h care nu au fost trimise deja."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    new = []
    for art in articles:
        if art["url"] in sent_urls:
            continue
        pub = art.get("published")
        if pub is None:
            # Articole fără dată: le includem cu prudență (pot fi vechi)
            logger.warning(f"Articol fără dată publicare, sărit: {art['title'][:60]}")
            continue
        if pub >= cutoff:
            new.append(art)
    logger.info(f"Articole noi în ultimele 24h: {len(new)}")
    return new


def relevance_score(article: dict) -> int:
    """Scor simplu de relevanță bazat pe cuvinte cheie în titlu."""
    title_lower = article["title"].lower()
    return sum(1 for kw in RELEVANCE_KEYWORDS if kw in title_lower)


def select_top_articles(articles: list[dict], max_count: int = MAX_ARTICLES) -> list[dict]:
    """Selectează cele mai relevante articole, maxim max_count."""
    if len(articles) <= max_count:
        return articles
    sorted_articles = sorted(articles, key=relevance_score, reverse=True)
    selected = sorted_articles[:max_count]
    logger.info(f"Selectate {len(selected)} din {len(articles)} articole după relevanță")
    return selected


def format_digest(articles: list[dict], summaries: list[str] | None, date_str: str) -> str:
    """Formatează digest-ul final pentru Telegram."""
    lines = [f"📍 Digest imobiliar — {date_str}", ""]

    for i, art in enumerate(articles, 1):
        lines.append(f"{i}. <b>{art['title']}</b>")

        if summaries and i <= len(summaries):
            lines.append(f"   {summaries[i - 1]}")
        # fallback: dacă nu avem rezumat, nu adăugăm nimic în plus

        lines.append(f"   🔗 {art['url']}")
        lines.append("")

    # Eliminăm ultima linie goală
    if lines and lines[-1] == "":
        lines.pop()

    return "\n".join(lines)


def main(dry_run: bool = False) -> None:
    """Fluxul principal al digest-ului."""
    today = datetime.now(timezone.utc).strftime("%d %B %Y")
    logger.info(f"=== Start digest imobiliar {today} ===")

    # 1. Citire articole din toate feed-urile RSS
    all_articles = fetch_articles()
    logger.info(f"Total articole din RSS: {len(all_articles)}")

    # 2. Filtrare: doar noi și din ultimele 24h
    sent_data = load_sent_articles()
    sent_urls = {entry["url"] for entry in sent_data}
    new_articles = filter_new_articles(all_articles, sent_urls)

    # 3. Dacă nu există articole noi, trimitem notificare și ieșim
    if not new_articles:
        mesaj = "📍 Digest imobiliar\n\nNicio știre nouă azi."
        logger.info("Niciun articol nou. Se trimite notificare.")
        if not dry_run:
            send_message(mesaj)
        else:
            print("\n--- DRY RUN ---")
            print(mesaj)
        return

    # 4. Selectare maxim 8 articole după relevanță
    articles_to_send = select_top_articles(new_articles)

    # 5. Rezumare cu Claude API
    summaries = summarize(articles_to_send)
    if summaries is None:
        logger.warning("Rezumarea a eșuat complet. Se folosesc titluri brute.")

    # 6. Formatare digest
    digest_text = format_digest(articles_to_send, summaries, today)

    # 7. Trimitere sau afișare (dry run)
    if dry_run:
        print("\n--- DRY RUN (fără trimitere Telegram) ---")
        print(digest_text)
        print(f"\n[{len(articles_to_send)} articole, rezumare: {'reușită' if summaries else 'eșuată (titluri brute)'}]")
    else:
        succes = send_message(digest_text)
        if not succes:
            logger.error("Trimiterea pe Telegram a eșuat.")
            sys.exit(1)

    # 8. Actualizare sent_articles.json (chiar și în dry run, ca să nu retrimitem)
    sent_at = datetime.now(timezone.utc).isoformat()
    for art in articles_to_send:
        sent_data.append({
            "url": art["url"],
            "title": art["title"],
            "sent_at": sent_at,
        })

    if not dry_run:
        save_sent_articles(sent_data)
    else:
        logger.info("[DRY RUN] sent_articles.json nu a fost modificat.")

    logger.info("=== Digest finalizat cu succes ===")


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    main(dry_run=dry_run)
