#!/usr/bin/env python3
"""Alfred Script Filter for fli flights search."""

import base64
import json
import os
import re
import shlex
import subprocess
import sys
from datetime import date, datetime


def expand_date(s):
    """Turn MM-DD or M-D into YYYY-MM-DD (current year, or next year if past)."""
    if re.match(r"^\d{4}-\d{1,2}-\d{1,2}$", s):
        return s
    m = re.match(r"^(\d{1,2})-(\d{1,2})$", s)
    if m:
        month, day = int(m.group(1)), int(m.group(2))
        today = date.today()
        try:
            candidate = date(today.year, month, day)
        except ValueError:
            return s
        if candidate < today:
            candidate = date(today.year + 1, month, day)
        return candidate.isoformat()
    return s


def expand_dates_in_parts(parts):
    """Expand short dates in positional args and after --return / --from / --to."""
    out = []
    date_flags = {"--return", "-r", "--from", "--to"}
    expect_date = False
    positional_idx = 0
    for p in parts:
        if expect_date:
            out.append(expand_date(p))
            expect_date = False
        elif p in date_flags:
            out.append(p)
            expect_date = True
        elif not p.startswith("-"):
            positional_idx += 1
            # 3rd positional arg is the departure date
            out.append(expand_date(p) if positional_idx == 3 else p)
        else:
            out.append(p)
    return out


def usage_items():
    return {
        "items": [
            {
                "title": "Search Flights: ORIGIN DEST MM-DD",
                "subtitle": "e.g. JFK LHR 05-15  |  Options: --class BUSINESS --stops NON_STOP --sort DURATION",
                "valid": False,
                "icon": {"path": "icon.png"},
            }
        ]
    }


def error_item(title, subtitle=""):
    return {"items": [{"title": title, "subtitle": subtitle, "valid": False, "icon": {"path": "icon.png"}}]}


def format_duration(minutes):
    h, m = divmod(minutes, 60)
    return f"{h}h{m:02d}m"


def format_time(iso_str):
    if not iso_str or "T" not in iso_str:
        return ""
    return iso_str.split("T")[1][:5]


def build_google_flights_url(origin, dest, dep_date, ret_date=None):
    base = f"https://www.google.com/travel/flights?q=flights+from+{origin}+to+{dest}+on+{dep_date}"
    if ret_date:
        base += f"+returning+{ret_date}"
    return base


def main():
    query = " ".join(sys.argv[1:]).strip() if len(sys.argv) > 1 else ""

    if not query:
        print(json.dumps(usage_items()))
        return

    parts = shlex.split(query)
    positional = [p for p in parts if not p.startswith("-")]
    if len(positional) < 3:
        print(json.dumps(usage_items()))
        return

    parts = expand_dates_in_parts(parts)

    env = os.environ.copy()
    env["PATH"] = os.path.expanduser("~/.local/bin") + ":" + env.get("PATH", "")

    cmd = ["fli", "flights"] + parts + ["--format", "json"]
    if "--format" in parts:
        cmd = ["fli", "flights"] + parts

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, env=env)
    except subprocess.TimeoutExpired:
        print(json.dumps(error_item("Search timed out", "Try again or simplify your search")))
        return
    except Exception as e:
        print(json.dumps(error_item("Error running fli", str(e)[:120])))
        return

    if result.returncode != 0:
        stderr = result.stderr.strip()
        msg = stderr.split("\n")[-1] if stderr else "Unknown error"
        print(json.dumps(error_item("Flight search failed", msg[:120])))
        return

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        print(json.dumps(error_item("Could not parse results", result.stdout[:120])))
        return

    if not data.get("success") or not data.get("flights"):
        print(json.dumps(error_item("No flights found", "Try different airports, dates, or options")))
        return

    q = data.get("query", {})
    origin = q.get("origin", "")
    dest = q.get("destination", "")
    dep_date = q.get("departure_date", "")
    ret_date = q.get("return_date")
    gf_url = build_google_flights_url(origin, dest, dep_date, ret_date)

    all_flights = data["flights"][:25]

    def summarize(f):
        p = f.get("price", 0)
        cur = f.get("currency", "USD")
        d = f.get("duration", 0)
        s = f.get("stops", 0)
        fl = f.get("legs", [])
        names = []
        for lg in fl:
            an = lg.get("airline", {}).get("name", "")
            fn = lg.get("flight_number", "")
            names.append(f"{an} {fn}".strip())
        stops_t = "Nonstop" if s == 0 else f"{s} stop{'s' if s > 1 else ''}"
        dt = format_time(fl[0].get("departure_time", "")) if fl else ""
        at = format_time(fl[-1].get("arrival_time", "")) if fl else ""
        time_t = f"{dt}-{at}" if dt and at else ""
        airline_t = ", ".join(names) if names else ""
        return f"{cur} {p:.0f} | {format_duration(d)} | {stops_t} | {airline_t} {time_t}".strip()

    flight_summaries = [summarize(f) for f in all_flights]

    items = []
    for idx, flight in enumerate(all_flights):
        price = flight.get("price", 0)
        currency = flight.get("currency", "USD")
        duration = flight.get("duration", 0)
        stops = flight.get("stops", 0)
        legs = flight.get("legs", [])

        airlines = []
        segments = []
        for leg in legs:
            aname = leg.get("airline", {}).get("name", "")
            fnum = leg.get("flight_number", "")
            airlines.append(f"{aname} {fnum}".strip())
            dep_code = leg.get("departure_airport", {}).get("code", "")
            arr_code = leg.get("arrival_airport", {}).get("code", "")
            segments.append(f"{dep_code}→{arr_code}")

        stops_txt = "Nonstop" if stops == 0 else f"{stops} stop{'s' if stops > 1 else ''}"
        dur_txt = format_duration(duration)
        airline_txt = " · ".join(airlines) if airlines else "—"

        dep_time = format_time(legs[0].get("departure_time", "")) if legs else ""
        arr_time = format_time(legs[-1].get("arrival_time", "")) if legs else ""
        time_txt = f"{dep_time}–{arr_time}" if dep_time and arr_time else ""

        title = f"{currency} {price:.0f}  ·  {dur_txt}  ·  {stops_txt}"
        subtitle = airline_txt
        if time_txt:
            subtitle += f"  ·  {time_txt}"
        if len(segments) > 1:
            subtitle += f"  ({' → '.join(segments)})"

        clipboard_txt = f"{title}\n{subtitle}"

        others = [s for j, s in enumerate(flight_summaries) if j != idx]

        cal_data = base64.b64encode(json.dumps({
            "legs": flight.get("legs", []),
            "price": price,
            "currency": currency,
            "url": gf_url,
            "others": others,
        }).encode()).decode()

        items.append(
            {
                "title": title,
                "subtitle": subtitle,
                "arg": clipboard_txt,
                "mods": {
                    "cmd": {
                        "arg": gf_url,
                        "subtitle": "⌘↵ Open Google Flights in browser",
                    },
                    "cmd+shift": {
                        "arg": cal_data,
                        "subtitle": "⇧⌘↵ Add flight to Calendar (with timezones)",
                    },
                },
                "text": {"copy": clipboard_txt, "largetype": clipboard_txt},
                "icon": {"path": "icon.png"},
                "valid": True,
            }
        )

    count = data.get("count", len(items))
    if count > 25:
        items.append(
            {
                "title": f"… and {count - 25} more results",
                "subtitle": "⌘↵ Open Google Flights to see all",
                "arg": gf_url,
                "icon": {"path": "icon.png"},
                "valid": True,
            }
        )

    print(json.dumps({"items": items}))


if __name__ == "__main__":
    main()
