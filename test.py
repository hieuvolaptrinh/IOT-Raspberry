#!/usr/bin/env python3
"""
TEST CƠ BẢN - ST7789 LCD với SPI Mode 3
Hiển thị màu và test kết nối
"""
from display_image import ST7789Display
from PIL import Image
import time

print("=" * 50)
print(" TEST LCD ST7789 - SPI Mode 3")
print("=" * 50)

display = ST7789Display()

# Test màu
colors = [
    ("ĐỎ", "red"),
    ("XANH LÁ", "green"),
    ("XANH DƯƠNG", "blue"),
    ("TRẮNG", "white"),
]

print("\n→ Test các màu cơ bản:")
for name, color in colors:
    print(f"  {name}")
    display.fill(color)
    time.sleep(0.5)

print("\n✓ Test hoàn tất!")
display.cleanup()