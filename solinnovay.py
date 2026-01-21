#!/usr/bin/env python3
"""
TEST 4: solinnovay Python_ST7789 library
Thư viện này cần Adafruit_GPIO (không phải RPi.GPIO)

Cài đặt:
    pip install Adafruit-GPIO
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

# Kiểm tra Adafruit_GPIO
try:
    import Adafruit_GPIO as GPIO
    import Adafruit_GPIO.SPI as SPI
    print("[1] Adafruit_GPIO: OK")
except ImportError:
    print("❌ Chưa cài Adafruit_GPIO!")
    print("   Chạy: pip install Adafruit-GPIO")
    exit(1)

# Kiểm tra ST7789
try:
    from ST7789 import ST7789
    print("[2] ST7789 (solinnovay): OK")
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

# Bật backlight thủ công
import RPi.GPIO as RGPIO
RGPIO.setmode(RGPIO.BCM)
RGPIO.setwarnings(False)
RGPIO.setup(BL_PIN, RGPIO.OUT)
RGPIO.output(BL_PIN, RGPIO.HIGH)
print("[3] Backlight: ON")

# Khởi tạo display
print("[4] Khởi tạo display...")
try:
    # Tạo SPI device
    spi = SPI.SpiDev(0, 0, max_speed_hz=40000000)
    
    # Tạo GPIO platform
    gpio = GPIO.get_platform_gpio()
    
    # Khởi tạo ST7789
    disp = ST7789(
        spi=spi,
        gpio=gpio,
        dc=DC_PIN,
        rst=RST_PIN,
        width=240,
        height=240
    )
    print("    ✓ Khởi tạo thành công!")
    
except Exception as e:
    print(f"    Lỗi: {e}")
    print("\n    Thử cách 2...")
    
    try:
        # Thử không dùng SPI wrapper
        disp = ST7789(
            dc=DC_PIN,
            rst=RST_PIN,
            spi=SPI.SpiDev(0, 0)
        )
        print("    ✓ Khởi tạo thành công (cách 2)!")
    except Exception as e2:
        print(f"    Lỗi: {e2}")
        print("\n⚠️  Thư viện không tương thích. Thử:")
        print("    python3 test_final.py")
        RGPIO.cleanup()
        exit(1)

# Bắt đầu display
disp.begin()

# Test màu
print("\n[5] Test màu...")
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
RGPIO.cleanup()