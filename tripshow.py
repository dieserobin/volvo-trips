#!/usr/bin/env python3
"""
Volvo XC40 Trip Analyzer. Human-readable terminal summary.
Shows histogram bins with numeric ranges.

usage: python3 tripshow.py 2025-09.csv
disclaimer: vibe coded with gpt5 and 5-mini
"""
import sys, csv, re
from datetime import datetime
import statistics


# ---------- Helpers ----------
def parse_number(text):
    if not text:
        return None
    text = re.sub(r"[^\d,.\-]", "", text).replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def parse_duration(text, start, stop):
    if not text:
        try:
            a = datetime.fromisoformat(start.replace("Z", ""))
            b = datetime.fromisoformat(stop.replace("Z", ""))
            return max(0, (b - a).total_seconds() / 60)
        except Exception:
            return None
    t = text.strip().lower()
    if ":" in t:
        parts = [int(p) for p in t.split(":")]
        if len(parts) == 3:
            return parts[0] * 60 + parts[1] + parts[2] / 60
        if len(parts) == 2:
            return parts[0] + parts[1] / 60
    h = re.findall(r"(\d+)\s*h", t)
    m = re.findall(r"(\d+)\s*m", t)
    if h or m:
        hours = int(h[0]) if h else 0
        minutes = int(m[0]) if m else 0
        return hours * 60 + minutes
    if t.startswith("pt"):
        mm = re.match(r"pt(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?", t)
        if mm:
            h, m, s = (int(x) if x else 0 for x in mm.groups())
            return h * 60 + m + s / 60
    if t.isdigit():
        return float(t)
    return None


def format_minutes(total_minutes):
    if total_minutes is None:
        return "—"
    total_minutes = int(round(total_minutes))
    hours, minutes = divmod(total_minutes, 60)
    days, hours = divmod(hours, 24)
    if days:
        return f"{days} day{'s' if days>1 else ''}, {hours} h, {minutes} m"
    if hours:
        return f"{hours} hour{'s' if hours!=1 else ''}, {minutes} minute{'s' if minutes!=1 else ''}"
    return f"{minutes} minute{'s' if minutes!=1 else ''}"


# ---------- Histogram with bin ranges ----------
def print_histogram(values, tag, unit, bins=15, width=30):
    if not values:
        return
    vmin, vmax = min(values), max(values)
    rng = (vmax - vmin) or 1
    step = rng / bins
    counts = [0] * bins
    for v in values:
        i = int((v - vmin) / rng * bins)
        if i == bins:
            i -= 1
        counts[i] += 1
    peak = max(counts) or 1
    print(f"{tag} histogram ({unit})  —  scaled to {width}")
    for i, c in enumerate(counts):
        low = vmin + i * step
        high = low + step
        stars = int(round(c / peak * width))
        label = f"{low:.1f} – {high:.1f} {unit}"
        print(f"{label:<20} \t | {c:>3} | {'*'*stars}")
    print()


def print_hour_histogram(hours, width=40):
    """24-bin histogram showing counts per hour of day (0..23)."""
    if not hours:
        return
    counts = [0] * 24
    for h in hours:
        if 0 <= h < 24:
            counts[h] += 1
    peak = max(counts) or 1
    print("Usage by hour of day — scaled to", width)
    for h, c in enumerate(counts):
        stars = int(round(c / peak * width))
        label = f"{h:02d}:00–{(h+1)%24:02d}:00"
        print(f"{label:<11} \t\t | {c:>3} | {'*'*stars}")
    print()


# ---------- Main ----------
def main():
    if len(sys.argv) < 2:
        print("Usage: python3 trip_analyzer_bins.py trips.csv")
        sys.exit(1)
    path = sys.argv[1]

    distances, durations, fuels = [], [], []
    speeds = []
    hours = []
    with open(path, newline="", encoding="utf-16") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            d = parse_number(row.get("Distance (km)"))
            fu = parse_number(row.get("Fuel consumption (litres)"))
            du = parse_duration(
                row.get("Duration", ""), row.get("Started", ""), row.get("Stopped", "")
            )
            if d is not None:
                distances.append(d)
            if du is not None:
                durations.append(du)
            # collect per-trip speed in km/h when both distance and duration exist
            if d is not None and du is not None and du > 0:
                speeds.append(d / (du / 60.0))
            # collect start hour for usage-by-hour histogram
            started = row.get("Started")
            if started:
                try:
                    dt = datetime.fromisoformat(started.replace("Z", ""))
                    hours.append(dt.hour)
                except Exception:
                    pass
            if fu is not None:
                fuels.append(fu)

    if not distances:
        print("No usable trip rows found.")
        sys.exit(1)

    trips = len(distances)
    total_distance = sum(distances)
    total_duration = sum(durations) if durations else None
    total_fuel = sum(fuels) if fuels else None

    avg_distance = total_distance / trips
    avg_duration = (total_duration / trips) if durations else None
    avg_speed = (
        total_distance / ((total_duration or 1) / 60) if total_duration else None
    )
    fuel_per_100km = (total_fuel / total_distance * 100) if total_fuel else None

    # means and medians (per-trip)
    distance_mean = statistics.mean(distances) if distances else None
    distance_median = statistics.median(distances) if distances else None
    duration_mean = statistics.mean(durations) if durations else None
    duration_median = statistics.median(durations) if durations else None
    speed_mean = statistics.mean(speeds) if speeds else None
    speed_median = statistics.median(speeds) if speeds else None

    print("\n====================  TRIP SUMMARY  ====================")
    print(f"Total number of trips:              {trips}")
    print(f"Total distance driven:              {total_distance:.1f} km")
    print(f"Total driving time:                 {format_minutes(total_duration)}")
    if total_fuel is not None:
        print(f"Total fuel consumed:                {total_fuel:.2f} liters")
    if fuel_per_100km:
        print(f"Average fuel consumption:           {fuel_per_100km:.1f} liters/100km")
    print(f"Average distance per trip:")
    if distance_mean is not None and distance_median is not None:
        print(f"  Mean distance:                    {distance_mean:.1f} km")
        print(f"  Median distance:                  {distance_median:.1f} km")
    if avg_duration:
        print(f"Average trip duration:")
        if duration_mean is not None and duration_median is not None:
            print(f"  Mean duration:                    {duration_mean:.1f} minutes")
            print(f"  Median duration:                  {duration_median:.1f} minutes")
    if avg_speed:
        print(f"Average speed:")
    # print per-trip speed mean/median if available
    if speed_mean is not None and speed_median is not None:
        print(f"  Mean per-trip speed:              {speed_mean:.1f} km/h")
        print(f"  Median per-trip speed:            {speed_median:.1f} km/h")
    print("========================================================\n")

    print_histogram(distances, "Trip distance", "km", bins=50, width=50)
    if durations:
        print_histogram(durations, "Trip duration", "minutes", bins=10, width=50)
    # hourly usage histogram
    print_hour_histogram(hours, width=50)


if __name__ == "__main__":
    main()
