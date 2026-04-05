#!/usr/bin/env python3
"""Alfred Script Filter for quick nonstop flight search (today / tomorrow).

Called with: nonstop_filter.py <day_offset> "<query>"
  day_offset: 0 = today, 1 = tomorrow
  query:      ORIGIN DEST [extra fli options]
"""

import base64
import json
import os
import shlex
import subprocess
import sys
from datetime import date, timedelta


def usage_items(label):
    return {
        "items": [
            {
                "title": f"Nonstop flights {label}: ORIGIN DEST",
                "subtitle": "e.g. BCN AMS  |  Extra options: --class BUSINESS --sort DURATION --time 6-20",
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


def build_google_flights_url(origin, dest, dep_date):
    return f"https://www.google.com/travel/flights?q=nonstop+flights+from+{origin}+to+{dest}+on+{dep_date}"


def main():
    day_offset = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    query = " ".join(sys.argv[2:]).strip() if len(sys.argv) > 2 else ""
    label = "today" if day_offset == 0 else "tomorrow"
    travel_date = (date.today() + timedelta(days=day_offset)).isoformat()

    if not query:
        print(json.dumps(usage_items(label)))
        return

    parts = shlex.split(query)
    positional = [p for p in parts if not p.startswith("-")]
    if len(positional) < 2:
        print(json.dumps(usage_items(label)))
        return

    origin = positional[0].upper()
    dest = positional[1].upper()

    env = os.environ.copy()
    env["PATH"] = os.path.expanduser("~/.local/bin") + ":" + env.get("PATH", "")

    cmd = ["fli", "flights"] + parts + [travel_date, "--stops", "NON_STOP", "--format", "json"]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, env=env)
    except subprocess.TimeoutExpired:
        print(json.dumps(error_item("Search timed out", "Try again")))
        return
    except Exception as e:
        print(json.dumps(error_item("Error running fli", str(e)[:120])))
        return

    if result.returncode != 0:
        stderr = result.stderr.strip()
        msg = stderr.split("\n")[-1] if stderr else "Unknown error"
        print(json.dumps(error_item(f"No nonstop flights {label}", msg[:120])))
        return

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        print(json.dumps(error_item("Could not parse results", result.stdout[:120])))
        return

    if not data.get("success") or not data.get("flights"):
        print(json.dumps(error_item(
            f"No nonstop flights {label} ({travel_date})",
            f"{origin} → {dest} — try a different date or remove the nonstop filter with 'flights'"
        )))
        return

    gf_url = build_google_flights_url(origin, dest, travel_date)

    all_flights = data["flights"][:25]

    def summarize(f):
        p = f.get("price", 0)
        cur = f.get("currency", "USD")
        d = f.get("duration", 0)
        fl = f.get("legs", [])
        names = []
        for lg in fl:
            an = lg.get("airline", {}).get("name", "")
            fn = lg.get("flight_number", "")
            names.append(f"{an} {fn}".strip())
        dt = format_time(fl[0].get("departure_time", "")) if fl else ""
        at = format_time(fl[-1].get("arrival_time", "")) if fl else ""
        time_t = f"{dt}-{at}" if dt and at else ""
        airline_t = ", ".join(names) if names else ""
        return f"{cur} {p:.0f} | {format_duration(d)} | Nonstop | {airline_t} {time_t}".strip()

    flight_summaries = [summarize(f) for f in all_flights]

    items = []
    for idx, flight in enumerate(all_flights):
        price = flight.get("price", 0)
        currency = flight.get("currency", "USD")
        duration = flight.get("duration", 0)
        legs = flight.get("legs", [])

        airlines = []
        for leg in legs:
            aname = leg.get("airline", {}).get("name", "")
            fnum = leg.get("flight_number", "")
            airlines.append(f"{aname} {fnum}".strip())

        dur_txt = format_duration(duration)
        airline_txt = " · ".join(airlines) if airlines else "—"

        dep_time = format_time(legs[0].get("departure_time", "")) if legs else ""
        arr_time = format_time(legs[-1].get("arrival_time", "")) if legs else ""
        time_txt = f"{dep_time}–{arr_time}" if dep_time and arr_time else ""

        title = f"{currency} {price:.0f}  ·  {dur_txt}  ·  Nonstop"
        subtitle = airline_txt
        if time_txt:
            subtitle += f"  ·  {time_txt}"

        clipboard_txt = f"{title}\n{subtitle}\n{origin}→{dest} {travel_date}"

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
