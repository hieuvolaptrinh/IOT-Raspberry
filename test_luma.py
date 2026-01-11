#!/usr/bin/env python3
"""
Test LCD sử dụng thư viện luma.lcd
Thư viện này hỗ trợ nhiều loại ST7789 hơn
"""

from luma.core.interface.serial import spi
from luma.lcd.device import st7789
from PIL import Image, ImageDraw
import time

print("="*50)
print("TEST LCD VỚI LUMA.LCD")
print("="*50)

# Thử cấu hình 1: DC=24, RST=25
print("\n[Test 1] DC=GPIO24, RST=GPIO25")
try:
    serial = spi(port=0, device=0, gpio_DC=24, gpio_RST=25, bus_speed_hz=32000000)
    device = st7789(serial, width=240, height=240, rotate=0)
    
    # Tô màu đỏ
    img = Image.new('RGB', (240, 240), color='red')
    device.display(img)
    print("→ Màn hình có hiển thị màu ĐỎ không?")
    time.sleep(3)
    
    # Tô màu xanh
    img = Image.new('RGB', (240, 240), color='green')
    device.display(img)
    print("→ Màn hình có hiển thị màu XANH LÁ không?")
    time.sleep(3)
    
    # Tô màu xanh dương
    img = Image.new('RGB', (240, 240), color='blue')
    device.display(img)
    print("→ Màn hình có hiển thị màu XANH DƯƠNG không?")
    time.sleep(3)
    
except Exception as e:
    print(f"Lỗi: {e}")

# Thử cấu hình 2: DC=25, RST=24 (đảo ngược)
print("\n[Test 2] DC=GPIO25, RST=GPIO24 (đảo ngược)")
try:
    serial = spi(port=0, device=0, gpio_DC=25, gpio_RST=24, bus_speed_hz=32000000)
    device = st7789(serial, width=240, height=240, rotate=0)
    
    img = Image.new('RGB', (240, 240), color='red')
    device.display(img)
    print("→ Màn hình có hiển thị màu ĐỎ không?")
    time.sleep(3)
    
except Exception as e:
    print(f"Lỗi: {e}")

print("\n" + "="*50)
print("HOÀN TẤT!")
print("Nếu KHÔNG cấu hình nào hoạt động:")
print("1. Đổi dây SDA <-> SCL trên board")  
print("2. Kiểm tra dây nối có chắc chắn không")
print("="*50)
