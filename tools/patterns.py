#!/usr/bin/env python3
# human-contributors: ["Jonny Kram"]
"""
patterns.py -- prototype light patterns live on the wall, without rebuilding the C++.

Designed for the limits found in session 006 (2026-11-16), while the Mean Well PWM-40
is still fitted:
  - nothing lights unless at least 20 of 24 channels are on
  - nothing lights below ~30% PWM at 1017 Hz
  - only "all 24 at 100%" is silent and full brightness
So every pattern keeps >= 20 channels on and never goes below FLOOR (except "off").

Run on the Pi from the repo folder, with the service stopped:
    sudo systemctl stop sns-sidelights.service
    python3 tools/patterns.py breathe          # Ctrl+C to stop (lights hold last state)
    python3 tools/patterns.py list

Python 3.5 compatible (Raspbian Stretch): no f-strings.
"""

import math
import os
import random
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import probe  # noqa: E402

FLOOR = 32.0   # lowest level that reliably lights at 1017 Hz (floor measured 25-30%)
FPS = 40.0

# Physical columns, left to right. Confirmed: 1-4 far left, 21-24 far right.
# The middle four are a GUESS (consecutive groups of 4); a sweep will show the truth.
COLUMNS = [list(range(c * 4 + 1, c * 4 + 5)) for c in range(6)]


DEMO_SECONDS = None  # set by "demo" so endless patterns stop after a while


def run(frame_fn, lights, duration=None):
    """Call frame_fn(t) -> {led: level} every frame and show it."""
    if duration is None:
        duration = DEMO_SECONDS
    start = time.time()
    while duration is None or time.time() - start < duration:
        t = time.time() - start
        levels = frame_fn(t)
        for led, level in levels.items():
            lights.set(led, level)
        lights.show()
        time.sleep(1.0 / FPS)


def clamp(level):
    return max(FLOOR, min(100.0, level))


# ---------------------------------------------------------------- patterns

def full(lights):
    """All 24 at 100%. The only silent state. House lights up."""
    lights.set_all(100)
    lights.show()
    print("All 24 at 100%.")
    if DEMO_SECONDS:
        time.sleep(DEMO_SECONDS)


def breathe(lights, period=8.0):
    """Whole wall breathes slowly between FLOOR and 100%."""
    def frame(t):
        x = (1 - math.cos(2 * math.pi * t / period)) / 2  # 0..1, starts low
        level = FLOOR + (100 - FLOOR) * x
        return {n: level for n in range(1, 25)}
    run(frame, lights)


def shimmer(lights):
    """Every panel drifts independently between 55% and 100%, like slow candlelight."""
    targets = {n: random.uniform(55, 100) for n in range(1, 25)}
    current = dict(targets)
    speed = {n: random.uniform(0.3, 1.0) for n in range(1, 25)}

    def frame(t):
        for n in current:
            step = speed[n] * 30.0 / FPS
            if abs(targets[n] - current[n]) <= step:
                targets[n] = random.uniform(55, 100)
                speed[n] = random.uniform(0.3, 1.0)
            current[n] += step if targets[n] > current[n] else -step
        return {n: clamp(v) for n, v in current.items()}
    run(frame, lights)


def shadow(lights, step_s=0.7, gap_level=0.0):
    """One dark column sweeps left-right-left across a lit wall (keeps 20 on)."""
    order = list(range(6)) + list(range(4, 0, -1))  # 0..5..1, then repeats

    def frame(t):
        col = order[int(t / step_s) % len(order)]
        levels = {n: 100.0 for n in range(1, 25)}
        for n in COLUMNS[col]:
            levels[n] = gap_level
        return levels
    run(frame, lights)


def wave(lights, period=6.0):
    """A soft brightness wave rolls across the columns (all stay >= FLOOR)."""
    def frame(t):
        levels = {}
        for c, leds in enumerate(COLUMNS):
            x = (1 + math.sin(2 * math.pi * (t / period - c / 6.0))) / 2
            for n in leds:
                levels[n] = FLOOR + (100 - FLOOR) * x
        return levels
    run(frame, lights)


