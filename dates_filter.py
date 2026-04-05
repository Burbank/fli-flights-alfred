#!/usr/bin/env python3
"""Alfred Script Filter for fli dates (cheapest travel dates) search."""

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
    """Expand short dates after --from / --to flags."""
    out = []
    date_flags = {"--return", "-r", "--from", "--to"}
    expect_date = False
    for p in parts:
        if expect_date:
            out.append(expand_date(p))
            expect_date = False
        elif p in date_flags:
            out.append(p)
            expect_date = True
        else:
            out.append(p)
    return out


def usage_items():
    return {
        "items": [
            {
                "title": "Find Cheapest Dates: ORIGIN DEST [options]",
                "subtitle": "e.g. JFK LHR  |  --from 06-01 --to 07-01 --round --class BUSINESS",
                "valid": False,
                "icon": {"path": "icon.png"},
            }
        ]
    }


def error_item(title, subtitle=""):
    return {"items": [{"title": title, "subtitle": subtitle, "valid": False, "icon": {"path": "icon.png"}}]}


def weekday_name(date_str):
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").strftime("%a")
    except (ValueError, TypeError):
        return ""


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
    if len(positional) < 2:
        print(json.dumps(usage_items()))
        return

    parts = expand_dates_in_parts(parts)

    env = os.environ.copy()
    env["PATH"] = os.path.expanduser("~/.local/bin") + ":" + env.get("PATH", "")

    cmd = ["fli", "dates"] + parts + ["--format", "json", "--sort"]
    if "--format" in parts:
        cmd = ["fli", "dates"] + parts
        if "--sort" not in parts:
            cmd += ["--sort"]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, env=env)
    except subprocess.TimeoutExpired:
        print(json.dumps(error_item("Search timed out", "Try a smaller date range")))
        return
    except Exception as e:
        print(json.dumps(error_item("Error running fli", str(e)[:120])))
        return

    if result.returncode != 0:
        stderr = result.stderr.strip()
        msg = stderr.split("\n")[-1] if stderr else "Unknown error"
        print(json.dumps(error_item("Date search failed", msg[:120])))
        return

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        print(json.dumps(error_item("Could not parse results", result.stdout[:120])))
        return

    if not data.get("success") or not data.get("dates"):
        print(json.dumps(error_item("No dates found", "Try different airports or a wider date range")))
        return

    q = data.get("query", {})
    origin = q.get("origin", "")
    dest = q.get("destination", "")
    is_round = q.get("is_round_trip", False)
    trip_type = "Round-trip" if is_round else "One-way"

    dates = data["dates"]
    prices = [d["price"] for d in dates if d.get("price")]
    min_price = min(prices) if prices else None

    items = []
    for entry in dates[:30]:
        dep_date = entry.get("departure_date", "")
        ret_date = entry.get("return_date")
        price = entry.get("price")
        currency = entry.get("currency", "USD")

        if price is None:
            continue

        day_name = weekday_name(dep_date)
        is_cheapest = price == min_price

        price_str = f"{currency} {price:.0f}"
        if is_cheapest:
            price_str += "  ★ cheapest"

        title = f"{dep_date} ({day_name})  —  {price_str}"
        subtitle = f"{origin} → {dest}  ·  {trip_type}"
        if ret_date:
            ret_day = weekday_name(ret_date)
            subtitle += f"  ·  Return: {ret_date} ({ret_day})"

        gf_url = build_google_flights_url(origin, dest, dep_date, ret_date)
        clipboard_txt = f"{dep_date} ({day_name}): {currency} {price:.0f} — {origin}→{dest}"

        items.append(
            {
                "title": title,
                "subtitle": subtitle,
                "arg": gf_url,
                "mods": {
                    "cmd": {
                        "arg": clipboard_txt,
                        "subtitle": "⌘↵ Copy flight details to clipboard",
                    }
                },
                "text": {"copy": clipboard_txt, "largetype": clipboard_txt},
                "icon": {"path": "icon.png"},
                "valid": True,
            }
        )

    print(json.dumps({"items": items}))


if __name__ == "__main__":
    main()
