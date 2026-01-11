#!/usr/bin/env python3
"""
Test LCD với CS được điều khiển thủ công (không dùng hardware CE0)
"""

import spidev
import RPi.GPIO as GPIO
import time

# GPIO pins
DC_PIN = 24    # Pin 18
RST_PIN = 25   # Pin 22
BL_PIN = 18    # Pin 12
CS_PIN = 8     # Pin 24 (GPIO 8 = CE0) - điều khiển thủ công

print("="*50)
print("TEST LCD VỚI CS THỦ CÔNG")
print("="*50)

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(DC_PIN, GPIO.OUT)
GPIO.setup(RST_PIN, GPIO.OUT)
GPIO.setup(BL_PIN, GPIO.OUT)
GPIO.setup(CS_PIN, GPIO.OUT)

GPIO.output(BL_PIN, GPIO.HIGH)
GPIO.output(CS_PIN, GPIO.HIGH)  # CS inactive

# SPI không dùng CE - chọn port 0, cs 1 hoặc no_cs
spi = spidev.SpiDev()
spi.open(0, 0)
spi.max_speed_hz = 20000000  # 20MHz - thử chậm hơn
spi.mode = 0
spi.no_cs = True  # Không dùng hardware CS

def cmd(c):
    GPIO.output(CS_PIN, GPIO.LOW)   # CS active
    GPIO.output(DC_PIN, GPIO.LOW)   # Command mode
    spi.writebytes([c])
    GPIO.output(CS_PIN, GPIO.HIGH)  # CS inactive

def data(d):
    GPIO.output(CS_PIN, GPIO.LOW)   # CS active
    GPIO.output(DC_PIN, GPIO.HIGH)  # Data mode
    if isinstance(d, int):
        spi.writebytes([d])
    elif isinstance(d, list):
        chunk_size = 4096
        for i in range(0, len(d), chunk_size):
            spi.writebytes(d[i:i+chunk_size])
    GPIO.output(CS_PIN, GPIO.HIGH)  # CS inactive

def data_continuous(d):
    """Gửi data liên tục không ngắt CS"""
    GPIO.output(CS_PIN, GPIO.LOW)
    GPIO.output(DC_PIN, GPIO.HIGH)
    if isinstance(d, list):
        chunk_size = 4096
        for i in range(0, len(d), chunk_size):
            spi.writebytes(d[i:i+chunk_size])
    GPIO.output(CS_PIN, GPIO.HIGH)

# Hardware Reset
print("1. Hardware Reset...")
GPIO.output(RST_PIN, GPIO.HIGH)
time.sleep(0.1)
GPIO.output(RST_PIN, GPIO.LOW)
time.sleep(0.1)
GPIO.output(RST_PIN, GPIO.HIGH)
time.sleep(0.2)

# Software Reset
print("2. Software Reset...")
cmd(0x01)
time.sleep(0.15)

# Sleep Out
print("3. Sleep Out...")
cmd(0x11)
time.sleep(0.12)

# Memory Access Control
print("4. Memory Access Control...")
cmd(0x36)
data(0x00)

# Pixel Format 16-bit
print("5. Pixel Format...")
cmd(0x3A)
data(0x55)

# Porch
cmd(0xB2)
data([0x0C, 0x0C, 0x00, 0x33, 0x33])

# Gate Control
cmd(0xB7)
data(0x35)

# VCOM
cmd(0xBB)
data(0x19)

# LCM Control
cmd(0xC0)
data(0x2C)

# VDV and VRH Enable
cmd(0xC2)
data(0x01)

# VRH Set
cmd(0xC3)
data(0x12)

# VDV Set
cmd(0xC4)
data(0x20)

# Frame Rate
cmd(0xC6)
data(0x0F)

# Power Control
cmd(0xD0)
data([0xA4, 0xA1])

# Positive Gamma
cmd(0xE0)
data([0xD0, 0x04, 0x0D, 0x11, 0x13, 0x2B, 0x3F, 0x54, 0x4C, 0x18, 0x0D, 0x0B, 0x1F, 0x23])

# Negative Gamma
cmd(0xE1)
data([0xD0, 0x04, 0x0C, 0x11, 0x13, 0x2C, 0x3F, 0x44, 0x51, 0x2F, 0x1F, 0x1F, 0x20, 0x23])

# Inversion ON
print("6. Display Inversion ON...")
cmd(0x21)

# Display ON
print("7. Display ON...")
cmd(0x29)
time.sleep(0.1)

# Set Column
print("8. Set Window...")
cmd(0x2A)
data([0x00, 0x00, 0x00, 0xEF])

# Set Row
cmd(0x2B)
data([0x00, 0x00, 0x00, 0xEF])

# Memory Write
cmd(0x2C)

# Fill RED - giữ CS low trong khi gửi data
print("9. Tô màu ĐỎ...")
GPIO.output(CS_PIN, GPIO.LOW)
GPIO.output(DC_PIN, GPIO.HIGH)

red_row = [0xF8, 0x00] * 240  # RGB565 red
for i in range(240):
    spi.writebytes(red_row)

GPIO.output(CS_PIN, GPIO.HIGH)

print("\n" + "="*50)
print("✅ HOÀN TẤT!")
print("Màn hình có hiển thị màu ĐỎ không?")
print("="*50)

time.sleep(5)

# Test GREEN
print("\nTest màu XANH LÁ...")
cmd(0x2A)
data([0x00, 0x00, 0x00, 0xEF])
cmd(0x2B)
data([0x00, 0x00, 0x00, 0xEF])
cmd(0x2C)

GPIO.output(CS_PIN, GPIO.LOW)
GPIO.output(DC_PIN, GPIO.HIGH)
green_row = [0x07, 0xE0] * 240  # RGB565 green
for i in range(240):
    spi.writebytes(green_row)
GPIO.output(CS_PIN, GPIO.HIGH)

time.sleep(3)

spi.close()
GPIO.cleanup()
print("Done!")
