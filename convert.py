#!/usr/bin/env python3
"""
Daily Greek fuel prices per prefecture -> prices.json

Downloads the newest "IMERISIO_DELTIO_ANA_NOMO_dd_mm_yyyy.pdf" from www.fuelprices.gr
(Ministry of Development, published on working days, prices of the previous day),
extracts the prices with pypdf and writes a small JSON file that an ESP32 can read.
The previous bulletin is parsed too, so the change since then is included.

Idea and prefecture list from https://github.com/mavroprovato/fuelpricesgr (MIT license).

Usage:  python convert.py [output.json]       needs:  pip install pypdf
"""
import datetime
import io
import json
import re
import sys
import urllib.error
import urllib.request

import pypdf

URL = "https://www.fuelprices.gr/files/deltia/IMERISIO_DELTIO_ANA_NOMO_{:%d_%m_%Y}.pdf"
LOOK_BACK_DAYS = 14

# id -> name as printed in the bulletin (genitive, upper case)
PREFECTURES = {
    "ATTICA": "ΑΤΤΙΚΗΣ", "AETOLIA_ACARNANIA": "ΑΙΤΩΛΙΑΣ ΚΑΙ ΑΚΑΡΝΑΝΙΑΣ", "ARGOLIS": "ΑΡΓΟΛΙΔΟΣ",
    "ARKADIA": "ΑΡΚΑΔΙΑΣ", "ARTA": "ΑΡΤΗΣ", "ACHAEA": "ΑΧΑΪΑΣ", "BOEOTIA": "ΒΟΙΩΤΙΑΣ",
    "GREVENA": "ΓΡΕΒΕΝΩΝ", "DRAMA": "ΔΡΑΜΑΣ", "DODECANESE": "ΔΩΔΕΚΑΝΗΣΟΥ", "EVROS": "ΕΒΡΟΥ",
    "EUBOEA": "ΕΥΒΟΙΑΣ", "EVRYTANIA": "ΕΥΡΥΤΑΝΙΑΣ", "ZAKYNTHOS": "ΖΑΚΥΝΘΟΥ", "ELIS": "ΗΛΕΙΑΣ",
    "IMATHIA": "ΗΜΑΘΙΑΣ", "HERAKLION": "ΗΡΑΚΛΕΙΟΥ", "THESPROTIA": "ΘΕΣΠΡΩΤΙΑΣ",
    "THESSALONIKI": "ΘΕΣΣΑΛΟΝΙΚΗΣ", "IOANNINA": "ΙΩΑΝΝΙΝΩΝ", "KAVALA": "ΚΑΒΑΛΑΣ",
    "KARDITSA": "ΚΑΡΔΙΤΣΗΣ", "KASTORIA": "ΚΑΣΤΟΡΙΑΣ", "KERKYRA": "ΚΕΡΚΥΡΑΣ",
    "CEPHALONIA": "ΚΕΦΑΛΛΗΝΙΑΣ", "KILKIS": "ΚΙΛΚΙΣ", "KOZANI": "ΚΟΖΑΝΗΣ", "CORINTHIA": "ΚΟΡΙΝΘΙΑΣ",
    "CYCLADES": "ΚΥΚΛΑΔΩΝ", "LACONIA": "ΛΑΚΩΝΙΑΣ", "LARISSA": "ΛΑΡΙΣΗΣ", "LASITHI": "ΛΑΣΙΘΙΟΥ",
    "LESBOS": "ΛΕΣΒΟΥ", "LEFKADA": "ΛΕΥΚΑΔΟΣ", "MAGNESIA": "ΜΑΓΝΗΣΙΑΣ", "MESSENIA": "ΜΕΣΣΗΝΙΑΣ",
    "XANTHI": "ΞΑΝΘΗΣ", "PELLA": "ΠΕΛΛΗΣ", "PIERIA": "ΠΙΕΡΙΑΣ", "PREVEZA": "ΠΡΕΒΕΖΗΣ",
    "RETHYMNO": "ΡΕΘΥΜΝΗΣ", "RHODOPE": "ΡΟΔΟΠΗΣ", "SAMOS": "ΣΑΜΟΥ", "SERRES": "ΣΕΡΡΩΝ",
    "TRIKALA": "ΤΡΙΚΑΛΩΝ", "PHTHIOTIS": "ΦΘΙΩΤΙΔΟΣ", "FLORINA": "ΦΛΩΡΙΝΗΣ", "PHOCIS": "ΦΩΚΙΔΟΣ",
    "CHALKIDIKI": "ΧΑΛΚΙΔΙΚΗΣ", "CHANIA": "ΧΑΝΙΩΝ", "CHIOS": "ΧΙΟΥ",
}
BY_NAME = {name.replace(" ", ""): pid for pid, name in PREFECTURES.items()}

