#!/usr/bin/env python3
"""
Test với DC và RST đảo ngược
"""

import spidev
import RPi.GPIO as GPIO
import time

# THỬ ĐẢO NGƯỢC: DC=25, RST=24 (thay vì DC=24, RST=25)
DC_PIN = 25    # Pin 22 (đảo ngược)
RST_PIN = 24   # Pin 18 (đảo ngược)
BL_PIN = 18    # Pin 12

print("="*50)
print("TEST VỚI DC/RST ĐẢO NGƯỢC")
print(f"DC = GPIO{DC_PIN}, RST = GPIO{RST_PIN}")
print("="*50)

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(DC_PIN, GPIO.OUT)
GPIO.setup(RST_PIN, GPIO.OUT)
GPIO.setup(BL_PIN, GPIO.OUT)
GPIO.output(BL_PIN, GPIO.HIGH)

spi = spidev.SpiDev()
spi.open(0, 0)
spi.max_speed_hz = 40000000
spi.mode = 0

def cmd(c):
    GPIO.output(DC_PIN, GPIO.LOW)
    spi.writebytes([c])

def data(d):
    GPIO.output(DC_PIN, GPIO.HIGH)
    if isinstance(d, int):
        spi.writebytes([d])
    elif isinstance(d, list):
        chunk_size = 4096
        for i in range(0, len(d), chunk_size):
            spi.writebytes(d[i:i+chunk_size])

# Reset
print("Reset LCD...")
GPIO.output(RST_PIN, GPIO.HIGH)
time.sleep(0.05)
GPIO.output(RST_PIN, GPIO.LOW)
time.sleep(0.05)
GPIO.output(RST_PIN, GPIO.HIGH)
time.sleep(0.15)

# Init
print("Khởi tạo...")
cmd(0x11)
time.sleep(0.12)
cmd(0x36)
data(0x00)
cmd(0x3A)
data(0x55)
cmd(0xB2)
data([0x0C, 0x0C, 0x00, 0x33, 0x33])
cmd(0xB7)
data(0x35)
cmd(0xBB)
data(0x19)
cmd(0xC0)
data(0x2C)
cmd(0xC2)
data(0x01)
cmd(0xC3)
data(0x12)
cmd(0xC4)
data(0x20)
cmd(0xC6)
data(0x0F)
cmd(0xD0)
data([0xA4, 0xA1])
cmd(0x21)
cmd(0x29)
time.sleep(0.1)

# Fill RED
print("Tô màu ĐỎ...")
cmd(0x2A)
data([0x00, 0x00, 0x00, 0xEF])
cmd(0x2B)
data([0x00, 0x00, 0x00, 0xEF])
cmd(0x2C)

row = [0xF8, 0x00] * 240  # Red RGB565
for _ in range(240):
    data(row)

print("\n→ Màn hình có hiện màu ĐỎ không?")
print("  Nếu CÓ → DC=GPIO25, RST=GPIO24 là đúng!")
print("  Nếu KHÔNG → Kiểm tra lại dây nối")

time.sleep(5)
spi.close()
GPIO.cleanup()
