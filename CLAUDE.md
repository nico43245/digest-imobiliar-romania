# Proiect: Digest zilnic imobiliar România

## Context
Script care rulează automat o dată pe zi, citește știri imobiliare din surse
românești, le filtrează pe cele noi, le rezumă cu Claude API și le trimite
printr-un bot de Telegram, direct în chatul privat cu mine (nu canal).
Rulează pe GitHub Actions (cron), fără server propriu, fără bază de date
în cloud. Scop: demo de portofoliu pentru servicii de automatizare AI,
plus utilitate reală pentru urmărirea pieței.

## Surse RSS (în ordinea asta)
1. `https://www.zf.ro/rss/constructii-imobiliare`
2. `https://www.realitatea.net/feeds/stiri-imobiliare.xml`
3. Economica.net — verifică la `https://www.economica.net/rss.html` care
   feed exact corespunde secțiunii imobiliare/construcții și folosește-l

Dacă un feed nu răspunde sau dă eroare, sari peste el și continuă cu
celelalte — nu opri tot scriptul pentru un singur feed picat.

## Reguli ferme (verificabile, nu le încălca)
- Nu trimite niciodată același articol de două ori. Un articol e "trimis"
  dacă link-ul lui apare deja în `sent_articles.json`.
- Ia în calcul doar articole publicate în ultimele 24 de ore.
- Dacă niciun articol nou nu există într-o zi, trimite un singur mesaj
  scurt "Nicio știre nouă azi" — nu trimite mesaj gol și nu sari peste
  rulare fără notificare.
- Token-ul botului Telegram și chat ID-ul NU se scriu niciodată în cod.
  Vin din variabile de mediu: `TELEGRAM_BOT_TOKEN` și `TELEGRAM_CHAT_ID`.
- Maxim 8 articole pe digest. Dacă sunt mai multe articole noi, alege
  cele mai relevante pentru un dezvoltator/agent imobiliar (prețuri,
  proiecte noi, reglementări, date de piață) — nu doar primele cronologic.
- Dacă apelul către Claude API eșuează, retrimite o singură dată; dacă
  eșuează și a doua oară, trimite pe Telegram doar titlurile brute cu
  linkuri, fără rezumat, ca să nu pierdem digest-ul complet.

## Structura datelor

Fiecare articol reținut în `sent_articles.json`:
```json
{
  "url": "https://...",
  "title": "...",
  "sent_at": "2026-07-01T08:00:00"
}
```
Fișierul e o listă JSON simplă. La final de rulare, scriptul îl actualizează
și îl commite înapoi în repo (GitHub Actions face commit + push automat).

## Formatul rezumatului trimis pe Telegram
```
📍 Digest imobiliar — [dată]

1. [Titlu articol]
   [Rezumat 1-2 propoziții, ton: de ce contează pentru un dezvoltator/agent]
   🔗 [link]

2. ...
```
Rezumatul se cere de la Claude cu un prompt care include: titlul, sursa,
și (dacă disponibil din feed) descrierea articolului. Cere explicit
rezumat în română, concis, orientat spre impact practic — nu doar
reformulare a titlului.

## Structura fișierelor proiectului
```
digest-imobiliar/
├── CLAUDE.md
├── main.py              # script principal, orchestrează tot fluxul
├── rss_reader.py        # citește și parsează feed-urile RSS
├── summarizer.py        # apel către Claude API pentru rezumat
├── telegram_sender.py   # trimite mesajul final
├── sent_articles.json   # stare persistentă (commiса automat)
├── requirements.txt     # feedparser, anthropic, requests
└── .github/
    └── workflows/
        └── digest.yml   # cron trigger, 08:00 ora România (05:00 UTC)
```

## Stil de cod
- Python 3.11+, fără dependențe externe dacă există echivalent în
  librăria standard (folosește `requests` doar pentru Telegram, nu
  framework-uri grele)
- Comentarii în română, nume de variabile/funcții în engleză (convenție
  standard de cod)
- Fiecare fișier are o singură responsabilitate clară (vezi structura
  de mai sus) — nu pune toată logica într-un singur fișier mare
- Erorile se loghează clar în consolă (vizibil în logurile GitHub
  Actions), nu doar `pass` silențios

## Ce NU trebuie să facă
- Nu scrie credențiale sau token-uri direct în cod sau în commituri
- Nu trimite mesaje de test pe Telegram fără să-mi ceri confirmare
  explicită în timpul dezvoltării (ca să nu-mi spamez propriul chat)
- Nu adăuga surse RSS suplimentare fără să le validez întâi manual
- Nu instala pachete Python în afara celor din requirements.txt fără
  să explici de ce e nevoie de ele

## Pași de construcție, în ordine
1. Scrie `rss_reader.py` — citește cele 3 surse, întoarce listă de
   articole (titlu, link, dată publicare, descriere)
2. Scrie `sent_articles.json` (gol la început: `[]`) și logica de
   filtrare articole noi în `main.py`
3. Scrie `summarizer.py` — primește o listă de articole, întoarce
   rezumate folosind Claude API
4. Scrie `telegram_sender.py` — testează-l separat, întâi cu un
   mesaj simplu "test" (cere-mi confirmare înainte)
5. Leagă totul în `main.py`
6. Testează local, cu variabilele de mediu setate manual în terminal
7. Scrie `.github/workflows/digest.yml` cu trigger cron + trigger
   manual (`workflow_dispatch`) ca să pot testa din interfața GitHub
   fără să aștept ora programată
8. Adaugă `TELEGRAM_BOT_TOKEN` și `TELEGRAM_CHAT_ID` ca secrets în
   repo (Settings → Secrets and variables → Actions)
9. Rulează manual din GitHub Actions, verifică rezultatul, apoi lasă
   cron-ul să preia

## Notă despre cost
Claude API se plătește per token, separat de orice abonament Claude
folosit pentru development. La 8 articole/zi, costul e sub un leu/lună.
Dacă vreodată volumul crește mult, verificăm din nou costul înainte
să extindem numărul de surse sau frecvența.
