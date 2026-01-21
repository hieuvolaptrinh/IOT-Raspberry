#!/usr/bin/env python3
"""
TEST 2: Adafruit CircuitPython + Blinka
Cài đặt: pip install adafruit-blinka adafruit-circuitpython-rgb-display pillow
"""
import digitalio
import board
from PIL import Image
from adafruit_rgb_display import st7789
import time
import RPi.GPIO as GPIO

GPIO.setwarnings(False)

# Bật backlight thủ công
BL_PIN = 18
GPIO.setmode(GPIO.BCM)
GPIO.setup(BL_PIN, GPIO.OUT)
GPIO.output(BL_PIN, GPIO.HIGH)

print("=" * 50)
print(" TEST ADAFRUIT CIRCUITPYTHON - ST7789 1.54\"")
print("=" * 50)

# Config pins
cs_pin = digitalio.DigitalInOut(board.CE0)
dc_pin = digitalio.DigitalInOut(board.D25)
reset_pin = digitalio.DigitalInOut(board.D24)

# Init SPI
spi = board.SPI()

# Thử nhiều config
OFFSETS = [
    (0, 0),
    (40, 53),   # Waveshare
    (0, 80),    # Generic
]

for x_off, y_off in OFFSETS:
    print(f"\n→ Testing offset: x={x_off}, y={y_off}")
    
    try:
        disp = st7789.ST7789(
            spi,
            cs=cs_pin,
            dc=dc_pin,
            rst=reset_pin,
            baudrate=24000000,
            width=240,
            height=240,
            x_offset=x_off,
            y_offset=y_off
        )
        
        # Test màu đỏ
        print("  Hiển thị: ĐỎ")
        img = Image.new("RGB", (240, 240), "red")
        disp.image(img)
        time.sleep(1)
        
        # Test màu xanh
        print("  Hiển thị: XANH LÁ")
        img = Image.new("RGB", (240, 240), "green")
        disp.image(img)
        time.sleep(1)
        
        # Test màu xanh dương
        print("  Hiển thị: XANH DƯƠNG")
        img = Image.new("RGB", (240, 240), "blue")
        disp.image(img)
        time.sleep(1)
        
    except Exception as e:
        print(f"  Lỗi: {e}")

print("\n" + "=" * 50)
print(" Test xong! Nếu thấy 3 màu → THÀNH CÔNG!")
print("=" * 50)