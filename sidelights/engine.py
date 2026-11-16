# human-contributors: ["Jonny Kram"]
"""
engine.py -- the sequence engine

A sequence is a list of timed events (fades, instant sets, pulses) scheduled
in its constructor. update() plays them back against a LEDManager, which just
holds 24 brightness values (0-100). The same engine drives the terminal
preview (preview.py) and the real lights (__main__.py), so what you preview
is what the wall gets.

Ported from the original 2018 C++ engine; the event semantics are unchanged.

Classes:
    LEDManager          Holds 24 LED brightness values (0-100).
    Sequence            Schedules and runs events against a LEDManager.
    FadeEvent           Smooth fade from current brightness to a target.
    BrightnessSetEvent  Instant brightness change at a given time.
    PulseEvent          Instant-on at start time, instant-off at end time.
"""

import random
import time
from abc import ABC, abstractmethod

NUM_LEDS = 24


# ---------------------------------------------------------------------------
# LED state store
# ---------------------------------------------------------------------------

class LEDManager:
    """Holds the current brightness (0-100) for each of the 24 LEDs."""

    def __init__(self) -> None:
        self._brightness: list[float] = [0.0] * NUM_LEDS

    def set(self, led: int, brightness: float) -> None:
        """Set LED brightness. led is 1-indexed."""
        if 1 <= led <= NUM_LEDS:
            self._brightness[led - 1] = max(0.0, min(100.0, brightness))

    def get(self, led: int) -> float:
        """Get LED brightness. led is 1-indexed."""
        if 1 <= led <= NUM_LEDS:
            return self._brightness[led - 1]
        return 0.0

    def state(self) -> list[float]:
        """Snapshot of all 24 LED brightness values (index 0 = LED 1)."""
        return list(self._brightness)

    def reset_all(self) -> None:
        self._brightness = [0.0] * NUM_LEDS


# ---------------------------------------------------------------------------
# Event base class
# ---------------------------------------------------------------------------

class Event(ABC):
    """
    Base for all scheduled events.

    Times are stored in milliseconds internally; the public API takes seconds.
    """

    def __init__(
        self,
        sequence: "Sequence",
        led: int,
        brightness: float,
        start_time_seconds: float,
        length_seconds: float = 0.0,
    ) -> None:
        self.sequence = sequence
        self.led = led
        self.target_brightness = float(brightness)
        self.start_time = start_time_seconds * 1000.0   # stored in ms
        self.end_time = (start_time_seconds + length_seconds) * 1000.0
        self.triggered = False

    def reset(self) -> None:
        self.triggered = False

    @property
    def done(self) -> bool:
        """True once further update() calls can no longer change anything."""
        return self.triggered

    @abstractmethod
    def update(self, elapsed_ms: float) -> None: ...


# ---------------------------------------------------------------------------
# Concrete event types
# ---------------------------------------------------------------------------

class FadeEvent(Event):
    """
    Smoothly fades from whatever brightness the LED is at when the event
    triggers, to target_brightness, over the event's time window.

    The "fade from current" behaviour avoids jarring jumps when one sequence hands off to another.
    """

    def __init__(
        self, sequence: "Sequence", led: int, brightness: float,
        start_time_seconds: float, length_seconds: float,
    ) -> None:
        super().__init__(sequence, led, brightness, start_time_seconds, length_seconds)
        self._initial_brightness = 0.0
        self._finished = False

    def reset(self) -> None:
        self._initial_brightness = 0.0
        self._finished = False
        super().reset()

    @property
    def done(self) -> bool:
        return self._finished

    def update(self, elapsed_ms: float) -> None:
        if elapsed_ms >= self.start_time and elapsed_ms < self.end_time:
            if not self.triggered:
                self._initial_brightness = self.sequence.led_brightness_get(self.led)
                self.sequence.channel_reserve(self, self.led)
                self.triggered = True

            time_diff = self.end_time - self.start_time
            if time_diff > 0:
                brightness_diff = self.target_brightness - self._initial_brightness
                change_per_ms = brightness_diff / time_diff
                event_elapsed = elapsed_ms - self.start_time
                new_brightness = self._initial_brightness + change_per_ms * event_elapsed
                self.sequence.led_brightness_set(self, self.led, new_brightness)

        if elapsed_ms > self.end_time and not self._finished:
            self._finished = True
            self.sequence.led_brightness_set(self, self.led, self.target_brightness)


class BrightnessSetEvent(Event):
    """
    Sets an LED to an exact brightness at a specific point in time.
    One-shot: fires once, never again until reset().
    """

    def __init__(
        self, sequence: "Sequence", led: int, brightness: float,
        start_time_seconds: float,
    ) -> None:
        super().__init__(sequence, led, brightness, start_time_seconds, 0.0)

    def update(self, elapsed_ms: float) -> None:
        if not self.triggered and elapsed_ms > self.start_time:
            self.sequence.channel_reserve(self, self.led)
            self.sequence.led_brightness_set(self, self.led, self.target_brightness)
            self.triggered = True


