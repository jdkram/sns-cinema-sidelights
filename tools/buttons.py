#!/usr/bin/env python3
# human-contributors: ["Jonny Kram"]
"""
buttons.py -- the sidelight controller in Python: five booth buttons -> five patterns.

Replaces the C++ `main` while the Mean Well PWM-40 is fitted (see session 006/007).
Patterns only use whole-wall changes, which that PSU can display. Every change is a
smooth crossfade (no flashes), so it is photosensitivity-safe.

    Button 1  shimmer     pre-show ambience, irregular drift
    Button 2  fadeout     off: fades down from whatever is showing, then off
    Button 3  breathe     slow regular pulse
    Button 4  full        house lights, 100% (the only silent state)
    Button 5  countdown5  film starting: 5 dimming breaths, then off

Run by systemd (config/systemd/sns-sidelights-py.service). Manual test, service stopped:
    python3 tools/buttons.py            # buttons live, Ctrl+C to quit
    python3 tools/buttons.py --press 3  # simulate button 3 at start

No packages needed: I2C via probe.py, buttons via the kernel's /sys/class/gpio.
Python 3.5 compatible (Raspbian Stretch).
"""

import math
import os
import random
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import probe  # noqa: E402

PWM_HZ = 1000          # MUST match the C++ (CLEDManager HERTZ). The chips power up at ~200 Hz.
FLOOR = 32.0           # lowest level that lights reliably at 1000 Hz (session 006: 25-30%)
FPS = 40.0
POLL_S = 0.01          # button poll interval (C++ loop also runs at 100 Hz)
DEBOUNCE = 3           # consecutive HIGH readings to count as a press (30 ms)
XFADE_S = 1.5          # crossfade between patterns
LEDS = range(1, 25)

# BCM pins for buttons 1-5, same as src/main.cpp (active-high, pull-downs).
BUTTON_PINS = [22, 27, 18, 4, 17]


