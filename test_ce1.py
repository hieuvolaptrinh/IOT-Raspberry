#!/usr/bin/env python3
"""
Test với CS = CE1 (Pin 26) thay vì CE0 (Pin 24)
"""

import spidev
import RPi.GPIO as GPIO
import time

DC_PIN = 24
RST_PIN = 25

print("="*50)
print("TEST VỚI SPI CE1 (Pin 26)")
print("="*50)
print("Đảm bảo CS nối vào PIN 26 (không phải Pin 24)")

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(DC_PIN, GPIO.OUT)
GPIO.setup(RST_PIN, GPIO.OUT)

spi = spidev.SpiDev()
spi.open(0, 1)  # Dùng CE1 thay vì CE0
spi.max_speed_hz = 10000000
spi.mode = 0

def cmd(c):
    GPIO.output(DC_PIN, GPIO.LOW)
    spi.writebytes([c])

def data(d):
    GPIO.output(DC_PIN, GPIO.HIGH)
    if isinstance(d, int):
        spi.writebytes([d])
    else:
        for i in range(0, len(d), 4096):
            spi.writebytes(d[i:i+4096])

# Reset
print("Reset...")
GPIO.output(RST_PIN, GPIO.HIGH)
time.sleep(0.1)
GPIO.output(RST_PIN, GPIO.LOW)
time.sleep(0.1)
GPIO.output(RST_PIN, GPIO.HIGH)
time.sleep(0.2)

# Init
print("Init...")
cmd(0x01)
time.sleep(0.15)
cmd(0x11)
time.sleep(0.12)
cmd(0x36)
data(0x00)
cmd(0x3A)
data(0x55)
cmd(0x21)
cmd(0x29)
time.sleep(0.1)

# Fill RED
print("Fill RED...")
cmd(0x2A)
data([0x00, 0x00, 0x00, 0xEF])
cmd(0x2B)
data([0x00, 0x00, 0x00, 0xEF])
cmd(0x2C)

GPIO.output(DC_PIN, GPIO.HIGH)
red = [0xF8, 0x00] * 240
for _ in range(240):
    spi.writebytes(red)

print("\n→ Có thấy màu ĐỎ không?")
time.sleep(5)

spi.close()
GPIO.cleanup()
