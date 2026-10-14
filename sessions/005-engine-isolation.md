---
human-authors: Jonny Kram
session-date: YYYY-MM-DD
session-number: "005"
---

# Session 005: Event engine isolation

**Date:** YYYY-MM-DD
**Location:** Star and Shadow Cinema
**Tester:** Jonny
**Commit on Pi before session:** (run `git -C /home/pi/sidelights rev-parse --short HEAD`)
**Commit on dev machine before session:** (run `git rev-parse --short HEAD`)

---

## Goal

Determine whether the single-channel output problem is hardware (electrical minimum load)
or software (event engine bug), then fix or work around it.

**What session 004 actually showed:**

| Test | Channels active | Result |
|---|---|---|
| DIAG all-on (13) | 24 simultaneously | All visible |
| DIAG fade (15) | 24 simultaneously, fading | Smooth, 27% threshold |
| DIAG half (16) | 24 simultaneously | Steady |
| DIAG sweep (14) | 1 at a time, others at 0 | Nothing visible from normal position |
| HeartBeat (seq 3) | 24 via engine | Works |
| Ambient (seq 1) | 24 via engine | Works (winking) |
| KnightRider (seq 5) | 1-3 via engine | Nothing |
| Ember (seq 6) | sparse via engine | Nothing |

**The pattern is all-channel vs single-channel** — not engine vs direct write. Both the
direct-write sweep and engine single-channel sequences appear to produce zero output.

**Two possible explanations:**

A) **Visibility.** One LED strip at 100% in a large cinema is 1/24 of the all-on brightness.
Unnoticeable from normal viewing distance unless you stand directly next to it. If this is it,
the hardware is fine and the software/engine bug is real but separate from the sweep result.

B) **Minimum-load electrical.** The LED circuit requires a minimum number of channels active
before any individual channel produces visible output. PSU stability, shared ground return,
or driver biasing could all cause this.

**The DIAG sweep close-up test distinguishes A from B immediately.**

Note: LED 1 is not confirmed dead. The DEAD entry from session 004 was recorded before it was
understood that all LED positions appeared dark during the sweep. Treat LED 1 as unknown.

**New in this deploy:**
- TestSingle (seq 12): single BrightnessSetEvent on LED 5 via event engine
- DIAG I2C timing (17): measures actual microseconds per pwmWrite call

---

## Phase 1: Connect, deploy, build

- [ ] SSH in: `ssh pi@<pi-ip>`
- [ ] `i2cdetect -y 1` -- confirm `0x40` and `0x60` visible
- [ ] Stop the service: `sudo systemctl stop sns-sidelights.service`
- [ ] Deploy new code:
  ```bash
  cd /home/pi/sidelights
  git pull
  rm CMakeCache.txt
  cmake .
  make -j2
  ```
- [ ] Confirm build succeeded with no errors

**Notes:**

```
[build output, any warnings]
```

---

## Phase 2: TestSingle — the critical first test

```bash
sudo ./main 12
```

Runs for 10 seconds. Watch LED 5 only (board 0x40, physically: left row 1, 5th LED from one end).
The terminal will print `TestSingle: will set LED 5 to 100%...` as confirmation it started.

- [ ] Did LED 5 light up?
- [ ] Did any other LEDs change? (They should not)
- [ ] Was LED 5 at full brightness (matching DIAG sweep output)?

**Result:**

```
[describe exactly what you saw]
```

### Decision tree

**If LED 5 lit up:** The engine CAN write to a single channel. The problem with KnightRider is
specific to FadeEvent or to its timing/overlap structure. Continue to Phase 3 (FadeEvent tests).

**If LED 5 did not light up:** The engine cannot do any single-channel write, even the simplest
possible event. Continue to Phase 2a (logging to find the drop point).

---

### Phase 2a: Add logging (only if TestSingle failed)

Skip this if TestSingle worked.

The channel reservation check in `CSequence::ledBrightnessSet` is the most likely drop point.
Add a one-line print to confirm whether the write is reaching the hardware layer:

On the dev machine:

```cpp
// In src/sequences/CSequence.cpp, find ledBrightnessSet():
void CSequence::ledBrightnessSet(CEvent *pEvent, int pLED, int pBrightness) {
    if (pLED - 1 < mReservedChannels.size()) {
        if (mReservedChannels[pLED - 1] && pEvent == mReservedChannels[pLED - 1]) {
            cout << "[engine] writing LED " << pLED << " brightness " << pBrightness << endl; // ADD THIS
            mLEDManager->ledBrightnessSet(pLED, pBrightness);
        }
    }
}
```

Commit, push, pull and rebuild on Pi, then run `sudo ./main 12` again. The terminal will either
show `[engine] writing LED 5...` confirming the write reached hardware, or show nothing,
confirming the channel reservation check is rejecting the write.

**If `[engine] writing LED 5` appears but the LED still doesn't light:** The engine write is
reaching the hardware layer. The problem is in CLEDManager or the I2C driver. Add a similar
print in `CLEDManager::ledBrightnessSet` to confirm.

**If nothing appears:** The channel reservation check is failing. The event is not reserving
its channel before trying to write, or the reservation is being cleared. Check
`CBrightnessSetEvent.cpp` -- specifically whether `channelReserve` is called before
`ledBrightnessSet` in `update()`.

**Result of logging run:**

```
[paste terminal output here]
```

---

## Phase 3: FadeEvent isolation (only if TestSingle passed)

Skip this phase if TestSingle failed -- fix the BrightnessSetEvent path first.

