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
- [ ] `probe.py` pushed to GitHub, so the cinema laptop and the Pi can pull it
- [ ] Look at the controller-box photos on Nextcloud. Note what sits between the PCA9685
      boards and the LED wires: optocouplers (small 4-pin white/black chips, often
      "PC817"), MOSFETs (3-legged black packages, often on a heatsink), a ULN2803 (an 18-pin
      chip) or something else. Photograph the part numbers if you open the box today.
- [ ] Multimeter, if one's to hand. Test 6 is the quickest way to convict or clear the
      power supply, which one outside opinion thinks is the root cause.

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
and Raspbian Stretch copies it into place on the next boot, replacing the old one. So the
file must list every network you want:

```
country=GB
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1

network={
    ssid="NEW_HOTSPOT_NAME"
    psk="NEW_HOTSPOT_PASSWORD"
    priority=10
}

network={
    ssid="CINEMA_STAFF_SSID"
    psk="CINEMA_STAFF_PASSWORD"
    priority=5
}
```

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
- [ ] Get `probe.py` on the Pi: `git pull` (or from the laptop:
      `scp probe.py pi@<pi-ip>:/home/pi/sidelights/`)
- [ ] `python3 probe.py info`: expect ~1017 Hz, sleep=False, totem-pole=True

**Notes:**

```

```

---

## Phase 2: The tests (in this order, about 30 minutes)

Stand where you can see **LEDs 1-6 up close** for tests 2-3. Ask what LED 1 actually is
on the wall: the first test that lights a single panel tells you.

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
      fault in the switching stage or PSU wiring, so it's electrical.

If a single LED was invisible, run it again with the other LEDs held at 20%. That's
below the visible floor, but it keeps the power supply loaded:

```bash
python3 probe.py count --hold 6 --base 20
```

- [ ] Single LED now visible → the supply needs a minimum load. Replacing it is the
      real fix. Until then, patterns can keep an invisible background level as a workaround.

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
      strips with failing resistors/LEDs) or the PSU. Go to test 6.

### Test 5b: Stagger (is the power supply choking on simultaneous switch-on?)

Today every channel switches on at the same instant each cycle, so the driver sees all
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

- [ ] Floor drops or single LEDs appear → the Mean Well is struggling with the load
      pattern. Points at the power supply (see test 6).

### Test 6 (multimeter, optional)

DC volts, across the 12 V output of the Mean Well (red/black):

```
All off: ____ V    python3 probe.py one 5 100: ____ V    all 100: ____ V    all 50: ____ V
```

How to read it:

- Steady ~12 V everywhere: the driver's fine. Look downstream.
- Collapses or jumps around with 0-1 LEDs on but steady with all 24: the driver's
  light-load behaviour has failed. That one fault explains both the floor and the
  single-LED failure.
- Sags with everything on, or the driver ticks/cycles: overloaded or ageing driver
  (rated 40 W total, about 1.7 W per panel).

Whichever way it reads, the cheap hardware fix is the same. The PWM-40 is a dimming LED
driver that chops its own output. A plain constant-voltage 12 V supply suits a design
where the PCA9685 does the dimming better: Mean Well LRS-75-12 or similar, about £20,
sized with headroom over the measured full load.

---

## Phase 2b (optional): Put the Pi on the cinema Wi-Fi

Worth doing if there's time. The UniFi AP in the cinema (June 2026) should reach the
controller box. With the Pi on the house network you can reach it remotely through Weebo
(`ssh -J sns-weebo-tailscale pi@<pi-ip>`), so no more hotspots and no Tailscale on the Pi.

**Low risk:** the hotspot entry stays in the config, so if the cinema Wi-Fi fails the Pi
falls back to the hotspot. Expect your SSH session to drop when it switches.

1. **Change the default password first** if it's still `raspberry`: `passwd`. Don't put
   a default-password Pi on a shared network.
2. In UniFi (unifi.ui.com), check the staff SSID you'll use (not a guest one, which
   isolates clients):
   - it's broadcast on **2.4 GHz** from the Cinema AP
   - its security is **WPA2**, or WPA2/WPA3 with PMF "optional", not WPA3-only
3. On the Pi:
   ```bash
   sudo cp /etc/wpa_supplicant/wpa_supplicant.conf ~/wpa_supplicant.conf.bak
   wpa_passphrase "CINEMA_SSID" | sudo tee -a /etc/wpa_supplicant/wpa_supplicant.conf
   # type the Wi-Fi password, press Enter
   sudo nano /etc/wpa_supplicant/wpa_supplicant.conf
   #   delete the "#psk=..." line (plain-text copy of the password)
   #   add  priority=5  inside the new block
   sudo wpa_cli -i wlan0 reconfigure
   ```
