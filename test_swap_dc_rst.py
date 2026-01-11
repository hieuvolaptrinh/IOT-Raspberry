#!/usr/bin/env python3
"""
Test với DC và RST đảo ngược + nhiều cấu hình
"""

import spidev
import RPi.GPIO as GPIO
import time

# ĐẢO NGƯỢC DC và RST
DC_PIN = 25    # Thử GPIO 25 (Pin 22) làm DC
RST_PIN = 24   # Thử GPIO 24 (Pin 18) làm RST
CS_PIN = 8

print("="*50)
print("TEST VỚI DC=GPIO25, RST=GPIO24 (ĐẢO NGƯỢC)")
print("="*50)

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(DC_PIN, GPIO.OUT)
GPIO.setup(RST_PIN, GPIO.OUT)
GPIO.setup(CS_PIN, GPIO.OUT)

spi = spidev.SpiDev()
spi.open(0, 0)
spi.max_speed_hz = 10000000
spi.mode = 0
spi.no_cs = True

def cmd(c):
    GPIO.output(CS_PIN, GPIO.LOW)
    GPIO.output(DC_PIN, GPIO.LOW)
    spi.writebytes([c])
    GPIO.output(CS_PIN, GPIO.HIGH)

def data(d):
    GPIO.output(CS_PIN, GPIO.LOW)
    GPIO.output(DC_PIN, GPIO.HIGH)
    if isinstance(d, int):
        spi.writebytes([d])
    else:
        for i in range(0, len(d), 4096):
            spi.writebytes(d[i:i+4096])
    GPIO.output(CS_PIN, GPIO.HIGH)

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
cmd(0x21)  # Inversion ON
cmd(0x29)
time.sleep(0.1)

# Fill RED
print("Fill RED...")
cmd(0x2A)
data([0x00, 0x00, 0x00, 0xEF])
cmd(0x2B)
data([0x00, 0x00, 0x00, 0xEF])
cmd(0x2C)

GPIO.output(CS_PIN, GPIO.LOW)
GPIO.output(DC_PIN, GPIO.HIGH)
red = [0xF8, 0x00] * 240
for _ in range(240):
    spi.writebytes(red)
GPIO.output(CS_PIN, GPIO.HIGH)

print("\n→ Màn hình có hiện màu ĐỎ không?")
print("  Nếu CÓ → Bạn đã nối DC và RST ngược!")
print("  Giải pháp: Đổi dây DC <-> RST trên board")

time.sleep(5)

# Thử thêm với Inversion OFF
print("\nThử thêm Inversion OFF...")
cmd(0x01)
time.sleep(0.15)
cmd(0x11)
time.sleep(0.12)
cmd(0x36)
data(0x00)
cmd(0x3A)
data(0x55)
cmd(0x20)  # Inversion OFF
cmd(0x29)
time.sleep(0.1)

cmd(0x2A)
data([0x00, 0x00, 0x00, 0xEF])
cmd(0x2B)
data([0x00, 0x00, 0x00, 0xEF])
cmd(0x2C)

GPIO.output(CS_PIN, GPIO.LOW)
GPIO.output(DC_PIN, GPIO.HIGH)
for _ in range(240):
    spi.writebytes(red)
GPIO.output(CS_PIN, GPIO.HIGH)

print("→ Bây giờ có thấy màu ĐỎ không?")

time.sleep(5)
spi.close()
GPIO.cleanup()
