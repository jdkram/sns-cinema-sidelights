---
human-contributors: ["Jonny Kram"]
session-date: 2026-10-14
session-number: "006"
---

# Session 006: Establish what the hardware actually does

**Date:** 2026-10-14
**Location:** Star and Shadow Cinema
**Tester:** Jonny
**Commit on Pi before session:** (run `git -C /home/pi/sidelights rev-parse --short HEAD`)

---

## Why this session exists

The March sessions concluded that "the event engine can't drive single channels". A
re-read of the evidence in October 2026 says that conclusion was never supported:

- KnightRider already showed nothing on the untouched **2019 binary** (session 001), so
  the 2026 edits didn't cause it.
- The direct-write sweep (which bypasses the event engine) has only one recorded
  result: "LED 1 DEAD". The other 23 rows are blank. Later notes say both "works" and
  "nothing visible". Nobody knows.
- Ember isn't sparse: it drives all 24 LEDs at 12-55%. The 27% threshold alone explains it.
- The sweep and the all-on test send byte-identical I2C writes per channel. If one lights
  and the other doesn't, the cause is electrical (or a viewing problem), not software.

So today is about **facts, not fixes**. Every test uses `probe.py`, which talks to the
PCA9685 boards directly with no wiringPi and no C++. Nothing in it flashes faster than
one change every few seconds.

The two open questions:

1. **Does a single channel light on its own?** (Viewing distance, minimum load, or polarity?)
2. **Is the 27% floor a slow switching stage?** If so, the floor moves when the PWM
   frequency changes, and we can tune it away in software.

---

## Before leaving home

- [ ] Hotspot details sorted (see "Getting connected" below)
- [ ] Current `probe.py` on the laptop you are taking (it goes to the Pi by `scp`)
- [ ] Read [HARDWARE.md](../HARDWARE.md) "Signal path" and "Two explanations to test".
- [ ] Multimeter, if one's to hand, for test 6.

## Getting connected

The Pi only knows the hotspot it was set up with (profile name recorded as `sns_test`).
It won't find your new phone unless the new hotspot matches **exactly**:

- same network name (SSID), same password (case-sensitive)
- **2.4 GHz** band (Pi Zero W has no 5 GHz). On Pixels: Hotspot settings → "Extend
  compatibility" on, or pick 2.4 GHz.
- **WPA2-Personal** security, not WPA3 (Raspbian Stretch predates WPA3)

Where the password might be: the old phone's hotspot settings screen, your password
manager, or Nextcloud.

**If you can't find it:** you can still get in, but it needs the SD card (ladder). Put a
`wpa_supplicant.conf` file on the card's small `boot` partition (readable on any laptop),
and Raspbian Stretch copies it into place on the next boot, replacing the old one:

```
country=GB
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1

network={
    ssid="NEW_HOTSPOT_NAME"
    psk="NEW_HOTSPOT_PASSWORD"
}
```

Use a phone hotspot only. This card's operating system has had no security updates
since 2020, so it should not join the cinema network.

**Finding the Pi:** hotspot's connected-devices list (hostname `raspberrypi`), or from
the laptop on the same hotspot: `ping raspberrypi.local`.

---

## Phase 1: Connect and record the starting state

- [ ] `ssh pi@<pi-ip>`
- [ ] Record what's actually on the Pi (never recorded before):
  ```bash
  cd /home/pi/sidelights
  git rev-parse --short HEAD
  git status --short
  ```
- [ ] Stop the service: `sudo systemctl stop sns-sidelights.service`
- [ ] `i2cdetect -y 1`: expect `40`, `60` and `70` (0x70 is the chips' built-in
      "all-call" address, which is normal)
- [ ] Copy `probe.py` to the Pi from the laptop:
      `scp probe.py pi@<pi-ip>:/home/pi/sidelights/`
      **Do not `git pull` on this Pi.** The repository no longer contains the C++
      source, so a pull would delete it from the card and the old program could
      never be rebuilt there.
- [ ] `python3 probe.py info`: expect ~1017 Hz, sleep=False, totem-pole=True

**Notes:**

```

```

---

## Phase 2: The tests (in this order, about 30 minutes)

Stand where you can see **LEDs 1-6 up close** for tests 2-3. Ask what LED 1 actually is
on the wall: the first test that lights a single panel tells you.

For every result, write down **where you were standing and whether the house lights
were on**. "Nothing visible" without that has been useless before.

```
Standing:                         House lights:
```

### Test 1: Polarity

```bash
python3 probe.py polarity
```

Step 1 holds every output pin LOW for 6 s, step 2 holds them all HIGH for 6 s.

- [ ] Lights on during step 1 → active-low (C++ is right)
- [ ] Lights on during step 2 → active-high (C++ has been inverted all along; add
      `--active-high` to every command below)

```

```

### Test 2: How many LEDs need to be on before any light?