4. Turn off the phone hotspot. Within a minute the Pi should appear in UniFi's client
   list. Note its IP, then put the laptop on the same Wi-Fi and `ssh pi@<that-ip>`.
5. Give the Pi a fixed address: DHCP reservation on the BT Hub (it's the DHCP server).

```
Cinema Wi-Fi joined? ____   IP: ____   Reservation set? ____
```

---

## Phase 3: Restore

- [ ] `sudo systemctl start sns-sidelights.service` (the C++ resets the frequency to 1000 Hz)
- [ ] Press a couple of buttons to confirm normal behaviour

---

## Results summary

```
Polarity:                   active-low (C++ is correct)
Single LED visible:         NO. Nothing lights until 20 of 24 channels are on.
Floor vs frequency:         1017 Hz: floor between 25% and 30%. 254 Hz: 25% lights
                            but stutters violently (unusable).
Physical map done:          partial. LEDs 1-4 = far-left column, 21-24 = far-right column.
Switching stage parts seen: not inspected (needs access at height)
```

### Results (run 2026-11-16, remotely during session 007)

The tests were run turn by turn from KUSANAGI over SSH, with Jonny alone in the
auditorium reporting what he saw. Instead of `probe.py`'s timed commands, each state
was set with a one-liner (`import probe; Lights(...).show()`), which the PCA9685s then
hold until the next write. That avoided chat latency spoiling the timed tests.
Service stopped throughout. `probe.py info`: both boards ~1017 Hz, totem-pole, no
invert, awake.

| State (all at 1017 Hz unless noted) | What the wall did |
|---|---|
| All pins LOW (`raw_all`) | All lit, max brightness |
| All pins HIGH | All dark |
| LED 1 only, 100% | Dark |
| LED 5 only, 100% | Dark |
| LED 13 only, 100% (other board) | Dark |
| LEDs 1-6, 100% | Dark |
| LEDs 1-12, 100% (all of board 0x60) | Dark |
| All 24, 100% (`set_all`, control) | Very bright, **silent** |
| 23 on (LED 1 off) | LED 1 dark, **all others at mid brightness**, **audible hum** |
| 20 on (LEDs 1-4 off) | Rest at mid, hum about the same. LEDs 1-4 = far-left column |
| 20 on (LEDs 21-24 off) | Rest at mid. LEDs 21-24 = far-right column |
| 19 on (LEDs 1-5 off) | Whole wall dark |
| 18 on, 16 on | Whole wall dark |
| All 24 at 50% | Lit, ~70% of max, slight hum |
| All 24 at 30% | Lit, dim, hum maybe louder |
| All 24 at 25% | Dark |
| All 24 at 25%, **254 Hz** | Lit but stuttering violently ("epilepsy inducing"). Stopped at once |

**Diagnosis: the power supply (Mean Well PWM-40-12) can't drive a partial or switched load.**

- Every panel dims **together** when any channel is off, and a hum starts at
  anything less than full load. A constant-voltage supply in good order wouldn't care.
- There's a sharp cliff at **20 of 24** channels. It depends on how many are on, not
  which ones (the left or right column off gives the same result).
- This explains both long-standing symptoms. Single-LED and sparse patterns
  (KnightRider, sweeps, Ember) are below the cliff. Low PWM levels (the ~27% floor)
  are too.
- Lowering the PWM frequency moves the floor but causes violent stutter. That looks
  like the PWM-40's own output chopping clashing with ours, so frequency isn't a fix.
- The March conclusion ("the event engine can't drive single channels") is wrong.
  The software was never the main fault.

**Fix:** replace the PWM-40 (a dimming LED driver) with a plain constant-voltage
12 V supply, e.g. Mean Well LRS-75-12 (~£20), sized with headroom over the measured
full load. Mains work at height: a competent person, not alone. Before buying,
ideally confirm with a multimeter on the 12 V output: all 24 on vs 19 on.

**Working envelope until then (for pattern design):** ≥ 20 of 24 channels on, and
PWM level ≥ ~30%. Only all 24 at 100% is silent and full brightness. Any channel
off drops the whole wall to "mid".

## What the results decide

| Result | Next step |
|---|---|
| Single LEDs fine, floor tracks frequency | Software-only fix: lower frequency + rescale brightness. Python rewrite becomes the main project. |
| Single LEDs fine, floor fixed | Software rescale (map 1-100% onto floor-100%) works around it. Strips/PSU are a later hardware job. |
| Single LEDs need N others on | Electrical fault in the switching stage. Needs someone with EE skills and photos of the board before any pattern work. |
| Voltage unstable at light load, or stagger helps | Replace the Mean Well with a plain constant-voltage supply. Probably fixes both symptoms at once. |
| Polarity is active-high | The whole codebase has inverted brightness. Big but easy fix. |
