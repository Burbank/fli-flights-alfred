#!/usr/bin/env python3
"""Alfred Script Filter showing the Fli Flights workflow guide."""

import json
import sys

GUIDE = [
    {
        "title": "━━  flights  ━━  Search flights on a specific date",
        "subtitle": "↵ copies  |  ⌘↵ Google Flights  |  ⇧⌘↵ add to Calendar",
        "valid": False,
    },
    {
        "title": "flights JFK LHR 05-15",
        "subtitle": "One-way economy, cheapest first. Year is auto-filled.",
        "arg": "flights JFK LHR 05-15",
        "valid": True,
    },
    {
        "title": "flights JFK LHR 05-15 --return 05-22",
        "subtitle": "Round-trip.  -r is short for --return",
        "arg": "flights JFK LHR 05-15 --return 05-22",
        "valid": True,
    },
    {
        "title": "flights JFK LHR 05-15 --class BUSINESS",
        "subtitle": "Cabin: ECONOMY (default) | PREMIUM_ECONOMY | BUSINESS | FIRST",
        "arg": "flights JFK LHR 05-15 --class BUSINESS",
        "valid": True,
    },
    {
        "title": "flights JFK LHR 05-15 --stops NON_STOP",
        "subtitle": "Stops: ANY (default) | NON_STOP | ONE_STOP",
        "arg": "flights JFK LHR 05-15 --stops NON_STOP",
        "valid": True,
    },
    {
        "title": "flights JFK LHR 05-15 --sort DURATION",
        "subtitle": "Sort: CHEAPEST (default) | DURATION | DEPARTURE_TIME | ARRIVAL_TIME",
        "arg": "flights JFK LHR 05-15 --sort DURATION",
        "valid": True,
    },
    {
        "title": "flights JFK LHR 05-15 --time 6-20",
        "subtitle": "Departure window: 6 AM – 8 PM (24h format)",
        "arg": "flights JFK LHR 05-15 --time 6-20",
        "valid": True,
    },
    {
        "title": "flights JFK LHR 05-15 --airlines BA AA",
        "subtitle": "Filter by airline IATA codes",
        "arg": "flights JFK LHR 05-15 --airlines BA AA",
        "valid": True,
    },
    {
        "title": "━━  nsflt  ━━  Nonstop flights today",
        "subtitle": "↵ copies  |  ⌘↵ Google Flights  |  ⇧⌘↵ add to Calendar",
        "valid": False,
    },
    {
        "title": "nsflt BCN AMS",
        "subtitle": "All nonstop flights from Barcelona to Amsterdam today",
        "arg": "nsflt BCN AMS",
        "valid": True,
    },
    {
        "title": "nsflt JFK LAX --class BUSINESS",
        "subtitle": "Nonstop business class today. Extra options: --sort, --time, --airlines",
        "arg": "nsflt JFK LAX --class BUSINESS",
        "valid": True,
    },
    {
        "title": "━━  nstom  ━━  Nonstop flights tomorrow",
        "subtitle": "↵ copies  |  ⌘↵ Google Flights  |  ⇧⌘↵ add to Calendar",
        "valid": False,
    },
    {
        "title": "nstom BCN AMS",
        "subtitle": "All nonstop flights from Barcelona to Amsterdam tomorrow",
        "arg": "nstom BCN AMS",
        "valid": True,
    },
    {
        "title": "nstom SFO NRT --sort DURATION",
        "subtitle": "Nonstop tomorrow sorted by shortest. Extra options: --class, --time, --airlines",
        "arg": "nstom SFO NRT --sort DURATION",
        "valid": True,
    },
    {
        "title": "━━  flydates  ━━  Find the cheapest travel dates",
        "subtitle": "↵ opens Google Flights  |  ⌘↵ copies details",
        "valid": False,
    },
    {
        "title": "flydates JFK LHR",
        "subtitle": "Cheapest one-way dates over the next ~60 days",
        "arg": "flydates JFK LHR",
        "valid": True,
    },
    {
        "title": "flydates JFK LHR --from 06-01 --to 07-01",
        "subtitle": "Specific date range. Year auto-filled from MM-DD.",
        "arg": "flydates JFK LHR --from 06-01 --to 07-01",
        "valid": True,
    },
    {
        "title": "flydates JFK LHR --round --duration 7",
        "subtitle": "Round-trip, 7-day trips.  -R = --round, -d = --duration",
        "arg": "flydates JFK LHR --round --duration 7",
        "valid": True,
    },
    {
        "title": "flydates JFK LHR --friday --saturday",
        "subtitle": "Day filters: --monday … --sunday  (combine any)",
        "arg": "flydates JFK LHR --friday --saturday",
        "valid": True,
    },
    {
        "title": "flydates JFK LHR --class BUSINESS --stops NON_STOP",
        "subtitle": "Same cabin / stops filters as flights",
        "arg": "flydates JFK LHR --class BUSINESS --stops NON_STOP",
        "valid": True,
    },
    {
        "title": "━━  Date Shortcuts  ━━",
        "subtitle": "No need to type the year — just use MM-DD",
        "valid": False,
    },
    {
        "title": "05-15 → auto-expands to 2026-05-15",
        "subtitle": "If the date has passed this year, it rolls to next year",
        "valid": False,
    },
]


def main():
    query = " ".join(sys.argv[1:]).strip().lower() if len(sys.argv) > 1 else ""

    items = []
    for entry in GUIDE:
        if query and query not in entry["title"].lower() and query not in entry.get("subtitle", "").lower():
            continue
        item = {
            "title": entry["title"],
            "subtitle": entry.get("subtitle", ""),
            "valid": entry.get("valid", False),
            "icon": {"path": "icon.png"},
        }
        if entry.get("arg"):
            item["arg"] = entry["arg"]
            item["text"] = {"copy": entry["arg"]}
        items.append(item)

    if not items:
        items = [{"title": "No matching help items", "subtitle": f"Searched for: {query}", "valid": False, "icon": {"path": "icon.png"}}]

    print(json.dumps({"items": items}))


if __name__ == "__main__":
    main()
