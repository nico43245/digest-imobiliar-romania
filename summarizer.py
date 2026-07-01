"""Rezumare articole imobiliare folosind Claude API (modelul Haiku 4.5)."""

import logging
import anthropic

logger = logging.getLogger(__name__)

MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 2048


def _build_prompt(articles: list[dict]) -> str:
    """Construiește promptul pentru rezumare."""
    articole_text = ""
    for i, art in enumerate(articles, 1):
        articole_text += f"\n--- Articol {i} ---\n"
        articole_text += f"Titlu: {art['title']}\n"
        articole_text += f"Sursă: {art['source']}\n"
        if art.get("description"):
            articole_text += f"Descriere: {art['description'][:500]}\n"
        articole_text += f"Link: {art['url']}\n"

    return f"""Ești un analist imobiliar expert. Pentru fiecare articol de mai jos, scrie un rezumat concis de 1-2 propoziții în română.

Tonul rezumatului trebuie să evidențieze impactul practic pentru un dezvoltator sau agent imobiliar: ce înseamnă această știre pentru piață, ce oportunitate sau risc prezintă, ce acțiune ar putea declanșa.

NU reformula pur și simplu titlul. Adaugă context și relevanță practică.

Articolele de rezumat:
{articole_text}

Răspunde EXCLUSIV în formatul următor (fără text suplimentar înainte sau după):

1. [rezumat articol 1]
2. [rezumat articol 2]
...și așa mai departe pentru fiecare articol"""


def summarize(articles: list[dict]) -> list[str] | None:
    """
    Primește o listă de articole și returnează o listă de rezumate.
    Returnează None dacă ambele încercări eșuează.
    """
    if not articles:
        return []

    client = anthropic.Anthropic()
    prompt = _build_prompt(articles)

    for attempt in range(1, 3):
        try:
            logger.info(f"Apel Claude API pentru rezumare (încercarea {attempt})...")
            response = client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                messages=[{"role": "user", "content": prompt}],
            )

            raw_text = response.content[0].text.strip()
            summaries = _parse_summaries(raw_text, len(articles))

            if summaries:
                logger.info(f"Rezumare reușită: {len(summaries)} articole procesate")
                return summaries

            logger.warning("Răspuns Claude neașteptat, reîncerc...")

        except anthropic.RateLimitError as e:
            logger.error(f"Rate limit Claude API (încercarea {attempt}): {e}")
        except anthropic.APIStatusError as e:
            logger.error(f"Eroare API Claude (încercarea {attempt}): {e.status_code} - {e.message}")
        except anthropic.APIConnectionError as e:
            logger.error(f"Eroare conexiune Claude API (încercarea {attempt}): {e}")
        except Exception as e:
            logger.error(f"Eroare neașteptată la rezumare (încercarea {attempt}): {e}")

        if attempt == 1:
            logger.info("Reîncerc rezumarea...")

    logger.error("Ambele încercări de rezumare au eșuat. Se va folosi fallback cu titluri brute.")
    return None


def _parse_summaries(text: str, expected_count: int) -> list[str]:
    """Parsează răspunsul Claude și extrage rezumatele numerotate."""
    lines = text.strip().split("\n")
    summaries = []

    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Caută linii care încep cu număr urmat de punct sau paranteză
        for sep in (". ", ") ", "- "):
            if line[0].isdigit() and sep in line:
                idx = line.index(sep)
                if idx <= 3:  # numărul are max 3 cifre
                    summary = line[idx + len(sep):].strip()
                    if summary:
                        summaries.append(summary)
                    break

    # Validare: verificăm că am obținut suficiente rezumate
    if len(summaries) < expected_count:
        logger.warning(f"Am obținut {len(summaries)} rezumate din {expected_count} așteptate")

    return summaries


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    # Test cu articole fictive
    test_articles = [
        {
            "title": "Prețurile apartamentelor în București au crescut cu 8% în T1 2026",
            "source": "Ziarul Financiar",
            "description": "Piața rezidențială din capitală continuă tendința ascendentă...",
            "url": "https://www.zf.ro/test1",
        },
        {
            "title": "Noi reglementări pentru autorizațiile de construcție din 2026",
            "source": "Economica.net",
            "description": "Ministerul Dezvoltării a anunțat modificări la procedura de autorizare...",
            "url": "https://www.economica.net/test2",
        },
    ]

    rezultate = summarize(test_articles)
    if rezultate:
        for i, rez in enumerate(rezultate, 1):
            print(f"{i}. {rez}")
    else:
        print("Rezumarea a eșuat.")
