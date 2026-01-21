#!/usr/bin/env python3
"""
TEST 3: Pimoroni st7789 library
Cài đặt: pip install st7789
"""
import st7789
from PIL import Image
import time

print("=" * 50)
print(" TEST PIMORONI ST7789 - 1.54\"")
print("=" * 50)

# Thử nhiều config khác nhau
CONFIGS = [
    # (dc, rst, invert, offset_left, offset_top)
    (25, 24, True, 0, 0),
    (24, 25, True, 0, 0),     # Hoán đổi DC/RST
    (25, 24, False, 0, 0),    # Không invert
    (25, 24, True, 40, 53),   # Waveshare offset
    (25, 24, True, 0, 80),    # Generic offset
]

for i, (dc, rst, inv, off_l, off_t) in enumerate(CONFIGS):
    print(f"\n[{i+1}/{len(CONFIGS)}] DC={dc}, RST={rst}, invert={inv}, offset=({off_l},{off_t})")
    
    try:
        disp = st7789.ST7789(
            port=0,
            cs=0,
            dc=dc,
            rst=rst,
            backlight=18,
            width=240,
            height=240,
            rotation=0,
            invert=inv,
            spi_speed_hz=40000000,
            offset_left=off_l,
            offset_top=off_t
        )
        
        # Test màu đỏ
        print("  → ĐỎ")
        img = Image.new("RGB", (240, 240), "red")
        disp.display(img)
        time.sleep(0.8)
        
        # Test màu xanh
        print("  → XANH LÁ")
        img = Image.new("RGB", (240, 240), "green")
        disp.display(img)
        time.sleep(0.8)
        
        # Test màu xanh dương
        print("  → XANH DƯƠNG")
        img = Image.new("RGB", (240, 240), "blue")
        disp.display(img)
        time.sleep(0.8)
        
        print("  ✓ Config này hoạt động!")
        
    except Exception as e:
        print(f"  ✗ Lỗi: {e}")

print("\n" + "=" * 50)
print(" Test xong!")
print("=" * 50)
