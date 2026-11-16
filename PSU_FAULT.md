---
human-contributors: ["Jonny Kram"]
date: 2026-11-16
---

# Sidelights fault: probable power supply (summary for a circuits person)

Written to hand to whoever looks at the hardware next. It separates what we
**observed** from what we **think**. Test detail: `sessions/006-hardware-truth.md`
(Results). Context: `sessions/007-cinema-wifi-and-hardening.md`.

## System

Pi Zero W → I2C → 2× PCA9685 PWM boards (0x40 / 0x60, 12 channels used on each,
~1 kHz, totem-pole outputs). Outputs are **active-low** (pin LOW = panel on) →
**switching stage, not inspected** → 24 × 12 V LED strip panels, all fed from **one
Mean Well PWM-40-12** (12 V, 3.34 A, 40 W, DIM wires unconnected). See `HARDWARE.md`.

## Observed (2026-11-16, channels held fully on/off, no PWM, unless stated)

- **All 24 on:** very bright, silent.
- **20–23 on:** all lit panels dim *together* to "mid"; audible hum from the supply
  area (audible from the front rows, less so at row G).
- **≤ 19 on:** nothing lights at all, including any single channel on either board.
- Depends on **how many** channels are on, not **which** (left column off = right
  column off).
- **All 24 under PWM at ~1 kHz:** 50% ≈ 70% perceived; 30% dim; 25% dark.
  At ~250 Hz, 25% lights but stutters irregularly.
- Panels set to **different** PWM levels mostly dim together (the old "Ambient"
  pattern made panels drop in and out erratically).
- Both boards read back correctly and every channel switches as commanded.

## Not measured

No voltage readings. Switching stage unidentified. No scope.

## Working hypothesis

The PWM-40 can't hold its output at partial or chopped (PWM) load. It's an LED
driver whose own output is PWM-chopped for dimming, so it may never have suited a
second PWM stage downstream. Ageing (output capacitors / feedback loop; it's a
potted, sealed unit in a warm enclosure) may have made it worse.

**Not ruled out:** a shared element in the switching stage (common rail, ground
return, series part), or wiring/connector resistance.

## What would settle it

1. **DC voltage at the PSU output and at a panel**, with all 24 on vs 19 on (the Pi
   can hold either state on request; see below).
2. **Identify the switching stage** (MOSFETs / optocouplers / ULN-type driver) and how
   the panels are wired (e.g. common +12 V, low side switched?).
3. If the supply is the cause: replace it with a **constant-voltage 12 V supply** with
   headroom over the measured load (e.g. Mean Well LRS-75-12).

### Where to put the probes

The layout inside the box isn't documented here, so check the Nextcloud photos.

- **PSU output:** where the PWM-40's **red (V+)** and **black (V−)** output leads
  terminate (screw terminal, connector or board). Meter on DC volts; black probe on
  V−, red probe on V+. Healthy: steady ~12 V.
- **At a panel:** across the strip's + and − where it connects, while that panel
  should be on. Optionally strip + vs PSU V− to see cable losses.
- **Ripple hint:** the same points on AC volts. Near zero is healthy. A clear reading
  suggests ripple or chopping. Cheap meters are rough at these frequencies.

| Supply output when 19 on | Suggests |
|---|---|
| Steady ~12 V, panels still dark | Supply OK; look at the switching stage or wiring |
| Drops or wanders | Supply is the problem |
| Won't settle / jumps around | Supply cycling ("hiccup" / burst mode) |

**Safety:** 12 V side only. The other end of the PWM-40 is **mains** (brown/blue
wires, IEC inlet, the green PCB). The circuit must be live to measure, so use shrouded
probes and don't bridge adjacent terminals (3 A+ will spark). It's at height:
**two people, never alone.**

### Holding a test state from the Pi

```bash
ssh sns-sidelights
sudo systemctl stop sns-sidelights-py.service
cd ~/sidelights
python3 probe.py all 100                     # all 24 on (Ctrl+C; lights hold)
python3 -c "import probe as p; L=p.Lights(p.Bus()); L.set_all(100); [L.set(i,0) for i in range(1,6)]; L.show()"   # 19 on
sudo systemctl start sns-sidelights-py.service   # back to normal
```

## Glossary

- **PWM:** dimming by switching fully on/off fast. *Duty cycle* = % of each cycle on.
  30% at 1 kHz = on 0.3 ms, off 0.7 ms, 1000×/s.
- **PCA9685:** chip that generates 16 PWM signals itself. The Pi sets each duty cycle
  over **I2C** (a two-wire chip bus).
- **Active-low:** output LOW (0 V) = panel on. A transistor or optocoupler sits in
  between (a logic pin can't power a 12 V strip). That's the "switching stage".
- **CV supply vs LED driver:** a CV supply holds 12 V whatever the load, which is what
  you want when something downstream dims. The PWM-40 is an LED driver with
  built-in PWM dimming. Chopping its output again downstream can interfere (possibly
  the 250 Hz stutter).
- **Load / burst mode:** fewer panels = lighter load. Many switch-mode supplies
  misbehave at light load and cycle stop-start. The hum is the coils vibrating at
  audible rates.
- **Why "count, not which" matters:** a bad channel fails specific panels. Panels
  failing below a total, and all dimming together, point at something **shared**.
