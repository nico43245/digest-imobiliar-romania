"""Rezumare articole imobiliare folosind Groq API cu LLaMA 3 (gratuit)."""

import logging
import os
from groq import Groq

logger = logging.getLogger(__name__)

MODEL = "llama-3.1-8b-instant"


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

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        logger.error("Variabila de mediu GROQ_API_KEY lipsește.")
        return None

    client = Groq(api_key=api_key)
    prompt = _build_prompt(articles)

    for attempt in range(1, 3):
        try:
            logger.info(f"Apel Groq API pentru rezumare (încercarea {attempt})...")
            response = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1024,
                temperature=0.3,
            )
            raw_text = response.choices[0].message.content.strip()
            summaries = _parse_summaries(raw_text, len(articles))

            if summaries:
                logger.info(f"Rezumare reușită: {len(summaries)} articole procesate")
                return summaries

            logger.warning("Răspuns Groq neașteptat, reîncerc...")

        except Exception as e:
            logger.error(f"Eroare la rezumare cu Groq (încercarea {attempt}): {e}")

        if attempt == 1:
            logger.info("Reîncerc rezumarea...")

    logger.error("Ambele încercări de rezumare au eșuat. Se va folosi fallback cu titluri brute.")
    return None


def _parse_summaries(text: str, expected_count: int) -> list[str]:
    """Parsează răspunsul și extrage rezumatele numerotate."""
    lines = text.strip().split("\n")
    summaries = []

    for line in lines:
        line = line.strip()
        if not line:
            continue
        for sep in (". ", ") ", "- "):
            if line[0].isdigit() and sep in line:
                idx = line.index(sep)
                if idx <= 3:
                    summary = line[idx + len(sep):].strip()
                    if summary:
                        summaries.append(summary)
                    break

    if len(summaries) < expected_count:
        logger.warning(f"Am obținut {len(summaries)} rezumate din {expected_count} așteptate")

    return summaries
