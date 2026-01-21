#!/usr/bin/env python3
"""
TEST 4: solinnovay Python_ST7789 library
Thư viện này có API đặc biệt - cần truyền GPIO object

Cài đặt:
    cd ~
    git clone https://github.com/solinnovay/Python_ST7789.git
    cd Python_ST7789
    pip install .
"""
import time
from PIL import Image
import RPi.GPIO as GPIO

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

# Cấu hình
DC_PIN = 24       # GPIO24 - Data/Command
RST_PIN = 25      # GPIO25 - Reset
BL_PIN = 18       # GPIO18 - Backlight
SPI_SPEED = 40000000

# Setup GPIO trước
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Bật backlight
GPIO.setup(BL_PIN, GPIO.OUT)
GPIO.output(BL_PIN, GPIO.HIGH)
print("\n[1] Backlight: ON")

# Khởi tạo display - truyền GPIO object
print("[2] Khởi tạo display...")
try:
    # API của solinnovay: ST7789(gpio, spi, dc, rst, width, height, speed)
    import spidev
    spi = spidev.SpiDev()
    spi.open(0, 0)
    spi.max_speed_hz = SPI_SPEED
    spi.mode = 0
    
    disp = ST7789(
        gpio=GPIO,
        spi=spi,
        dc=DC_PIN,
        rst=RST_PIN,
        width=240,
        height=240
    )
    print("    ✓ Khởi tạo thành công!")
    
except TypeError as e:
    print(f"    Lỗi TypeError: {e}")
    print("    Thử API khác...")
    
    # Thử API khác
    try:
        disp = ST7789(
            GPIO,           # gpio object
            DC_PIN,         # dc
            RST_PIN,        # rst
            240,            # width
            240             # height
        )
        print("    ✓ Khởi tạo thành công (API 2)!")
    except Exception as e2:
        print(f"    Lỗi: {e2}")
        print("\n⚠️  Thư viện solinnovay không tương thích.")
        print("    Hãy thử chạy: python3 test_raw_spi.py")
        GPIO.cleanup()
        exit(1)

except Exception as e:
    print(f"    Lỗi: {e}")
    print("\n⚠️  Hãy thử chạy: python3 test_raw_spi.py")
    GPIO.cleanup()
    exit(1)

# Test màu
print("\n[3] Test màu...")
colors = [
    ("ĐỎ", "red"),
    ("XANH LÁ", "green"),
    ("XANH DƯƠNG", "blue"),
    ("TRẮNG", "white"),
]

for name, color in colors:
    print(f"    → {name}")
    img = Image.new("RGB", (240, 240), color)
    disp.display(img)
    time.sleep(1)

print("\n" + "=" * 50)
print(" Test xong!")
print("=" * 50)
GPIO.cleanup()