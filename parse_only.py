#!/usr/bin/env python3
"""Automated SSO PDF downloader and parser.

This script scrapes Alabama's ADEM eFile site for all Sanitary Sewer Overflow
(SSO) reports filed in 2024, downloads the PDF documents, extracts key fields
and writes the results to ``sso_reports_2024.csv``.
"""


import os
import csv
import re
import itertools  # needed by some helpers in future refactors
import pdfplumber
from datetime import datetime
from typing import List

# Constants
PDF_DIR = "/Users/cade/SSOs"
OUTPUT_CSV = "parsed_sso_data.csv"

# Target fields
FIELDNAMES = [
    "permittee", "facility", "start", "stop", "volume", "receiving_water",
    "latitude", "longitude", "destination", "swimming_water",
    "monitoring", "cleaned", "disinfected", "cause", "file_name"
]

# Helpers
def extract_datetime(lines, label):
    label = label.lower()
    for i, ln in enumerate(lines):
        if label in ln.lower():
            # scan forward for a MM/DD/YYYY token and a time token
            date_str, time_str = None, None
            for tok in lines[i + 1 : i + 6]:  # look a few lines ahead
                if not date_str and re.match(r"\d{1,2}/\d{1,2}/\d{4}", tok):
                    date_str = tok
                elif not time_str and re.match(r"\d{1,2}:\d{2}\s*(?:am|pm)", tok, re.I):
                    time_str = tok
                if date_str and time_str:
                    return datetime.strptime(f"{date_str} {time_str}", "%m/%d/%Y %I:%M %p").isoformat()
            break
    return ""

def extract_after(lines, label, default=""):
    """
    Return the first non‑blank line that follows a line containing *label* (case‑insensitive).
    """
    label = label.lower()
    for i, ln in enumerate(lines):
        if label in ln.lower():
            # return next non‑empty line
            for nxt in lines[i + 1 :]:
                if nxt:
                    return nxt
            break
    return default

def get_permittee(lines):
    """
    Return the actual permittee name, skipping the generic 'Permittee Information'
    header that is followed by 'Permit Number'.
    """
    for i, ln in enumerate(lines):
        if ln.strip().lower() == "permittee":
            for nxt in lines[i + 1:]:
                if nxt and "Permit Number" not in nxt:
                    return nxt
    return ""

def extract_datetime_from_text(text: str, label: str) -> str:
    """
    Capture the ISO‑8601 datetime that appears shortly after *label*.

    The pattern we see in these PDFs is:

        Date/Time SSO Event Started:
        Date        Time
        12/30/2024  03:00 pm

    or the date/time can be on the same line.  We therefore scan the next
    ~250 characters (incl. new‑lines) for the first date token and the first
    time token, then combine them.
    """
    # date token  —  1/1/2024, 12/30/2024, etc.
    date_pat = r"(\d{1,2}/\d{1,2}/\d{4})"
    # time token  —  09:30 am, 3:05 PM, etc.
    time_pat = r"(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm))"
    patt = rf"{re.escape(label)}[\s\S]{{0,250}}?{date_pat}[^\d]{{0,20}}?{time_pat}"
    m = re.search(patt, text, re.I)
    if not m:
        return ""
    try:
        return datetime.strptime(
            f"{m.group(1)} {m.group(2)}", "%m/%d/%Y %I:%M %p"
        ).isoformat()
    except ValueError:
        return ""

def extract_sso_id(text: str) -> str:
    """
    Return the SSO‑002xxxxx identifier found near the top of the form.
    """
    m = re.search(r"SSO\s*ID\s*(SSO-\d+)", text, re.I)
    return m.group(1) if m else ""

def extract_volume(text: str, lines: list[str]) -> str:
    # --- Case 1: explicit range --------------------------------------------------------------
    m = re.search(r"(\d[\d,]*)\s*<\s*gallons\s*<=\s*(\d[\d,]*)", text, re.I)
    if m:
        return m.group(2).replace(",", "")

    # --- Case 2: single numeric value --------------------------------------------------------
    for idx, ln in enumerate(lines):
        if "estimated volume discharged" in ln.lower():
            # 2a ─ a number might be on the **same** line
            m_same = re.search(r"(\d[\d,]*)", ln)
            if m_same:
                return m_same.group(1).replace(",", "")

            # 2b ─ otherwise look ahead a few lines for a stand‑alone number
            lookahead = (l.strip() for l in lines[idx + 1 : idx + 8] if l.strip())
            for follow in lookahead:
                # skip explanatory sentences like "Estimated volumes above 1,000,000 gallons …"
                if len(follow) > 25:
                    continue
                m_num = re.match(r"^(\d[\d,]*)$", follow)
                if m_num:
                    return m_num.group(1).replace(",", "")
            break  # stop after first match

    # --- Case 3: range chosen but numbers not printed ----------------------------------------
    if re.search(r"Estimated Volume Discharged[^\\n]{0,60}?Range", text, re.I):
        return "9999"

    return ""

