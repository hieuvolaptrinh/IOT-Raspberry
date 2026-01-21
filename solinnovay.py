#!/usr/bin/env python3
"""
TEST 4: solinnovay Python_ST7789 library
Thư viện này dành cho màn hình 7-pin không có CS

Cài đặt trước:
    cd ~
    git clone https://github.com/solinnovay/Python_ST7789.git
    cd Python_ST7789
    pip install .
"""
import time
from PIL import Image

print("=" * 50)
print(" TEST SOLINNOVAY Python_ST7789 - 1.54\"")
print("=" * 50)

try:
    from ST7789 import ST7789
except ImportError:
    print("❌ Chưa cài thư viện solinnovay!")
    print("\nCài đặt:")
    print("  cd ~")
    print("  git clone https://github.com/solinnovay/Python_ST7789.git")
    print("  cd Python_ST7789")
    print("  pip install .")
    exit(1)

# Cấu hình GPIO
SPI_PORT = 0
SPI_DEVICE = 0
DC_PIN = 25       # GPIO25
RST_PIN = 24      # GPIO24
BL_PIN = 18       # GPIO18 (Backlight)

# Bật backlight thủ công
import RPi.GPIO as GPIO
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(BL_PIN, GPIO.OUT)
GPIO.output(BL_PIN, GPIO.HIGH)

# Khởi tạo display - API của solinnovay
print("\n→ Khởi tạo display...")
try:
    disp = ST7789(
        SPI_PORT,
        SPI_DEVICE,
        DC_PIN,
        RST_PIN,
        0,              # CS (không dùng = 0)
        240,            # width
        240,            # height
        40000000        # SPI speed
    )
except TypeError:
    # Thử API khác
    print("  Thử API thay thế...")
    disp = ST7789(
        dc=DC_PIN,
        rst=RST_PIN,
        width=240,
        height=240
    )

print("  ✓ Khởi tạo thành công!")

# Test màu
colors = [
    ("ĐỎ", "red"),
    ("XANH LÁ", "green"),
    ("XANH DƯƠNG", "blue"),
    ("TRẮNG", "white"),
]

for name, color in colors:
    print(f"  → Hiển thị: {name}")
    img = Image.new("RGB", (240, 240), color)
    disp.display(img)
    time.sleep(1)

print("\n" + "=" * 50)
print(" Test xong! Nếu thấy 4 màu → THÀNH CÔNG!")
print("=" * 50)