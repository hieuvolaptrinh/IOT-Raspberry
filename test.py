#!/usr/bin/env python3
"""
TEST 1: luma.lcd library
Cài đặt: pip install luma.lcd
"""
from luma.core.interface.serial import spi
from luma.lcd.device import st7789
from PIL import Image
import RPi.GPIO as GPIO
import time

GPIO.setwarnings(False)

# Bật backlight thủ công
BL_PIN = 18
GPIO.setmode(GPIO.BCM)
GPIO.setup(BL_PIN, GPIO.OUT)
GPIO.output(BL_PIN, GPIO.HIGH)

print("=" * 50)
print(" TEST LUMA.LCD - ST7789 1.54\"")
print("=" * 50)

# Thử nhiều config offset cho màn hình 1.54"
CONFIGS = [
    {"offset": (0, 0), "name": "No offset"},
    {"offset": (40, 53), "name": "Waveshare offset"},
    {"offset": (0, 80), "name": "Generic offset 1"},
    {"offset": (80, 0), "name": "Generic offset 2"},
]

for i, cfg in enumerate(CONFIGS):
    print(f"\n[{i+1}/{len(CONFIGS)}] Testing: {cfg['name']}")
    print(f"  offset_left={cfg['offset'][0]}, offset_top={cfg['offset'][1]}")
    
    try:
        serial = spi(port=0, device=0, gpio_DC=25, gpio_RST=24, bus_speed_hz=40000000)
        device = st7789(serial, width=240, height=240, rotate=0, bgr=True)
        
        # Test màu đỏ
        img = Image.new("RGB", (240, 240), "red")
        device.display(img)
        time.sleep(1)
        
        # Test màu xanh
        img = Image.new("RGB", (240, 240), "green")
        device.display(img)
        time.sleep(1)
        
        # Test màu xanh dương
        img = Image.new("RGB", (240, 240), "blue")
        device.display(img)
        time.sleep(1)
        
        print("  → Hiển thị 3 màu: ĐỎ, XANH LÁ, XANH DƯƠNG")
        
    except Exception as e:
        print(f"  → Lỗi: {e}")

print("\n" + "=" * 50)
print(" Test xong! Nếu thấy 3 màu → THÀNH CÔNG!")
print("=" * 50)