The question is now: does a single FadeEvent work? This uses `FadeEventAdd` rather than
`BrightnessSetEvent`, which adds interpolation and timing complexity.

A minimal test: start KnightRider (`./main 5`) but watch only LED 1. With STAGGER=1.0s and
FADE_TIME=1.5s, LED 1 should start fading up from t=0.01s and reach 100% by t=1.51s.

If the engine can do BrightnessSetEvent but not FadeEvent, we can add a proper FadeEvent
diagnostic sequence (similar to TestSingle but using fadeEventAdd). Do that on the dev machine,
push, and re-test.

```bash
sudo ./main 5
```

Watch only LED 1 for the first 10 seconds.

- [ ] Did LED 1 light up at all?
- [ ] Was there any gradual fade visible?

**Result:**

```
[describe what you saw]
```

---

## Phase 4: I2C timing probe

Run this regardless of TestSingle outcome -- the data is useful either way.

```bash
sudo ./main 17
```

Takes ~30 seconds. No visual output (brief flash then off).

- [ ] Single LED write avg: _____ us
- [ ] 24-LED round: _____ us

**Result:**

```
[paste full output]
```

**Interpretation:**
- < 500 us per LED (< 12 ms per 24-LED round): I2C speed is not the issue
- 500 us – 2 ms per LED: I2C is slow but the update loop still runs; marginal
- \> 2 ms per LED: the 10ms usleep in `update()` is irrelevant -- I2C is the actual frame limiter

---

## Phase 5: AmbientHigh verification

AmbientHigh was updated in session 004: MIN_BRIGHTNESS lowered from 55% to 30%
(just above the 27% threshold). The intent: each LED now has visible contrast when
it fades to its minimum, making the independent per-LED animation actually visible.

```bash
sudo ./main 8
# or press button 5
```

Watch for 30+ seconds (takes a few 2-second fade cycles to become apparent).

- [ ] Are individual panels moving at different rates/times? Or all together?
- [ ] Is there visible brightness contrast between panels (some brighter, some dimmer)?
- [ ] Compare with Ambient (button 1): is AmbientHigh's variation more obvious?

**Result:**

```
[describe what you saw]
```

---

## Phase 6: Complete LED sweep map

Only LED 1 was noted in session 004. Run the full sweep and complete the map.

```bash
sudo ./main 14
```

Fill in as sweep runs. Mark each LED: OK / DIM / FLICKER / DEAD

| LED | Board | Physical position | Status |
|-----|-------|-------------------|--------|
| 1   | 0x40  | Left row 1, #1    | unknown (sweep inconclusive - see goal) |
| 2   | 0x40  | Left row 1, #2    |        |
| 3   | 0x40  | Left row 1, #3    |        |
| 4   | 0x40  | Left row 1, #4    |        |
| 5   | 0x40  | Left row 1, #5    |        |
| 6   | 0x40  | Left row 1, #6    |        |
| 7   | 0x40  | Right row 1, #1   |        |
| 8   | 0x40  | Right row 1, #2   |        |
| 9   | 0x40  | Right row 1, #3   |        |
| 10  | 0x40  | Right row 1, #4   |        |
| 11  | 0x40  | Right row 1, #5   |        |
| 12  | 0x40  | Right row 1, #6   |        |
| 13  | 0x60  | Left row 2, #1    |        |
| 14  | 0x60  | Left row 2, #2    |        |
| 15  | 0x60  | Left row 2, #3    |        |
| 16  | 0x60  | Left row 2, #4    |        |
| 17  | 0x60  | Left row 2, #5    |        |
| 18  | 0x60  | Left row 2, #6    |        |
| 19  | 0x60  | Right row 2, #1   |        |
| 20  | 0x60  | Right row 2, #2   |        |
| 21  | 0x60  | Right row 2, #3   |        |
| 22  | 0x60  | Right row 2, #4   |        |
| 23  | 0x60  | Right row 2, #5   |        |
| 24  | 0x60  | Right row 2, #6   |        |

**Notes on any failures:**

```
[describe any dead/dim/flickering LEDs]
```

---

## Phase 7: Physical inspection (needs two people + ladder)

From session 004: LED 1 (Left row 1, #1) is confirmed dead. Physical access
requires a ladder and is safer with a second person.

If two people are present:

- [ ] Run `sudo ./main 13` (all-on) while physically inspecting
- [ ] Wiggle connectors at PCA9685 board 0x40 -- does LED 1 flicker on?
  (If so: cold solder joint or loose connector, not a dead LED)
- [ ] Visually inspect solder joints on board 0x40, especially the screw terminals
- [ ] Look for visible corrosion on connectors to Left row 1

**Inspection notes:**

```
[anything found]
```

---

## Sign-off

- [ ] TestSingle result recorded (Phase 2)
- [ ] I2C timing recorded (Phase 4)
- [ ] AmbientHigh assessment recorded (Phase 5)
- [ ] LED sweep map completed or updated (Phase 6)
- [ ] Service restarted: `sudo systemctl start sns-sidelights.service`
- [ ] Service healthy: `sudo systemctl status sns-sidelights.service`
- [ ] Lights in reasonable state for cinema use

**End commit on Pi:** (run `git -C /home/pi/sidelights rev-parse --short HEAD`)

**Overall result:** PASS / FAIL / PARTIAL

**TestSingle outcome (circle one):**

```
[ ] LED 5 lit up  →  engine can write single channels; FadeEvent or KnightRider-specific issue
[ ] LED 5 dark    →  engine cannot write single channels; channel reservation or deeper bug
```

**What to carry forward to next session:**

```
[based on results]
```
