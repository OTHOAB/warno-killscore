# creates adjusted feed with recent kills

import csv
from bisect import bisect_right
from pathlib import Path


# ---- settings ----
WINDOW_SECONDS = 10   # "recent" = kills within the last n seconds
EMPTY = 0             # value for rows where the side did not increase (use "" for blank)
SRC = Path("/home/killfeed/feed.csv") # replace with your path
DST = SRC.with_name("feed_adjusted.csv")
# ------------------

def to_sec(ts):
    h, m, s = map(int, ts.split(":"))
    return h * 3600 + m * 60 + s

with open(SRC, newline="") as f:
    rows = list(csv.DictReader(f, delimiter=";"))

times = [to_sec(r["ts"]) for r in rows]
red = [int(r["red"]) for r in rows]
blue = [int(r["blue"]) for r in rows]

def recent(values, i):
    """Cumsum now minus cumsum as it stood WINDOW_SECONDS ago."""
    cutoff = times[i] - WINDOW_SECONDS
    j = bisect_right(times, cutoff) - 1   # last row at or before the cutoff
    past = values[j] if j >= 0 else 0
    return values[i] - past

for i, r in enumerate(rows):
    increased_red = i > 0 and red[i] > red[i - 1]
    increased_blue = i > 0 and blue[i] > blue[i - 1]
    r["redrecent"] = recent(red, i) if increased_red else EMPTY
    r["bluerecent"] = recent(blue, i) if increased_blue else EMPTY

with open(DST, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["ts", "blue", "red", "bluerecent", "redrecent"], delimiter=";")
    w.writeheader()
    w.writerows(rows)

print(f"Wrote {DST}")
