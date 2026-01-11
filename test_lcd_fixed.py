#!/usr/bin/env python3
"""
Test LCD 1.54" ST7789 - Gửi dữ liệu nhỏ hơn 4096 bytes
"""

import spidev
import RPi.GPIO as GPIO
import time

# GPIO pins (BCM)
DC_PIN = 24    # Pin 18
RST_PIN = 25   # Pin 22
BL_PIN = 18    # Pin 12

print("="*50)
print("TEST LCD 1.54 inch ST7789")
print("="*50)

# Setup GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(DC_PIN, GPIO.OUT)
GPIO.setup(RST_PIN, GPIO.OUT)
GPIO.setup(BL_PIN, GPIO.OUT)

# Bật backlight
GPIO.output(BL_PIN, GPIO.HIGH)
print("✓ Backlight ON")

# Setup SPI
spi = spidev.SpiDev()
spi.open(0, 0)
spi.max_speed_hz = 40000000  # 40MHz
spi.mode = 0

def cmd(c):
    GPIO.output(DC_PIN, GPIO.LOW)
    spi.writebytes([c])

def data(d):
    GPIO.output(DC_PIN, GPIO.HIGH)
    if isinstance(d, int):
        spi.writebytes([d])
    elif isinstance(d, list):
        # Chia nhỏ thành chunks <= 4096 bytes
        chunk_size = 4096
        for i in range(0, len(d), chunk_size):
            spi.writebytes(d[i:i+chunk_size])

# Reset LCD
print("Đang reset LCD...")
GPIO.output(RST_PIN, GPIO.HIGH)
time.sleep(0.05)
GPIO.output(RST_PIN, GPIO.LOW)
time.sleep(0.05)
GPIO.output(RST_PIN, GPIO.HIGH)
time.sleep(0.15)

# Khởi tạo ST7789
print("Đang khởi tạo ST7789...")

cmd(0x11)  # Sleep Out
time.sleep(0.12)

cmd(0x36)  # Memory Access Control
data(0x00)

cmd(0x3A)  # Pixel Format
data(0x55)  # 16-bit RGB565

cmd(0xB2)  # Porch Setting
data([0x0C, 0x0C, 0x00, 0x33, 0x33])

cmd(0xB7)  # Gate Control
data(0x35)

cmd(0xBB)  # VCOM
data(0x19)

cmd(0xC0)  # LCM Control
data(0x2C)

cmd(0xC2)  # VDV and VRH Enable
data(0x01)

cmd(0xC3)  # VRH Set
data(0x12)

cmd(0xC4)  # VDV Set
data(0x20)

cmd(0xC6)  # Frame Rate
data(0x0F)

cmd(0xD0)  # Power Control
data([0xA4, 0xA1])

cmd(0x21)  # Inversion ON

cmd(0x29)  # Display ON
time.sleep(0.1)

print("✓ LCD đã khởi tạo!")

# Set Window
def set_window(x0, y0, x1, y1):
    cmd(0x2A)  # Column
    data([x0 >> 8, x0 & 0xFF, x1 >> 8, x1 & 0xFF])
    cmd(0x2B)  # Row
    data([y0 >> 8, y0 & 0xFF, y1 >> 8, y1 & 0xFF])
    cmd(0x2C)  # Memory Write

def fill_color(r, g, b):
    """Fill màn hình với màu RGB"""
    # Convert RGB888 to RGB565
    rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
    high = rgb565 >> 8
    low = rgb565 & 0xFF
    
    set_window(0, 0, 239, 239)
    
    # Gửi từng dòng (240 pixels = 480 bytes < 4096)
    row = [high, low] * 240
    for _ in range(240):
        data(row)

# Test màu
print("\nTest 1: Màu ĐỎ...")
fill_color(255, 0, 0)
time.sleep(2)

print("Test 2: Màu XANH LÁ...")
fill_color(0, 255, 0)
time.sleep(2)

print("Test 3: Màu XANH DƯƠNG...")
fill_color(0, 0, 255)
time.sleep(2)

print("Test 4: Màu TRẮNG...")
fill_color(255, 255, 255)
time.sleep(2)

print("Test 5: Màu ĐEN...")
fill_color(0, 0, 0)
time.sleep(1)

print("\n" + "="*50)
print("✅ HOÀN TẤT!")
print("Nếu màn hình hiển thị các màu đúng → LCD OK!")
print("="*50)

spi.close()
GPIO.cleanup()
