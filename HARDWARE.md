---
human-authors: Jonny Kram
---

# Hardware Specifications: LED Driver

> **Known fault (2026-11-16):** this supply appears unable to drive a partial or PWM load. See [PSU_FAULT.md](PSU_FAULT.md).

The sidelight system uses a **Mean Well PWM-40-12** LED driver. This is an IP67-rated constant voltage power supply designed to provide a PWM (Pulse Width Modulation) style output, which is why it works well for the dimmable LED strips in the boxlights.

## Device Label Information

**Model:** Mean Well PWM-40-12  
**Type:** Class 2 Power Supply

### Specifications
- **Input:** 100-240V~ 0.6A 50/60Hz (277V~ for North America only: 0.25A 50/60Hz)
- **Output:** +12V…3.34A
- **IP Rating:** IP67 (Dust tight and waterproof)
- **Certifications:** SELV, CE, Double Insulated (Square-in-square symbol)

## Wiring Legend

| Wire | Function | Color | Notes |
|------|----------|-------|-------|
| **AC/L** | Live | BROWN | Connected to custom PCB |
| **AC/N** | Neutral | BLUE | Connected to custom PCB |
| **V+** | Positive Output | RED | To LED strips |
| **V-** | Negative Output | BLACK | To LED strips |
| **DIM+** | Dimming Control + | BLUE | Not connected (default 100%) |
| **DIM-** | Dimming Control - | WHITE | Not connected (default 100%) |

## Troubleshooting Notes

### Power and Connectivity
The AC input (Brown/Blue) is wired into a custom PCB with an IEC inlet. If the sidelights aren't firing up, check the solder joints or terminals on that green PCB first—they often take the most mechanical stress when the power leads are plugged and unplugged.

### Dimming Control
The DIM wires (Blue/White) appear to be tucked away or cut back. This model dims the output itself based on a signal to those wires, but if they are unconnected, it should just output at 100% brightness by default. In this installation, dimming is handled by the PCA9685 PWM controller downstream of the driver, so these wires are not needed.

---

## Signal Path: Button Press to Light

```text
PROJECTION BOOTH
┌─────────────────┐
│  Button panel   │
│  [1] [2] [3]    │
│     [4] [5]     │
└────────┬────────┘
         │ wired cable run
         ▼
CONTROLLER BOX
┌─────────────────────────────────────────┐
│  Raspberry Pi Zero                      │
│                                         │
│  GPIO pins (BCM numbering)              │
│  btn1=22  btn2=27  btn3=18              │
│  btn4=4   btn5=17                       │
│       │                                 │
│       ▼  (wiringPi, BCM mode)           │
│  CDigitalButton                         │
│  press/release detection + debounce     │
│       │                                 │
│       ▼  wasPressed() fires             │
│  CSequenceManager                       │
│  BUTTON_SEQUENCE_MAP[i] → seq number    │
│       │                                 │
│       ▼  100 Hz update loop             │
│  Sequence events                        │
│  FadeEvent / BrightnessSetEvent /       │
│  PulseEvent → brightness 0-100          │
│       │                                 │
│       ▼                                 │
│  CLEDManager                            │
│  onTime = 4095 − (brightness×4095/100)  │
│  active-low: HIGH=off, LOW=on           │
│       │                                 │
│       ▼  pwmWrite() via wiringPi        │
│  ┌─────────┐       ┌─────────┐         │
│  │PCA9685  │       │PCA9685  │         │
│  │0x40     │       │0x60     │         │
│  │LEDs 1-12│       │LEDs13-24│         │
│  └────┬────┘       └────┬────┘         │
│       │  I2C bus        │              │
│       │  at 1000 Hz PWM │              │
└───────┼─────────────────┼──────────────┘
        │ PWM signal      │ PWM signal
        ▼                 ▼
  [switching element — not fully documented
   in this repo; the active-low wiring in
   CLEDManager.cpp implies a MOSFET or
   transistor inverting the signal before
   the LED strips]
        │
        │ switched 12V
        ▼
┌────────────────────┐
│ Mean Well PWM-40-12│
│ AC mains → 12V DC  │
│ DIM wires unused:  │
│ constant full V    │
└────────┬───────────┘
         │ 12V DC rail
    ┌────┴────┐
    ▼         ▼
[LED strips in lightboxes — 24 channels
 total, 6 per box, 4 boxes]
```

### What this diagram clarifies

**The Mean Well does no dimming.** Its DIM wires are cut/unused so it just supplies a steady 12V rail. All brightness control is done entirely by the PCA9685 via 1kHz PWM.

**Active-low wiring.** `CLEDManager.cpp` (the `ledBrightnessSet` function) shows that `pwmWrite(0)` = LED fully on, `pwmWrite(4095)` = LED off. This is the opposite of what you'd expect from the PCA9685 datasheet directly. The inversion happens in a switching element (likely a MOSFET or transistor array) between the PCA9685 output pins and the LED strip. This element is not explicitly documented in the current hardware notes — worth mapping during a future session.

**I2C is the software-to-hardware boundary.** Everything above the PCA9685 is software; everything below is hardware. If `i2cdetect -y 1` shows both boards (0x40 and 0x60) but sequences don't behave correctly, the problem is almost certainly in the software or the wiringPi/pca9685 library layer, not in the LED strips or power supply.

**wiringPi dependency.** The pca9685 library bundled in this repo (`pca9685/src/pca9685.c`, written 2014) is a wiringPi devLib extension. It registers the PCA9685 channels as virtual GPIO pins via `wiringPiNewNode`. This means the system wiringPi version matters: wiringPi was deprecated by its author in 2019, and behaviour differences have been observed on newer Raspberry Pi OS versions. If the Pi was re-flashed with a post-2019 Raspbian/Pi OS, this is a potential source of subtle breakage even if I2C itself is working.
