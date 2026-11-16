# human-contributors: ["Jonny Kram"]
"""
output.py -- send 24 brightness values to the two PCA9685 boards.

Uses the kernel's /dev/i2c-1 interface directly, so it needs no packages.
Each board gets one I2C write covering all 16 channels, and only when its
values have changed.

probe.py at the repo root talks to the boards the same way but is kept
separate and standalone on purpose, so it can run on any Pi with no setup.
"""

import os
import time

from . import config

MODE1, PRESCALE, LED0_ON_L = 0x00, 0xFE, 0x06
MODE1_SLEEP, MODE1_AUTO_INCREMENT, MODE1_RESTART = 0x10, 0x20, 0x80
I2C_SLAVE = 0x0703  # ioctl number from linux/i2c-dev.h

# Register bytes for one channel: ON_L, ON_H, OFF_L, OFF_H.
PIN_ALWAYS_HIGH = (0x00, 0x10, 0x00, 0x00)  # the chip's "full on" bit
PIN_ALWAYS_LOW = (0x00, 0x00, 0x00, 0x10)   # the chip's "full off" bit (power-on default)


def channel_registers(level: float) -> tuple[int, int, int, int]:
    """Register bytes that show `level` (0-100) on one channel."""
    level = max(0.0, min(100.0, level))
    floor = config.BRIGHTNESS_FLOOR
    if level > 0 and floor > 0:
        level = floor + level * (100.0 - floor) / 100.0

    lit = level / 100.0
    high = (1.0 - lit) if config.ACTIVE_LOW else lit
    ticks = int(round(high * 4096))  # how much of each PWM cycle the pin spends HIGH
    if ticks >= 4096:
        return PIN_ALWAYS_HIGH
    if ticks <= 0:
        return PIN_ALWAYS_LOW
    return (0x00, 0x00, ticks & 0xFF, ticks >> 8)


def board_frames(levels: list[float]) -> dict[int, bytes]:
    """Board address -> the 64 bytes for its 16 channels. levels[0] is LED 1."""
    frames = {}
    per_board = len(config.CHANNEL_ORDER)
    for board_index, address in enumerate(config.BOARDS):
        channels = [PIN_ALWAYS_LOW] * 16  # unwired channels keep the power-on default
        for i, channel in enumerate(config.CHANNEL_ORDER):
            channels[channel] = channel_registers(levels[board_index * per_board + i])
        frames[address] = bytes(b for registers in channels for b in registers)
    return frames


class Output:
    """
    show(levels) puts 24 brightness values on the wall.

    If the boards stop answering (loose connector, power blip), show() logs it
    once, then retries once a second and sets the boards up again when they
    come back, so the service never needs restarting by hand.
    """

    def __init__(self, dry_run: bool = False) -> None:
        self._dry_run = dry_run
        self._fd: int | None = None
        self._selected: int | None = None
        self._sent: dict[int, bytes] = {}
        self._retry_at = 0.0
        self._failing = False

    # --- raw I2C ---

    def _select(self, address: int) -> None:
        if address != self._selected:
            import fcntl  # Linux only; imported here so --dry-run works anywhere
            fcntl.ioctl(self._fd, I2C_SLAVE, address)
            self._selected = address

    def _write(self, address: int, register: int, data: bytes) -> None:
        self._select(address)
        os.write(self._fd, bytes([register]) + bytes(data))

    def _read(self, address: int, register: int) -> int:
        self._select(address)
        os.write(self._fd, bytes([register]))
        return os.read(self._fd, 1)[0]

    # --- setup ---

    def _connect(self) -> None:
        self._fd = os.open(config.I2C_BUS, os.O_RDWR)
        self._selected = None
        prescale = max(3, min(255, int(round(25000000.0 / (4096 * config.PWM_HZ))) - 1))
        dark = board_frames([0.0] * (len(config.BOARDS) * len(config.CHANNEL_ORDER)))

        for address in config.BOARDS:
            mode1 = (self._read(address, MODE1) & 0x7F) | MODE1_AUTO_INCREMENT
            self._write(address, MODE1, [mode1])
            # Go dark before the PWM clock starts, so a restart never flashes.
            self._write(address, LED0_ON_L, dark[address])
            if self._read(address, PRESCALE) != prescale:
                self._write(address, MODE1, [mode1 | MODE1_SLEEP])  # only writable asleep
                self._write(address, PRESCALE, [prescale])
            awake = mode1 & ~MODE1_SLEEP
            self._write(address, MODE1, [awake])
            time.sleep(0.001)  # oscillator settling time
            self._write(address, MODE1, [awake | MODE1_RESTART])

        self._sent = dict(dark)

    def _disconnect(self) -> None:
        if self._fd is not None:
            try:
                os.close(self._fd)
            except OSError:
                pass
        self._fd = None

    # --- frames ---

    def show(self, levels: list[float]) -> None:
        frames = board_frames(levels)
        if self._dry_run:
            self._sent = frames
            return

        try:
            if self._fd is None:
                if time.monotonic() < self._retry_at:
                    return
                self._connect()
            for address, frame in frames.items():
                if self._sent.get(address) != frame:
                    self._write(address, LED0_ON_L, frame)
                    self._sent[address] = frame
            if self._failing:
                print("I2C: boards are answering again", flush=True)
                self._failing = False
        except OSError as error:
            if not self._failing:
                print("I2C: cannot reach the PCA9685 boards (%s). Retrying every second." % error,
                      flush=True)
                self._failing = True
            self._disconnect()
            self._retry_at = time.monotonic() + 1.0
