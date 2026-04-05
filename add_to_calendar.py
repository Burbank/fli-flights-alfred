#!/usr/bin/env python3
"""Create a timezone-aware .ics calendar event from flight data and open in Calendar.app."""

import base64
import json
import os
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime

# ---------------------------------------------------------------------------
# IATA → IANA timezone via airportsdata (7,800+ airports, pip install airportsdata).
# Loaded once on import; falls back gracefully if the package is missing.
# ---------------------------------------------------------------------------
try:
    import airportsdata
    _AIRPORTS = airportsdata.load("IATA")
except ImportError:
    _AIRPORTS = None


def tz_for_airport(code):
    """Return IANA timezone for an IATA airport code, or None if unknown."""
    if not _AIRPORTS:
        return None
    ap = _AIRPORTS.get(code.upper())
    return ap["tz"] if ap else None


def dt_to_ical(iso_str):
    """Convert '2026-05-15T07:50:00' to iCal format '20260515T075000'."""
    return iso_str.replace("-", "").replace(":", "").replace("T", "T")[:15]


def escape_ics_text(s):
    """Escape text for iCalendar TEXT fields."""
    return s.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def build_ics(legs, price=None, currency=None, url=None, others=None):
    """Build an .ics calendar string with one event per flight leg."""
    cal_lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Fli Flights//Alfred Workflow//EN",
        "METHOD:PUBLISH",
        "CALSCALE:GREGORIAN",
    ]

    now_stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

    for i, leg in enumerate(legs):
        dep_code = leg.get("departure_airport", {}).get("code", "")
        arr_code = leg.get("arrival_airport", {}).get("code", "")
        dep_name = leg.get("departure_airport", {}).get("name", dep_code)
        arr_name = leg.get("arrival_airport", {}).get("name", arr_code)
        dep_time = leg.get("departure_time", "")
        arr_time = leg.get("arrival_time", "")
        airline = leg.get("airline", {}).get("name", "")
        flight_num = leg.get("flight_number", "")
        duration = leg.get("duration", 0)

        dep_tz = tz_for_airport(dep_code)
        arr_tz = tz_for_airport(arr_code)

        flight_label = f"{airline} {flight_num}".strip() or "Flight"
        summary = f"✈ {flight_label} · {dep_code} → {arr_code}"

        dur_h, dur_m = divmod(duration, 60)
        dep_local = dep_time.split("T")[1][:5] if "T" in dep_time else ""
        arr_local = arr_time.split("T")[1][:5] if "T" in arr_time else ""

        desc_parts = [
            f"{flight_label}",
            f"{dep_code} ({dep_local}) → {arr_code} ({arr_local})",
            f"Duration: {dur_h}h{dur_m:02d}m",
            "",
        ]
        if price and currency and i == 0:
            desc_parts.append(f"Price: {currency} {price:.0f}")
        desc_parts.append(f"Departure: {dep_name}")
        desc_parts.append(f"Arrival: {arr_name}")
        if dep_tz:
            desc_parts.append(f"Departure TZ: {dep_tz}")
        if arr_tz:
            desc_parts.append(f"Arrival TZ: {arr_tz}")
        if others and i == 0:
            desc_parts.append("")
            desc_parts.append("Other options:")
            for other in others:
                desc_parts.append(f"  • {other}")
        desc_parts.extend(["", "Created with Alfred Fli Google Flights lookup"])

        description = escape_ics_text("\n".join(desc_parts))
        uid = f"fli-{uuid.uuid4()}@alfred"

        cal_lines.append("BEGIN:VEVENT")
        cal_lines.append(f"UID:{uid}")
        cal_lines.append(f"DTSTAMP:{now_stamp}")

        if dep_tz:
            cal_lines.append(f"DTSTART;TZID={dep_tz}:{dt_to_ical(dep_time)}")
        else:
            cal_lines.append(f"DTSTART:{dt_to_ical(dep_time)}")

        if arr_tz:
            cal_lines.append(f"DTEND;TZID={arr_tz}:{dt_to_ical(arr_time)}")
        else:
            cal_lines.append(f"DTEND:{dt_to_ical(arr_time)}")

        cal_lines.append(f"SUMMARY:{escape_ics_text(summary)}")
        cal_lines.append(f"DESCRIPTION:{description}")
        cal_lines.append(f"LOCATION:{escape_ics_text(dep_name)}")
        if url:
            cal_lines.append(f"URL:{url}")
        cal_lines.append("TRANSP:OPAQUE")
        cal_lines.append("STATUS:CONFIRMED")
        cal_lines.append("END:VEVENT")

    cal_lines.append("END:VCALENDAR")
    return "\r\n".join(cal_lines) + "\r\n"


def main():
    if len(sys.argv) < 2:
        sys.exit(1)

    raw = sys.argv[1]
    try:
        data = json.loads(base64.b64decode(raw))
    except Exception:
        try:
            data = json.loads(raw)
        except Exception as e:
            subprocess.run([
                "osascript", "-e",
                f'display notification "Could not parse flight data: {e}" with title "Fli Flights"'
            ])
            sys.exit(1)

    legs = data.get("legs", [])
    if not legs:
        subprocess.run([
            "osascript", "-e",
            'display notification "No flight legs found" with title "Fli Flights"'
        ])
        sys.exit(1)

    price = data.get("price")
    currency = data.get("currency")
    url = data.get("url")
    others = data.get("others", [])

    unknown = []
    for leg in legs:
        for key in ("departure_airport", "arrival_airport"):
            code = leg.get(key, {}).get("code", "")
            if code and not tz_for_airport(code):
                unknown.append(code)

    ics_content = build_ics(legs, price, currency, url, others)

    ics_path = os.path.join(tempfile.gettempdir(), f"fli_flight_{uuid.uuid4().hex[:8]}.ics")
    with open(ics_path, "w", encoding="utf-8") as f:
        f.write(ics_content)

    subprocess.run(["open", ics_path])

    if unknown:
        codes = ", ".join(sorted(set(unknown)))
        subprocess.run([
            "osascript", "-e",
            f'display notification "Unknown timezone for: {codes} — times may need adjustment" '
            f'with title "Fli Flights"'
        ])


if __name__ == "__main__":
    main()