PRICE = r"\d,\d{3}"
ROW = re.compile(r"ΝΟΜΟΣ\s+([Α-ΩΆ-ΏΪΫ][Α-ΩΆ-ΏΪΫ ]*?)\s+((?:(?:" + PRICE + r"|-)\s*){3,6})")


def fetch(date):
    """PDF bytes of the bulletin for this date, or None."""
    req = urllib.request.Request(URL.format(date), headers={"User-Agent": "fuelprices-gr-json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data = r.read()
    except urllib.error.URLError:
        return None
    return data if data.startswith(b"%PDF") else None  # missing files return an HTML page


def columns(text):
    """Fuel columns in the order of the table header."""
    header = re.search(r"ΝΟΜΟΣ\s+Αμόλυβδη.*", text)
    h = header.group(0) if header else ""
    cols = ["u95", "u100"]
    if "Super" in h:
        cols.append("super")
    cols += ["diesel", "lpg"]
    if "Θέρμανσης" in h:
        cols.append("heating")
    return cols


def parse(pdf):
    text = "".join(page.extract_text() or "" for page in pypdf.PdfReader(io.BytesIO(pdf)).pages)
    cols = columns(text)
    out = {}
    for m in ROW.finditer(text):
        name = re.sub(r"\s+", " ", m.group(1)).strip()
        pid = BY_NAME.get(name.replace(" ", ""), name)
        values = m.group(2).split()
        if len(values) != len(cols):
            print(f"warning: {name}: {len(values)} values for {len(cols)} columns", file=sys.stderr)
            continue
        row = {"name": name}
        for col, v in zip(cols, values):
            if v != "-":
                row[col] = float(v.replace(",", "."))
        out[pid] = row
    return out


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else "prices.json"
    today = datetime.date.today()
    found = []  # (date, prefectures), newest first
    for back in range(LOOK_BACK_DAYS + 1):
        d = today - datetime.timedelta(days=back)
        pdf = fetch(d)
        if not pdf:
            continue
        data = parse(pdf)
        print(f"{d}: {len(data)} prefectures")
        if len(data) >= 40:
            found.append((d, data))
        if len(found) == 2:
            break
    if not found:
        sys.exit("no bulletin found")

    date, current = found[0]
    previous = found[1][1] if len(found) > 1 else {}
    for pid, row in current.items():
        prev = previous.get(pid, {})
        chg = {k: round(v - prev[k], 3) for k, v in row.items() if k != "name" and k in prev}
        if chg:
            row["chg"] = chg

    result = {
        "date": date.isoformat(),
        "previous": found[1][0].isoformat() if len(found) > 1 else None,
        "source": "www.fuelprices.gr",
        "unit": "EUR/L incl. VAT (LPG EUR/L)",
        "fuels": {"u95": "Unleaded 95", "u100": "Unleaded 100", "super": "Super", "diesel": "Diesel",
                  "lpg": "LPG (Autogas)", "heating": "Heating diesel"},
        "prefectures": current,
    }
    with open(target, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, separators=(",", ":"))
    print(f"wrote {target}: {date}, {len(current)} prefectures")


if __name__ == "__main__":
    main()