def ease(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def uniform(level):
    return {n: level for n in LEDS}


# ------------------------------------------------------------------ patterns
# Each pattern is a generator taking the levels showing when it starts, and
# yielding a {led: level} dict per frame. When it returns, the last frame holds.

def p_full(start):
    yield uniform(100.0)


def p_breathe(start, period=8.0):
    t0 = time.time()
    while True:
        t = time.time() - t0
        x = (1 + math.cos(2 * math.pi * t / period)) / 2      # starts at the top
        yield uniform(FLOOR + (100 - FLOOR) * x)


def p_shimmer(start):
    # Per-panel drift. With the current PSU the wall reads as one irregular,
    # candle-like breath; after a PSU swap the panels will drift independently.
    cur = {n: random.uniform(60, 100) for n in LEDS}
    tgt = {n: random.uniform(55, 100) for n in LEDS}
    spd = {n: random.uniform(0.3, 1.0) for n in LEDS}
    while True:
        for n in LEDS:
            step = spd[n] * 30.0 / FPS
            if abs(tgt[n] - cur[n]) <= step:
                tgt[n] = random.uniform(55, 100)
                spd[n] = random.uniform(0.3, 1.0)
            cur[n] += step if tgt[n] > cur[n] else -step
        yield dict(cur)


def p_fadeout(start, full_s=10.0):
    """Fade every panel down from where it is now to the floor, then off."""
    top = max(start.values())
    if top <= FLOOR:
        yield uniform(0.0)
        return
    secs = max(2.0, full_s * (top - FLOOR) / (100 - FLOOR))
    t0 = time.time()
    while True:
        x = ease((time.time() - t0) / secs)
        yield {n: (start[n] - (start[n] - FLOOR) * x) if start[n] > FLOOR else 0.0
               for n in LEDS}
        if x >= 1.0:
            break
    time.sleep(0.5)
    yield uniform(0.0)


def p_countdown5(start, breaths=5, breath_s=7.0):
    """Five slow breaths, each peak dimmer than the last, then off."""
    low = FLOOR + 3
    t0 = time.time()
    while True:
        t = time.time() - t0
        if t >= breaths * breath_s:
            break
        i = min(int(t / breath_s), breaths - 1)
        phase = (t - i * breath_s) / breath_s
        peak = 100 - (100 - (low + 10)) * i / (breaths - 1)
        x = (1 + math.cos(2 * math.pi * phase)) / 2
        if i == breaths - 1 and phase > 0.5:
            x = 0.0
        yield uniform(low + (peak - low) * x)
    time.sleep(1.0)
    yield uniform(0.0)


BUTTONS = [
    ("shimmer", p_shimmer),
    ("fadeout", p_fadeout),
    ("breathe", p_breathe),
    ("full", p_full),
    ("countdown5", p_countdown5),
]

# Patterns that manage their own start (no crossfade needed).
NO_XFADE = {"fadeout"}


# ------------------------------------------------------------------ hardware

def read_levels(bus):
    """Read what the boards are currently showing, as {led: level 0-100} (active-low)."""
    levels = {}
    for n, (addr, ch) in probe.LED_MAP.items():
        base = probe.LED0_ON_L + 4 * ch
        on_l, on_h, off_l, off_h = [bus.read(addr, base + i) for i in range(4)]
        if off_h & 0x10:
            high = 0.0                       # full-off bit: pin LOW -> LED fully on
        elif on_h & 0x10:
            high = 1.0                       # full-on bit: pin HIGH -> LED off
        else:
            on, off = ((on_h & 0x0F) << 8) | on_l, ((off_h & 0x0F) << 8) | off_l
            high = ((off - on) % 4096) / 4096.0
        levels[n] = round(100.0 * (1.0 - high), 1)
    return levels


class Buttons:
    """Read the five booth buttons via /sys/class/gpio, with debounce and edge detection."""

    def __init__(self, pins):
        self.files, self.count, self.held = [], [], []
        for pin in pins:
            path = "/sys/class/gpio/gpio%d" % pin
            if not os.path.isdir(path):
                with open("/sys/class/gpio/export", "w") as f:
                    f.write(str(pin))
                time.sleep(0.2)                       # udev sets permissions
            with open(path + "/direction", "w") as f:
                f.write("in")
            self.files.append(open(path + "/value", "r"))
            self.count.append(0)
            self.held.append(False)

    def pressed(self):
        """Return the 0-based index of a newly pressed button, or None."""
        hit = None
        for i, f in enumerate(self.files):
            f.seek(0)
            if f.read(1) == "1":
                self.count[i] = min(self.count[i] + 1, DEBOUNCE)
            else:
                self.count[i] = 0
                self.held[i] = False
            if self.count[i] >= DEBOUNCE and not self.held[i]:
                self.held[i] = True
                hit = i
        return hit


# ------------------------------------------------------------------ main loop

def main():
    press_at_start = None
    if "--press" in sys.argv:
        press_at_start = int(sys.argv[sys.argv.index("--press") + 1]) - 1

    bus = probe.Bus()
    probe.set_frequency(bus, PWM_HZ)
    lights = probe.Lights(bus)
    shown = read_levels(bus)
    buttons = Buttons(BUTTON_PINS)

    def start(index, reason):
        name, fn = BUTTONS[index]
        print("%s -> %s" % (reason, name))
        sys.stdout.flush()
        return name, fn(dict(shown)), dict(shown), time.time()

    # At boot, come up as house lights (crossfaded from whatever the chips show).
    name, gen, xfrom, xt0 = start(3 if press_at_start is None else press_at_start,
                                  "start")
    target = dict(shown)
    next_frame = 0.0

    while True:
        b = buttons.pressed()
        if b is not None:
            name, gen, xfrom, xt0 = start(b, "button %d" % (b + 1))

        now = time.time()
        if now >= next_frame:
            next_frame = now + 1.0 / FPS
            if gen is not None:
                try:
                    target = next(gen)
                except StopIteration:
                    gen = None
            x = 1.0 if name in NO_XFADE else ease((now - xt0) / XFADE_S)
            frame = {n: xfrom[n] + (target[n] - xfrom[n]) * x for n in LEDS}
            if frame != shown:
                for n, level in frame.items():
                    lights.set(n, level)
                lights.show()
                shown = frame
        time.sleep(POLL_S)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped (lights hold their last state).")
