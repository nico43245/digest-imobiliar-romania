"""Trimitere mesaje pe Telegram via Bot API."""

import logging
import os
import requests

logger = logging.getLogger(__name__)

TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"
MAX_MESSAGE_LENGTH = 4096  # limita Telegram pentru un singur mesaj


def send_message(text: str) -> bool:
    """
    Trimite un mesaj text în chat-ul privat configurat.
    Returnează True dacă a reușit, False în caz de eroare.
    """
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        logger.error("Variabilele de mediu TELEGRAM_BOT_TOKEN și/sau TELEGRAM_CHAT_ID lipsesc.")
        return False

    # Dacă mesajul depășește limita, îl tăiem și adăugăm avertisment
    if len(text) > MAX_MESSAGE_LENGTH:
        text = text[: MAX_MESSAGE_LENGTH - 50] + "\n\n[mesaj trunchiat — prea lung]"
        logger.warning("Mesajul a fost trunchiat pentru a respecta limita Telegram (4096 caractere).")

    url = TELEGRAM_API_URL.format(token=token)
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }

    try:
        response = requests.post(url, json=payload, timeout=15)
        response.raise_for_status()
        data = response.json()

        if data.get("ok"):
            logger.info("Mesaj trimis cu succes pe Telegram.")
            return True
        else:
            logger.error(f"Telegram API a returnat eroare: {data.get('description', 'necunoscut')}")
            return False

    except requests.exceptions.Timeout:
        logger.error("Timeout la trimiterea mesajului pe Telegram.")
        return False
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Eroare de conexiune la Telegram: {e}")
        return False
    except requests.exceptions.HTTPError as e:
        logger.error(f"Eroare HTTP la Telegram ({response.status_code}): {e}")
        return False
    except Exception as e:
        logger.error(f"Eroare neașteptată la trimiterea pe Telegram: {e}")
        return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    # Test simplu — rulează doar cu confirmare explicită din terminal
    mesaj_test = "Test bot digest imobiliar — mesaj de verificare conexiune."
    print(f"Gata de trimis: '{mesaj_test}'")
    print("Asigură-te că TELEGRAM_BOT_TOKEN și TELEGRAM_CHAT_ID sunt setate în mediu.")
    confirmare = input("Trimiți mesajul pe Telegram? (da/nu): ").strip().lower()

    if confirmare == "da":
        succes = send_message(mesaj_test)
        print("Trimis cu succes!" if succes else "Eroare la trimitere.")
    else:
        print("Anulat.")