class PulseEvent(Event):
    """
    Jumps to target_brightness instantly at start_time, then drops to 0
    instantly at end_time. No fading -- it is a hard on/off pulse.

    The abrupt transitions are intentional; the calling sequence controls density and overlap to create
    the visual effect (e.g. a sparkle build-up).
    """

    def __init__(
        self, sequence: "Sequence", led: int, brightness: float,
        start_time_seconds: float, length_seconds: float,
    ) -> None:
        super().__init__(sequence, led, brightness, start_time_seconds, length_seconds)
        self._finished = False

    def reset(self) -> None:
        self._finished = False
        super().reset()

    @property
    def done(self) -> bool:
        return self._finished

    def update(self, elapsed_ms: float) -> None:
        if self._finished:
            return
        if not self.triggered and elapsed_ms > self.start_time:
            self.sequence.channel_reserve(self, self.led)
            self.sequence.led_brightness_set(self, self.led, self.target_brightness)
            self.triggered = True
        elif self.triggered and elapsed_ms > self.end_time:
            self.sequence.led_brightness_set(self, self.led, 0.0)
            self._finished = True


# ---------------------------------------------------------------------------
# Sequence
# ---------------------------------------------------------------------------

class Sequence:
    """
    Container for a set of scheduled events that play against a LEDManager.

    Usage:
        led_manager = LEDManager()
        seq = MySequence(led_manager)   # constructor schedules events
        seq.start()
        while True:
            seq.update()
            # read led_manager.state() to render the frame

    The channel reservation system (channel_reserve / led_brightness_set)
    ensures that when events overlap on the same LED, only the most recently
    reserved event can write.
    """

    def __init__(
        self,
        led_manager: LEDManager,
        loop: bool = False,
        length_seconds: float = 0.0,
    ) -> None:
        self._led_manager = led_manager
        self._loop = loop
        self._length_seconds = length_seconds
        self._events: list[Event] = []
        self._reserved: list[Event | None] = [None] * NUM_LEDS
        self._start_time_ms: float = 0.0
        self._running = False
        # Playback bookkeeping, rebuilt by start(). See update().
        self._by_start: list[tuple[float, int, Event]] = []
        self._next = 0
        self._active: list[tuple[int, Event]] = []

    # --- channel reservation ---

    def channel_reserve(self, event: Event, led: int) -> None:
        if 1 <= led <= NUM_LEDS:
            self._reserved[led - 1] = event

    def led_brightness_set(self, event: Event, led: int, brightness: float) -> None:
        if 1 <= led <= NUM_LEDS:
            if self._reserved[led - 1] is event:
                self._led_manager.set(led, brightness)

    def led_brightness_get(self, led: int) -> float:
        return self._led_manager.get(led)

    # --- event scheduling helpers ---

    def fade_event_add(self, led: int, brightness: int, start: float, length: float) -> None:
        self._events.append(FadeEvent(self, led, brightness, start, length))

    def fade_event_add_all_leds(self, brightness: int, start: float, length: float) -> None:
        for i in range(1, NUM_LEDS + 1):
            self.fade_event_add(i, brightness, start, length)

    def brightness_set_event_add(self, led: int, brightness: int, time_s: float) -> None:
        self._events.append(BrightnessSetEvent(self, led, brightness, time_s))

    def brightness_set_event_add_all_leds(self, brightness: int, time_s: float) -> None:
        for i in range(1, NUM_LEDS + 1):
            self.brightness_set_event_add(i, brightness, time_s)

    def pulse_event_add(self, led: int, brightness: int, time_s: float, length: float) -> None:
        self._events.append(PulseEvent(self, led, brightness, time_s, length))

    def pulse_event_add_all_leds(self, brightness: int, time_s: float, length: float) -> None:
        for i in range(1, NUM_LEDS + 1):
            self.pulse_event_add(i, brightness, time_s, length)

    # --- lifecycle ---

    def start(self) -> None:
        for event in self._events:
            event.reset()
        self._reserved = [None] * NUM_LEDS
        # (start time, scheduling order, event), earliest first.
        self._by_start = sorted(
            ((e.start_time, i, e) for i, e in enumerate(self._events)),
            key=lambda item: item[:2],
        )
        self._next = 0
        self._active = []
        self._start_time_ms = time.monotonic() * 1000.0
        self._running = True

    def update(self) -> None:
        """
        Advance playback to now.

        Only events that have started and are not yet done are visited, in
        the order they were scheduled. That gives the same result as visiting
        every event every frame (events outside that window do nothing), but
        a long sequence holds thousands of events and the Pi Zero cannot
        afford to walk them all 50 times a second.
        """
        if not self._running:
            return
        elapsed_ms = time.monotonic() * 1000.0 - self._start_time_ms

        added = False
        while self._next < len(self._by_start) and self._by_start[self._next][0] <= elapsed_ms:
            _, index, event = self._by_start[self._next]
            self._active.append((index, event))
            self._next += 1
            added = True
        if added:
            self._active.sort(key=lambda item: item[0])

        for _, event in self._active:
            event.update(elapsed_ms)
        self._active = [item for item in self._active if not item[1].done]

        length_ms = self._length_seconds * 1000.0
        if self._loop and length_ms > 0 and elapsed_ms > length_ms:
            self.start()

    def elapsed_seconds(self) -> float:
        if not self._running:
            return 0.0
        return (time.monotonic() * 1000.0 - self._start_time_ms) / 1000.0

    # --- utility shared with sequences ---

    @staticmethod
    def random_fraction() -> float:
        return random.random()
