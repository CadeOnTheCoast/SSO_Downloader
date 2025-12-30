#!/usr/bin/env python3
"""Automated SSO PDF parser (local PDFs only) with waterway disambiguation.

Walks a folder of ADEM SSO report PDFs, extracts key fields, de-dupes by SSO ID
(keeping the newest by footer timestamp), disambiguates waterbodies that share
names across utilities, and writes a CSV.

Usage:
  # CLI args
  python parse_sso_pdfs.py /path/to/pdfs /path/out.csv

  # or env vars
  PDF_DIR=/path/to/pdfs OUTPUT_CSV=/path/out.csv python parse_sso_pdfs.py
"""

import os
import sys
import csv
import re
from datetime import datetime
from typing import Dict, List, Tuple, Optional

import pdfplumber

# -------- Config (env or CLI) --------
PDF_DIR = os.getenv("PDF_DIR", "/Users/cade/SSOs")
OUTPUT_CSV = os.getenv("OUTPUT_CSV", "parsed_sso_data.csv")
if len(sys.argv) >= 2:
    PDF_DIR = sys.argv[1]
if len(sys.argv) >= 3:
    OUTPUT_CSV = sys.argv[2]

# Toggle if you ever want the raw name preserved in a new column.
PRESERVE_RAW_WATERNAME = False  # set True to add 'receiving_water_raw' column

# Optional utility abbreviation overrides (exact, case-insensitive match on permittee)
UTILITY_ABBREVS = {
    "Baldwin County Sewer Service": "BCSS",
    "Baldwin County Sewer Service, LLC": "BCSS",
    "City of Daphne": "Daphne",
    "City of Fairhope": "Fairhope",
    "City of Spanish Fort": "Spanish Fort",
    "City of Foley": "Foley",
    "City of Robertsdale": "Robertsdale",
    # add others here as needed
}

# -------- CSV Schema --------
FIELDNAMES = [
    "sso_id",
    "permittee",
    "facility",
    "start",
    "stop",
    "volume",
    "receiving_water",
    "latitude",
    "longitude",
    "destination",
    "swimming_water",
    "monitoring",
    "cleaned",
    "disinfected",
    "cause",
    "file_name",
]
if PRESERVE_RAW_WATERNAME:
    FIELDNAMES.insert(FIELDNAMES.index("receiving_water") + 1, "receiving_water_raw")

# -------- Helpers --------

_LABEL_RE = re.compile(r"[A-Za-z].*?:?$")  # crude “looks like a label” detector

def _clean(s: Optional[str]) -> str:
    return (s or "").strip()

def extract_after(lines: List[str], label: str, default: str = "") -> str:
    label_l = label.lower()
    placeholders = {
        "creek or river",
        "drainage ditch",
        "storm drain",
        "provide",
        "n/a",
        "na",
    }
    for i, ln in enumerate(lines):
        if label_l in ln.lower():
            for nxt in lines[i + 1 : i + 10]:
                nxt = _clean(nxt)
                if not nxt:
                    continue
                if nxt.endswith(":") or _LABEL_RE.fullmatch(nxt):
                    break
                low = nxt.lower()
                if any(ph in low for ph in placeholders):
                    continue
                return nxt
            break
    return default

def get_permittee(lines: List[str]) -> str:
    for i, ln in enumerate(lines):
        if ln.strip().lower() == "permittee":
            for nxt in lines[i + 1 : i + 6]:
                nxt = _clean(nxt)
                if nxt and "permit number" not in nxt.lower():
                    return nxt
    for ln in lines:
        m = re.search(r"^Permittee\s+(.{3,})$", ln, flags=re.I)
        if m:
            return _clean(m.group(1))
    return ""

def extract_datetime_from_text(text: str, label_variants: Tuple[str, ...]) -> str:
    date_pat = r"(\d{1,2}/\d{1,2}/\d{4})"
    time_pat = r"(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm))"
    for lbl in label_variants:
        patt = rf"{re.escape(lbl)}[\s\S]{{0,250}}?{date_pat}[^\d]{{0,40}}?{time_pat}"
        m = re.search(patt, text, re.I)
        if m:
            try:
                return datetime.strptime(
                    f"{m.group(1)} {m.group(2)}", "%m/%d/%Y %I:%M %p"
                ).isoformat()
            except ValueError:
                continue
    return ""

