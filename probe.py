#!/usr/bin/env python3
# human-contributors: ["Jonny Kram"]
"""
probe.py -- talk to the two PCA9685 boards directly, with no wiringPi and no C++.

Purpose: settle what the hardware actually does before writing any more pattern
code. Every test here is slow (seconds per step), so nothing flashes.

Runs on the Pi's old Python (3.5, Raspbian Stretch) with no packages: it uses
the kernel's /dev/i2c-1 interface directly.

ALWAYS stop the C++ service first, or two programs fight over the I2C bus:
    sudo systemctl stop sns-sidelights.service

Usage (run on the Pi, from the repo folder):
    python3 probe.py info              # read chip settings, change nothing
    python3 probe.py off               # all channels off
    python3 probe.py all 100           # all 24 at 100% (Ctrl+C to stop)
    python3 probe.py one 5 100         # LED 5 at 100%, others off
    python3 probe.py polarity          # which raw pin state lights the LEDs?
    python3 probe.py count             # light 1, 2, 3, 6, 12, 24 LEDs in turn
    python3 probe.py sweep             # one LED at a time, others off
    python3 probe.py holes             # all on, one LED at a time switched OFF
    python3 probe.py ramp              # slow ramp; press Enter when you first see light
    python3 probe.py freq 200          # change PWM frequency (until power-cycle)

Options:
    --active-high   treat output HIGH as "LED on" (the C++ assumes active-low)
    --dry-run       print I2C writes instead of sending them (for testing off-Pi)
    --hold N        seconds per step for count/sweep/holes (default 4)
    --base N        level (%) for the "off" LEDs in one/count/sweep, e.g. 20 keeps
                    the power supply loaded while staying below the visible floor
    --stagger       spread channels' switch-on points across the PWM cycle,
                    so they don't all load the power supply at the same instant

LED numbering matches the C++ (src/CLEDManager.cpp): LED 1-12 on board 0x60,
13-24 on board 0x40, channels 2-7 then 13 down to 8 on each board.
"""

import argparse
import fcntl
import os
import subprocess
import sys
import time

I2C_BUS = "/dev/i2c-1"
I2C_SLAVE = 0x0703  # ioctl number from linux/i2c-dev.h

MODE1, MODE2, LED0_ON_L, PRESCALE = 0x00, 0x01, 0x06, 0xFE
MODE1_SLEEP, MODE1_AI, MODE1_RESTART = 0x10, 0x20, 0x80

BOARDS = (0x60, 0x40)


def build_led_map():
    """LED number (1-24) -> (board address, channel). Mirrors CLEDManager.cpp."""
    leds = {}
    n = 1
    for addr in BOARDS:
        for ch in list(range(2, 8)) + list(range(13, 7, -1)):
            leds[n] = (addr, ch)
            n += 1
    return leds


LED_MAP = build_led_map()


class Bus:
    """Minimal I2C access via /dev/i2c-1. One write = one I2C transaction."""

    def __init__(self, dry_run=False):
        self.dry_run = dry_run
        self.fd = None if dry_run else os.open(I2C_BUS, os.O_RDWR)
        self.current = None

    def _select(self, addr):
        if not self.dry_run and addr != self.current:
            fcntl.ioctl(self.fd, I2C_SLAVE, addr)
            self.current = addr

    def write(self, addr, reg, data):
        if self.dry_run:
            print("  i2c 0x%02x reg 0x%02x <- %s" % (addr, reg, " ".join("%02x" % b for b in data)))
            return
        self._select(addr)
        os.write(self.fd, bytes([reg] + list(data)))

    def read(self, addr, reg):
        if self.dry_run:
            return {MODE1: MODE1_AI, MODE2: 0x04, PRESCALE: 5}.get(reg, 0)
        self._select(addr)
        os.write(self.fd, bytes([reg]))
        return os.read(self.fd, 1)[0]


class Lights:
    """
    Holds a brightness (0-100) per LED and writes whole boards at once.

    Each board gets ONE I2C transaction per update (all 16 channels via
    auto-increment) instead of the C++ library's 2-6 transactions per LED.
    """

    def __init__(self, bus, active_high=False, stagger=False):
        self.bus = bus
        self.active_high = active_high
        self.stagger = stagger
        self.levels = {n: 0.0 for n in LED_MAP}
        for addr in BOARDS:
            mode1 = bus.read(addr, MODE1)
            # Auto-increment on, sleep off. Leave frequency as it is.
            bus.write(addr, MODE1, [(mode1 | MODE1_AI) & ~MODE1_SLEEP & 0x7F])

    def _registers(self, level, channel):
        """
        4 register bytes (ON_L, ON_H, OFF_L, OFF_H) for one channel.

        With stagger, each channel's pulse starts at a different point in the
        cycle, so the 24 strips don't all switch on at the same instant.
        """
        led_on_fraction = max(0.0, min(100.0, level)) / 100.0
        high_fraction = led_on_fraction if self.active_high else 1.0 - led_on_fraction
        ticks = int(round(high_fraction * 4096))
        if ticks >= 4096:
            return [0x00, 0x10, 0x00, 0x00]  # full-on bit: pin always HIGH
        if ticks <= 0:
            return [0x00, 0x00, 0x00, 0x10]  # full-off bit: pin always LOW
        on = (channel * 256) if self.stagger else 0
        off = (on + ticks) % 4096
        return [on & 0xFF, on >> 8, off & 0xFF, off >> 8]

    def set(self, led, level):
        self.levels[led] = level

    def set_all(self, level):
        for n in self.levels:
            self.levels[n] = level

    def show(self):
        for addr in BOARDS:
            regs = [[0x00, 0x00, 0x00, 0x10]] * 16  # unused channels: power-on default (full-off)
            for n, (a, ch) in LED_MAP.items():
                if a == addr:
                    regs[ch] = self._registers(self.levels[n], ch)
            self.bus.write(addr, LED0_ON_L, [b for r in regs for b in r])

    def raw_all(self, pin_high):
        """Force every used channel's pin permanently HIGH or LOW, ignoring polarity."""
        reg = [0x00, 0x10, 0x00, 0x00] if pin_high else [0x00, 0x00, 0x00, 0x10]
        for addr in BOARDS:
            regs = [[0x00, 0x00, 0x00, 0x10]] * 16
            for n, (a, ch) in LED_MAP.items():
                if a == addr:
                    regs[ch] = reg
            self.bus.write(addr, LED0_ON_L, [b for r in regs for b in r])


