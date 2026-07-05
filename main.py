"""
Raspberry Pi Pico firmware (MicroPython) for the Driver Monitor System.

Listens on the default USB serial connection for single-character status
codes sent by the PC-side OpenCV script:

    'A'  -> AWAKE      (green LED on)
    'H'  -> HEAD DOWN  (yellow LED on + warning tone)
    'D'  -> DROWSY     (red LED on + alarm tone)

Any other byte is ignored.
"""

import sys
import micropython
from machine import Pin, PWM

# Stop Ctrl-C (0x03) from being treated as a keyboard interrupt on stdin,
# so we can safely read raw bytes from the PC script without the REPL
# hijacking control characters.
micropython.kbd_intr(-1)

# --- Pin setup (must match diagram.json) ---
led_green = Pin(16, Pin.OUT)
led_yellow = Pin(17, Pin.OUT)
led_red = Pin(18, Pin.OUT)

buzzer = PWM(Pin(19))
buzzer.duty_u16(0)

CURRENT_STATE = None


def buzzer_off():
    buzzer.duty_u16(0)


def buzzer_on(freq_hz):
    buzzer.freq(freq_hz)
    buzzer.duty_u16(25000)  # ~38% duty, audible but not full volume


def apply_state(state):
    """Drive the LEDs/buzzer for a given status code, only on change."""
    global CURRENT_STATE
    if state == CURRENT_STATE:
        return
    CURRENT_STATE = state

    led_green.value(0)
    led_yellow.value(0)
    led_red.value(0)
    buzzer_off()

    if state == "A":
        led_green.value(1)
    elif state == "H":
        led_yellow.value(1)
        buzzer_on(600)
    elif state == "D":
        led_red.value(1)
        buzzer_on(1200)


def main():
    print("Pico driver-monitor firmware ready (USB). Waiting for A/H/D bytes...")
    while True:
        # Blocking read of a single byte from the USB serial connection.
        # This is fine here since the firmware has nothing else to do
        # between status updates.
        ch = sys.stdin.read(1)
        if ch in ("A", "H", "D"):
            apply_state(ch)


if __name__ == "__main__":
    main()