def extract_sso_id(text: str) -> str:
    m = re.search(r"(?:Assigned\s+)?SSO\s*ID\s*(SSO-\d+)", text, re.I)
    return m.group(1) if m else ""

def extract_volume(text: str, lines: List[str]) -> str:
    m = re.search(r"(\d[\d,]*)\s*<\s*gallons\s*<=\s*(\d[\d,]*)", text, re.I)
    if m:
        return m.group(2).replace(",", "")
    for idx, ln in enumerate(lines):
        if "estimated volume discharged" in ln.lower():
            m_same = re.search(r"(\d[\d,]*)", ln)
            if m_same:
                return m_same.group(1).replace(",", "")
            lookahead = (l.strip() for l in lines[idx + 1 : idx + 8] if l.strip())
            for follow in lookahead:
                if len(follow) > 25:
                    continue
                m_num = re.match(r"^(\d[\d,]*)$", follow)
                if m_num:
                    return m_num.group(1).replace(",", "")
            break
    if re.search(r"Estimated Volume Discharged[^\n]{0,80}?Range", text, re.I):
        return "9999"
    return ""

def extract_lat_lon(text: str) -> Tuple[str, str]:
    patt = r"Latitude/Longitude of discharge\s*([-\d\.]+)[,\s]+([-\d\.]+)"
    m = re.search(patt, text, re.I)
    if m:
        return m.group(1), m.group(2)
    return "", ""

def extract_receiving_water(text: str, destination: Optional[str] = None) -> str:
    if destination and "ground absorbed" in destination.lower():
        return "Ground absorbed"
    lines = [ln.strip() for ln in text.splitlines()]
    helper_re = re.compile(
        r"provide the first named creek or river that receives the flow", re.I
    )
    for idx, ln in enumerate(lines):
        if helper_re.search(ln):
            for nxt in lines[idx + 1 : idx + 10]:
                nxt = _clean(nxt)
                if not nxt:
                    continue
                if re.fullmatch(r"(creek|river|drainage ditch|storm drain|provide.*)", nxt, re.I):
                    continue
                if re.search(r"[A-Za-z]", nxt):
                    return nxt
            break
    return destination or ""

def extract_submission_ts(text: str) -> Optional[datetime]:
    matches = re.findall(
        r"(\d{1,2}/\d{1,2}/\d{4})\s+(\d{1,2}:\d{2}:\d{2})\s*(AM|PM)",
        text,
        re.I,
    )
    if not matches:
        return None
    d, t, ampm = matches[-1]
    try:
        return datetime.strptime(f"{d} {t} {ampm}", "%m/%d/%Y %H:%M:%S %p")
    except ValueError:
        return None

def read_pdf_text(file_path: str) -> Tuple[str, List[str]]:
    with pdfplumber.open(file_path) as pdf:
        text = "\n".join(page.extract_text(layout=True) or "" for page in pdf.pages)
    lines = [ln.strip() for ln in text.splitlines()]
    return text, lines

def process_pdf(file_path: str) -> Dict[str, object]:
    text, lines = read_pdf_text(file_path)
    dest = extract_after(lines, "Destination of discharge")
    start = extract_datetime_from_text(
        text,
        ("Date/Time SSO Event Started", "Date / Time SSO Event Started", "Date - Time SSO Event Started"),
    )
    stop = extract_datetime_from_text(
        text,
        ("Date/Time SSO Event Stopped", "Date / Time SSO Event Stopped", "Date - Time SSO Event Stopped"),
    )
    lat, lon = extract_lat_lon(text)
    return {
        "sso_id": extract_sso_id(text),
        "permittee": get_permittee(lines),
        "facility": extract_after(lines, "Facility Name"),
        "start": start,
        "stop": stop,
        "volume": extract_volume(text, lines),
        "receiving_water": extract_receiving_water(text, dest),
        "latitude": lat,
        "longitude": lon,
        "destination": dest,
        "swimming_water": extract_after(lines, "Did the discharge reach a designated swimming water"),
        "monitoring": extract_after(lines, "Monitoring of the receiving water"),
        "cleaned": extract_after(lines, "Was the affected area cleaned"),
        "disinfected": extract_after(lines, "Was the affected area disinfected"),
        "cause": extract_after(lines, "Known or suspected cause of the discharge"),
        "file_name": os.path.basename(file_path),
        "_ts": extract_submission_ts(text),
    }

