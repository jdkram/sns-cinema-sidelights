---
human-contributors: ["Jonny Kram"]
---

# Plan

One path, in order. Each step says what finishing it looks like. Update the status column as things happen.

| # | Step | Status |
|---|---|---|
| 1 | Measure what the hardware does | Not done. Checklist ready |
| 2 | Fix or compensate for what step 1 finds | Blocked on step 1 |
| 3 | New SD card running the Python controller | Software ready, untested on the lights |
| 4 | Remote access over the cinema Wi-Fi | Blocked on step 3 |
| 5 | Trigger from the IMS3000 | Needs answers (below) |
| 6 | New patterns | Open to anyone once step 3 is done |

## 1. Measure what the hardware does

Run [sessions/006-hardware-truth.md](sessions/006-hardware-truth.md) on the existing Pi. It uses `probe.py` only, changes nothing permanent, and takes about 30 minutes. Copy `probe.py` across with `scp`; do not `git pull` on the old card (see the warning in that checklist).

**Done when** the results summary at the bottom of that file is filled in.

## 2. Fix or compensate

What step 1 decides:

| Result | What to do |
|---|---|
| Dark band shrinks in proportion when the PWM frequency is lowered | Explanation A in [HARDWARE.md](HARDWARE.md). Set `PWM_HZ` in `sidelights/config.py` to the lowest value with no visible flicker |
| Nothing lights until several panels are on, or the voltage at the controller's power socket drops when panels are switched off | Explanation B. The fault is inside the controller box or in what powers it. Read the label of the supply on that socket, and get the transistor and resistor values, before changing anything |
| Dark band is the same for any number of panels and at any frequency | Set `BRIGHTNESS_FLOOR` in `sidelights/config.py` to the measured value |
| Lights come on when the pins are HIGH | Set `ACTIVE_LOW = False` in `sidelights/config.py` |

**Done when** a single panel can be seen fading smoothly from off to full, from the seats.

## 3. New SD card running the Python controller

Follow [SETUP.md](SETUP.md). The old card stays untouched as the way back.

Why a new card and not an upgrade: the current system is Raspbian Stretch from 2017. It has had no security updates since 2020, its Python is too old for the controller, and the C++ build depends on a library (wiringPi) that no longer exists for current systems.

What has been checked without hardware: the engine plays 18 of the 19 older preview sequences exactly as the simulator did (KnightRider was shortened on purpose), the bytes sent to the PCA9685 boards match `probe.py`, and startup, button debounce and recovery from an I2C failure behave against a simulated chip. What has not: anything on a real Pi. Expect small fixes on first run, most likely around the button inputs.

**Done when** all five booth buttons work from the new card and the lights survive a power cycle.

## 4. Remote access

Also in [SETUP.md](SETUP.md): the Pi joins the staff Wi-Fi with key-only SSH and is reached through the existing jump host. No extra software on the Pi, nothing exposed to the internet.

**Done when** a maintainer can restart the service and change a button mapping from home.

## 5. Trigger from the IMS3000

Goal: the projector's server changes the sidelights as part of a show playlist, so nobody has to press a button at the right moment.

Two ways to do it:

- **Contact closure (preferred if a spare output exists).** An IMS3000 general-purpose output wired across a booth button behaves exactly like someone pressing it. No network, no new software, nothing to secure.
- **Network cue.** The IMS3000 sends a short message to the Pi and the controller starts the named sequence. More flexible (any sequence, not five), but it needs a listener adding to the controller, a fixed address for the Pi, and care about what else on the network can reach it.

Not started, because it depends on:

- Does the cinema already use IMS3000 automation cues for anything?
- Is there a spare general-purpose output, and how far is the IMS3000 from the button box?
- Is the IMS3000 on the same network as the staff Wi-Fi?

**Done when** a test playlist changes the lights with nobody in the booth.

## 6. New patterns

See "Write a new pattern" in [README.md](README.md). Nineteen patterns already exist in the preview; five are on buttons.

## Open questions

Answers go into [HARDWARE.md](HARDWARE.md).

1. Does each lightbox have its own Mean Well driver, with the phono lead joined to its thin blue and white wires?
2. What is plugged into the controller's round power socket (label: volts and amps)?
3. Transistor marking and resistor colour bands in the controller box (photo of one row, close up).
4. Which box does each numbered phono lead feed?
5. What can the IMS3000 do: how many spare general-purpose outputs, and can a cue send a network message to an address?
6. Do the booth buttons have their own pull-down resistors?

Paul, who built it in 2018, is not readily reachable.