def fadeout(lights, seconds=10.0):
    """House lights down: 100% to FLOOR over `seconds`, then cut to off."""
    def frame(t):
        x = min(1.0, t / seconds)
        x = x * x * (3 - 2 * x)  # ease in/out
        level = 100 - (100 - FLOOR) * x
        return {n: level for n in range(1, 25)}
    run(frame, lights, duration=seconds)
    time.sleep(0.5)
    lights.set_all(0)
    lights.show()
    print("Faded out, now off.")


def countdown(lights, seconds=60.0, fade_s=2.5, glow=FLOOR):
    """Film countdown: columns fade to a glow one by one (left to right), then the wall fades out.

    Photosensitivity-safe: every change is a slow ease over `fade_s` seconds (>= 1 s),
    nothing flashes, and at most one column changes at a time. Each column stays at
    `glow` (never off), so >= 20 channels stay lit for the PSU.
    """
    beat = seconds / 7.0          # 6 column beats + 1 final fade-out beat
    ease = lambda x: x * x * (3 - 2 * x)

    def frame(t):
        levels = {}
        for c, leds in enumerate(COLUMNS):
            start = (c + 1) * beat - fade_s          # column c finishes fading at beat c+1
            x = ease(max(0.0, min(1.0, (t - start) / fade_s)))
            for n in leds:
                levels[n] = 100 - (100 - glow) * x
        return levels
    run(frame, lights, duration=6 * beat)
    # Final beat: the whole glowing wall eases down, then cuts to off at the floor.
    def final(t):
        x = ease(min(1.0, t / max(fade_s * 2, 1.0)))
        return {n: glow - (glow - FLOOR) * x for n in range(1, 25)}
    run(final, lights, duration=max(fade_s * 2, 1.0))
    time.sleep(beat - max(fade_s * 2, 1.0) if beat > fade_s * 2 else 0.5)
    lights.set_all(0)
    lights.show()
    print("Countdown finished: lights off.")


DEMO_ORDER = [("full", 8), ("breathe", 40), ("shimmer", 40), ("shadow", 40),
              ("wave", 40), ("countdown", None), ("fadeout", None)]


def demo(lights):
    """Loop through every pattern in a fixed order, logging start times to /tmp/patterns-demo.log."""
    global DEMO_SECONDS
    while True:
        for name, secs in DEMO_ORDER:
            with open("/tmp/patterns-demo.log", "a") as log:
                log.write("%s %s\n" % (time.strftime("%H:%M:%S"), name))
            print("%s  %s" % (time.strftime("%H:%M:%S"), name))
            DEMO_SECONDS = secs
            PATTERNS[name](lights)
            DEMO_SECONDS = None
        lights.set_all(0)
        lights.show()
        time.sleep(5)


def colmap(lights, hold=4.0):
    """Light every column EXCEPT one, stepping left to right, to map the middle columns."""
    for c in range(6):
        lights.set_all(100)
        for n in COLUMNS[c]:
            lights.set(n, 0)
        lights.show()
        print("Dark: LEDs %s (guessed column %d of 6)" % (COLUMNS[c], c + 1))
        time.sleep(hold)


PATTERNS = {
    "full": full, "breathe": breathe, "shimmer": shimmer, "shadow": shadow,
    "wave": wave, "fadeout": fadeout, "countdown": countdown, "colmap": colmap, "demo": demo,
}


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else "list"
    if name not in PATTERNS:
        for k, fn in sorted(PATTERNS.items()):
            print("%-8s %s" % (k, (fn.__doc__ or "").strip().splitlines()[0]))
        return
    lights = probe.Lights(probe.Bus())
    try:
        PATTERNS[name](lights)
    except KeyboardInterrupt:
        print("\nStopped (lights hold their last state).")


if __name__ == "__main__":
    main()