def dedupe_keep_newest(rows: List[Dict[str, object]]) -> Dict[str, Dict[str, object]]:
    by_key: Dict[str, Dict[str, object]] = {}
    for r in rows:
        sso_id = _clean(r.get("sso_id") or "")
        key = sso_id if sso_id else f"__noid__{_clean(r.get('file_name'))}"
        ts_new = r.get("_ts")
        old = by_key.get(key)
        if old is None:
            by_key[key] = r
            continue
        ts_old = old.get("_ts")
        if ts_new and not ts_old:
            by_key[key] = r
        elif ts_new and ts_old and ts_new > ts_old:
            by_key[key] = r
    return by_key

# ---- Waterway disambiguation ----

_WORDS_TO_STRIP = re.compile(
    r"\b(city|town|village|county|water\s+and\s+sewer\s+board|water\s+&\s*sewer\s+board|utilities?\s+board|utility\s+board|board|department|authority|of|the)\b",
    re.I,
)

def utility_short_name(permittee: str) -> str:
    p = _clean(permittee)
    if not p:
        return ""
    # Explicit overrides first
    for k, v in UTILITY_ABBREVS.items():
        if p.lower() == k.lower():
            return v
    # If an acronym appears in parentheses, prefer it: "… (BCSS)"
    m = re.search(r"\(([A-Z]{2,6})\)", p)
    if m:
        return m.group(1)
    # Strip boilerplate words
    core = _WORDS_TO_STRIP.sub("", p).strip()
    # Collapse multiple spaces
    core = re.sub(r"\s{2,}", " ", core)
    # If the result is long, keep last 1–2 words; else keep as is
    parts = core.split()
    if len(parts) >= 2:
        return " ".join(parts[-2:])
    return core or p

def disambiguate_waterways(rows: List[Dict[str, object]]) -> None:
    """
    If a receiving_water name is used by multiple permittees, rewrite it as
    '<name> – <utility short name>' for those rows.
    Operates in-place on the provided list.
    """
    # Build index: name -> set(permittees)
    index: Dict[str, set] = {}
    for r in rows:
        name = _clean(r.get("receiving_water"))
        if not name:
            continue
        permittee = _clean(r.get("permittee"))
        index.setdefault(name, set()).add(permittee)

    # Names that need disambiguation
    collisions = {name for name, owners in index.items() if len({o for o in owners if o}) > 1}
    if not collisions:
        return

    for r in rows:
        name = _clean(r.get("receiving_water"))
        if not name or name not in collisions:
            continue
        if PRESERVE_RAW_WATERNAME:
            r["receiving_water_raw"] = name
        tag = utility_short_name(_clean(r.get("permittee")))
        if tag:
            r["receiving_water"] = f"{name} - {tag}"
        # if no tag, leave as-is

# ---- Main ----

def main():
    pdf_paths: List[str] = []
    for root, _, files in os.walk(PDF_DIR):
        for filename in sorted(files):
            if filename.lower().endswith(".pdf"):
                pdf_paths.append(os.path.join(root, filename))

    rows: List[Dict[str, object]] = []
    missing_crit = 0
    for path in pdf_paths:
        try:
            print(f"Processing: {os.path.basename(path)}")
            row = process_pdf(path)
            rows.append(row)
            if not row.get("sso_id") or not row.get("start") or not row.get("volume"):
                missing_crit += 1
        except Exception as e:
            print(f"Failed on {os.path.basename(path)}: {e}")

    # de-dupe by SSO id
    by_key = dedupe_keep_newest(rows)
    deduped_rows = list(by_key.values())

    # disambiguate waterbody names across utilities
    disambiguate_waterways(deduped_rows)

    # write CSV
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as out_file:
        writer = csv.DictWriter(out_file, fieldnames=FIELDNAMES)
        writer.writeheader()
        for row in deduped_rows:
            out = dict(row)
            out.pop("_ts", None)
            # ensure all fields in schema
            for k in FIELDNAMES:
                out.setdefault(k, "")
            writer.writerow(out)

    total = len(pdf_paths)
    kept = len(deduped_rows)
    print(f"\nDone. PDFs scanned: {total} | Rows kept after de-dupe: {kept} | With missing critical fields (sso_id/start/volume): {missing_crit}")
    print(f"Parsed CSV -> {OUTPUT_CSV}")
    print(f"Parsed from -> {PDF_DIR}")

if __name__ == "__main__":
    main()