```bash
python3 probe.py count --hold 6
```

Lights LEDs 1-1, 1-2, 1-3, 1-6, 1-12, then 1-24 at 100%.

- [ ] A single LED is clearly visible → individual addressing works, and the old
      sweep result was a viewing problem
- [ ] Nothing until N LEDs are on → note N. That's a minimum-load or shared-supply
      fault inside the controller box, so it's electrical.

If a single LED was invisible, run it again with the other LEDs held at 20%. That's
below the visible floor, but it changes what the other channels are doing:

```bash
python3 probe.py count --hold 6 --base 20
```

- [ ] Single LED now visible → what the other channels are doing matters. That is
      explanation B in HARDWARE.md. Do test 6.

```
First visible at N =            with --base 20: N =
```

### Test 3: Sweep and holes

```bash
python3 probe.py sweep --hold 3     # one on, rest off
python3 probe.py holes --hold 3     # all on, one off
```

`holes` is the more robust test: a dark gap in a lit wall is easy to see from anywhere.
Fill in the physical position of each LED number as you go (the docs disagree on it).

```
LED -> physical position, and any dead:

```

### Test 4: Brightness floor at the current frequency

```bash
python3 probe.py ramp
```

Ctrl+C the moment you see light. Repeat once to check.

```
1000 Hz floor: ____ %
```

### Test 4b: Does the floor depend on how many panels are lit?

This separates "each panel has its own dark band" from "what the other
channels are doing matters". Ramp only six panels, then only one, watching them up close:

```bash
python3 probe.py ramp --leds 6
python3 probe.py ramp --leds 1
```

```
Floor with 6 panels: ____ %     with 1 panel: ____ %     (24 panels, from test 4: ____ %)
```

- [ ] Roughly the same each time → the dark band belongs to each panel. Test 5 says
      whether frequency moves it.
- [ ] Higher with fewer panels, or never visible → it is total load. Go to tests 5b and 6.

### Test 5: Does the floor move with frequency?

This is the "something downstream is too slow" theory, tested properly. If the switching
stage needs a fixed time to switch on (say ~270 µs), the floor in percent scales with the
frequency: about 27% at 1000 Hz, ~13% at 500 Hz, ~7% at 250 Hz.

```bash
python3 probe.py freq 500 && python3 probe.py ramp
python3 probe.py freq 250 && python3 probe.py ramp
python3 probe.py freq 120 && python3 probe.py ramp
```

At each frequency also run `python3 probe.py all 50` and look for visible flicker,
including through your phone camera (rolling bands). Ctrl+C to move on.

```
500 Hz floor: ____ %   flicker? ____
250 Hz floor: ____ %   flicker? ____
120 Hz floor: ____ %   flicker? ____
```

- [ ] Floor shrinks roughly in proportion → slow switching stage confirmed. Pick the
      lowest frequency without visible flicker or camera banding.
- [ ] Floor stays ~27% regardless → not a timing problem. Suspect the LED strips (old
      strips with failing resistors/LEDs) or the controller's supply. Go to test 6.

### Test 5b: Stagger (does it matter that every channel switches at once?)

Today every channel switches on at the same instant each cycle, so the controller sees all
24 strips' current arrive at once. `--stagger` spreads them across the cycle. Back at
1000 Hz:

```bash
python3 probe.py freq 1000
python3 probe.py ramp --stagger
python3 probe.py count --stagger --hold 6
```

```
1000 Hz floor with stagger: ____ %     single LED visible with stagger? ____
```

- [ ] Floor drops or single LEDs appear → something shared is struggling when every
      channel switches at once. Note it and do test 6.

### Test 6 (multimeter, optional): does the controller's supply sag?

DC volts across the two contacts of the controller box's round power socket (or the
plug feeding it):

```bash
python3 probe.py all 100      # read the meter, then Ctrl+C
python3 probe.py off          # read the meter again
python3 probe.py one 5 100    # and again
```

```
All on: ____ V      All off: ____ V      One on: ____ V
Label on the supply feeding that socket: ____ V  ____ A
```

- [ ] About the same each time: the controller's supply is fine.
- [ ] Clearly lower with panels off: explanation B in HARDWARE.md. Something inside the
      controller is overloading its supply whenever panels are held off.

### Look at one lightbox

- [ ] Is there a Mean Well driver in or behind it? One per box?
- [ ] Do its thin blue and white wires join the numbered phono lead?

```

```

---

## Phase 3: Restore

- [ ] `sudo systemctl start sns-sidelights.service` (the old program sets the frequency back to 1000 Hz)
- [ ] Press a couple of buttons to confirm normal behaviour

---

## Results summary

```
Polarity:
Single LED visible:
Floor vs frequency:
Physical map done:
Switching stage parts seen:
```

## What the results decide

See step 2 of [PLAN.md](../PLAN.md). Copy confirmed facts into [HARDWARE.md](../HARDWARE.md).
