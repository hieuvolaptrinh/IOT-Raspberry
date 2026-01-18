#!/usr/bin/env python3
"""
Test LCD ST7789 dùng thư viện luma.lcd
Cài: pip3 install luma.lcd --break-system-packages
"""
from luma.core.interface.serial import spi
from luma.lcd.device import st7789
from PIL import Image, ImageDraw
import time

# GPIO pins (BCM)
DC = 24   # GPIO24 (pin 18)
RST = 25  # GPIO25 (pin 22)

def main():
    print("Khoi tao LCD voi luma.lcd...")
    
    # Khởi tạo SPI
    serial = spi(
        port=0,
        device=0,
        gpio_DC=DC,
        gpio_RST=RST,
        bus_speed_hz=4000000
    )
    
    # Khởi tạo LCD
    device = st7789(
        serial,
        width=240,
        height=240,
        rotate=0
    )
    
    print("LCD OK! Test mau...")
    
    # Test màu đỏ
    print("Do...")
    img = Image.new("RGB", (240, 240), "red")
    device.display(img)
    time.sleep(1)
    
    # Test màu xanh lá
    print("Xanh la...")
    img = Image.new("RGB", (240, 240), "green")
    device.display(img)
    time.sleep(1)
    
    # Test màu xanh dương
    print("Xanh duong...")
    img = Image.new("RGB", (240, 240), "blue")
    device.display(img)
    time.sleep(1)
    
    # Test màu trắng
    print("Trang...")
    img = Image.new("RGB", (240, 240), "white")
    device.display(img)
    time.sleep(1)
    
    # Vẽ text
    print("Ve text...")
    img = Image.new("RGB", (240, 240), "black")
    draw = ImageDraw.Draw(img)
    draw.text((50, 100), "LCD OK!", fill="white")
    draw.rectangle([10, 10, 230, 230], outline="yellow", width=2)
    device.display(img)
    
    print("Test hoan tat!")
    input("Nhan Enter de thoat...")

if __name__ == "__main__":
    main()
