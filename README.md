[![the-poster-for-a-place-that-i-2-20261121-0539](https://make.fun/badge/the-poster-for-a-place-that-i-2-20261121-0539.svg)](https://make.fun/bounty/the-poster-for-a-place-that-i-2-20261121-0539)
[![rank](https://make.fun/badge/the-poster-for-a-place-that-i-2-20261121-0539/Cervus121212/serene-crane-27/rank.svg)](https://make.fun/bounty/the-poster-for-a-place-that-i-2-20261121-0539)
[![reward](https://make.fun/badge/the-poster-for-a-place-that-i-2-20261121-0539/Cervus121212/serene-crane-27/reward.svg)](https://make.fun/bounty/the-poster-for-a-place-that-i-2-20261121-0539)

# VELMARA — Where the Water Climbs to the Sky

A travel poster for a place that does not exist: **VELMARA**, where a giant
waterfall flows *up* from the sea into the clouds at golden hour.

`main.py` (Python 3.13, standard library only) draws the whole 1024x1024
poster procedurally — sky gradient, sun with a warm halo half-hidden behind
a headland, the climbing waterfall, cliffs with pines, a sailboat for scale —
with a bitmap font written in the file. No network, no PIL. It writes
`entry.png` to `$MAKEFUN_OUTPUT_DIR` (falling back to the script's own
directory).

## What's on the poster

- **VELMARA** set huge in cream block letters with a dark outline, over an
  indigo → violet → amber golden-hour sky
- **The landmark:** one waterfall climbing from the teal sea into white
  clouds, foam at its base, wavy light streaks inside the column
- **The light:** a low pale sun, half behind a dark headland, its reflection
  streaking the sea; a small sailboat under it for scale
- **The place:** invented, specific, and impossible — water that climbs to
  the sky

## Run it

```sh
python3 main.py            # writes entry.png next to main.py
MAKEFUN_OUTPUT_DIR=/output python3 main.py   # writes entry.png there
```

The output is deterministic: two runs produce byte-identical PNGs
(1024x1024, well under the 1 MiB cap).