def extract_lat_lon(text):
    match = re.search(r"Latitude/Longitude of discharge\s*([\d\.\-]+)[^\d\-]+([\d\.\-]+)", text)
    if match:
        return match.group(1), match.group(2)
    return "", ""

def extract_receiving_water(text: str, destination: str | None = None) -> str:
    """
    Return the named creek / river when available, otherwise a sensible fallback.

    Logic
    -----
    1. If *destination* contains “Ground Absorbed”, return exactly **“Ground absorbed”**.
    2. Otherwise search for the helper prompt that appears in every form:

           Provide the first named creek or river that receives the flow.

       Grab the first non‑blank line that follows the prompt which:
         • has at least one alphabetic character, and
         • is *not* a generic placeholder such as “Creek or River”, “Drainage Ditch”, etc.

    3. If a name is found return it; otherwise fall back to *destination* (may be
       “Drainage Ditch”, “Storm Drain”, etc.).
    """
    if destination and "ground absorbed" in destination.lower():
        return "Ground absorbed"

    helper_re = re.compile(
        r"provide the first named creek or river that receives the flow",
        re.I,
    )

    # Work with a list of trimmed lines to keep scanning simple
    lines: list[str] = [ln.strip() for ln in text.splitlines()]
    waterbody = ""

    for idx, ln in enumerate(lines):
        if helper_re.search(ln):
            # Look ahead a handful of lines for the first “real” name
            for nxt in lines[idx + 1 : idx + 8]:
                nxt = nxt.strip()
                if not nxt:
                    continue
                # Skip obvious placeholders / prompts
                if re.fullmatch(
                    r"(creek|river|drainage ditch|storm drain|provide.*)", nxt,
                    re.I,
                ):
                    continue
                # Accept the line if it contains any alphabetic character
                if re.search(r"[A-Za-z]", nxt):
                    waterbody = nxt
                    break
            break

    return waterbody or (destination or "")

def extract_submission_ts(text: str) -> datetime | None:
    """
    Each page footer ends with something like:
        12/31/2024 2:50:52 PM Page 1 of 5
    Use the **last** occurrence as the document timestamp so duplicates
    can be resolved (keep the *newest* copy).
    """
    matches = re.findall(
        r"(\d{1,2}/\d{1,2}/\d{4})\s+(\d{1,2}:\d{2}:\d{2})\s*(AM|PM)",
        text, re.I
    )
    if not matches:
        return None
    d, t, ampm = matches[-1]
    try:
        return datetime.strptime(f"{d} {t} {ampm}", "%m/%d/%Y %H:%M:%S %p")
    except ValueError:
        return None

def process_pdf(file_path):
    with pdfplumber.open(file_path) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)
        lines = [ln.strip() for ln in text.splitlines()]

    dest = extract_after(lines, "Destination of discharge")
    row = {
        "permittee": get_permittee(lines),
        "facility": extract_after(lines, "Facility Name"),
        "start": extract_datetime_from_text(text, "Date/Time SSO Event Started"),
        "stop": extract_datetime_from_text(text, "Date/Time SSO Event Stopped"),
        "volume": extract_volume(text, lines),
        "receiving_water": extract_receiving_water(text, dest),
        "latitude": "",
        "longitude": "",
        "destination": dest,
        "swimming_water": extract_after(lines, "Did the discharge reach a designated swimming water"),
        "monitoring": extract_after(lines, "Monitoring of the receiving water"),
        "cleaned": extract_after(lines, "Was the affected area cleaned"),
        "disinfected": extract_after(lines, "Was the affected area disinfected"),
        "cause": extract_after(lines, "Known or suspected cause of the discharge"),
        "file_name": os.path.basename(file_path)
    }
    lat, lon = extract_lat_lon(text)
    row["latitude"], row["longitude"] = lat, lon
    row["sso_id"] = extract_sso_id(text)
    row["_ts"] = extract_submission_ts(text)  # used for de‑duping
    return row

def main():
    # collect rows keyed by SSO id so we can keep the latest revision
    by_sso: dict[str, dict] = {}

    for root, _, files in os.walk(PDF_DIR):
        for filename in sorted(files):
            if not filename.lower().endswith(".pdf"):
                continue
            file_path = os.path.join(root, filename)
            try:
                print(f"Processing: {filename}")
                row = process_pdf(file_path)
                sso_id = row.pop("sso_id", None)
                ts = row.pop("_ts", None)
                if not sso_id:
                    # no id – write immediately, nothing to de‑dup
                    by_sso[f"__noid__{filename}"] = row
                    continue
                existing = by_sso.get(sso_id)
                if (existing is None) or (ts and existing.get("_ts") and ts > existing["_ts"]):
                    row["_ts"] = ts
                    by_sso[sso_id] = row
            except Exception as e:
                print(f"Failed on {filename}: {e}")

    # write out CSV
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as out_file:
        writer = csv.DictWriter(out_file, fieldnames=FIELDNAMES)
        writer.writeheader()
        for row in by_sso.values():
            # internal helper not part of output
            row.pop("_ts", None)
            writer.writerow(row)

if __name__ == "__main__":
    main()