def set_frequency(bus, hz):
    prescale = int(round(25000000.0 / (4096 * hz))) - 1
    prescale = max(3, min(255, prescale))
    for addr in BOARDS:
        mode1 = bus.read(addr, MODE1) & 0x7F
        bus.write(addr, MODE1, [mode1 | MODE1_SLEEP])  # prescale only writable asleep
        bus.write(addr, PRESCALE, [prescale])
        bus.write(addr, MODE1, [mode1 & ~MODE1_SLEEP])
        time.sleep(0.001)
        bus.write(addr, MODE1, [(mode1 & ~MODE1_SLEEP) | MODE1_RESTART])
    print("PWM frequency now ~%.0f Hz (prescale %d). Lasts until power-cycle." % (
        25000000.0 / (4096 * (prescale + 1)), prescale))


def cmd_info(bus):
    for addr in BOARDS:
        m1, m2, pre = bus.read(addr, MODE1), bus.read(addr, MODE2), bus.read(addr, PRESCALE)
        print("Board 0x%02x: MODE1=0x%02x MODE2=0x%02x prescale=%d (~%.0f Hz)" % (
            addr, m1, m2, pre, 25000000.0 / (4096 * (pre + 1))))
        print("    sleep=%s auto-increment=%s  output-invert=%s  totem-pole=%s" % (
            bool(m1 & 0x10), bool(m1 & 0x20), bool(m2 & 0x10), bool(m2 & 0x04)))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("command")
    p.add_argument("args", nargs="*", type=float)
    p.add_argument("--active-high", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--hold", type=float, default=4.0)
    p.add_argument("--stagger", action="store_true")
    p.add_argument("--base", type=float, default=0.0)
    a = p.parse_args()

    if not a.dry_run and subprocess.call(
            ["systemctl", "is-active", "--quiet", "sns-sidelights.service"]) == 0:
        sys.exit("The sidelights service is running. Stop it first:\n"
                 "    sudo systemctl stop sns-sidelights.service")

    bus = Bus(dry_run=a.dry_run)
    if a.command == "info":
        cmd_info(bus)
        return
    if a.command == "freq":
        set_frequency(bus, a.args[0])
        return

    lights = Lights(bus, active_high=a.active_high, stagger=a.stagger)
    c = a.command

    try:
        if c == "off":
            lights.set_all(0)
            lights.show()

        elif c == "all":
            lights.set_all(a.args[0])
            lights.show()
            print("All LEDs at %g%%. Ctrl+C to stop (lights keep their last state)." % a.args[0])
            while True:
                time.sleep(1)

        elif c == "one":
            led, level = int(a.args[0]), a.args[1]
            lights.set_all(a.base)
            lights.set(led, level)
            lights.show()
            print("LED %d at %g%%, others at %g%%. Ctrl+C to stop." % (led, level, a.base))
            while True:
                time.sleep(1)

        elif c == "polarity":
            print("Step 1: every pin held permanently LOW for 6 s.")
            lights.raw_all(pin_high=False)
            time.sleep(6)
            print("Step 2: every pin held permanently HIGH for 6 s.")
            lights.raw_all(pin_high=True)
            time.sleep(6)
            print("Which step lit the LEDs? Step 1 = active-low (C++ assumption). "
                  "Step 2 = active-high (use --active-high).")

        elif c == "count":
            for n in (1, 2, 3, 6, 12, 24):
                lights.set_all(a.base)
                for led in range(1, n + 1):
                    lights.set(led, 100)
                lights.show()
                print("LEDs 1-%d at 100%%, rest off. Visible? (%gs)" % (n, a.hold))
                time.sleep(a.hold)

        elif c == "sweep":
            for led in range(1, 25):
                lights.set_all(a.base)
                lights.set(led, 100)
                lights.show()
                print("LED %2d on, others off" % led)
                time.sleep(a.hold)

        elif c == "holes":
            for led in range(1, 25):
                lights.set_all(100)
                lights.set(led, 0)
                lights.show()
                print("All on except LED %2d" % led)
                time.sleep(a.hold)

        elif c == "ramp":
            print("Ramping all LEDs up 1% every 0.5 s. Press Ctrl+C the moment you see light.")
            level = 0
            while level <= 100:
                lights.set_all(level)
                lights.show()
                sys.stdout.write("\r  level %3d%%" % level)
                sys.stdout.flush()
                time.sleep(0.5)
                level += 1
            print()

        else:
            sys.exit("Unknown command: %s (see python3 probe.py --help)" % c)

    except KeyboardInterrupt:
        print("\nStopped. Level when stopped is the last one printed.")


if __name__ == "__main__":
    main()
