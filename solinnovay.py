#!/usr/bin/env python3
"""
TEST 4: solinnovay Python_ST7789 library
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
    import ST7789
except ImportError:
    print("❌ Chưa cài thư viện solinnovay!")
    print("\nCài đặt:")
    print("  cd ~")
    print("  git clone https://github.com/solinnovay/Python_ST7789.git")
    print("  cd Python_ST7789")
    print("  pip install .")
    exit(1)

# Khởi tạo display
print("\n→ Khởi tạo display...")
disp = ST7789.ST7789(
    port=0,
    cs=0,
    dc=25,
    rst=24,
    backlight=18,
    spi_speed_hz=40000000,
    width=240,
    height=240
)
disp.begin()

# Test màu
colors = [
    ("ĐỎ", "red"),
    ("XANH LÁ", "green"),
    ("XANH DƯƠNG", "blue"),
]

for name, color in colors:
    print(f"  → Hiển thị: {name}")
    img = Image.new("RGB", (240, 240), color)
    disp.display(img)
    time.sleep(1)

print("\n" + "=" * 50)
print(" Test xong! Nếu thấy 3 màu → THÀNH CÔNG!")
print("=" * 50)