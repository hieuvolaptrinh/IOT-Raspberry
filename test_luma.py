#!/usr/bin/env python3
"""
Test LCD ST7789 dùng thư viện luma.lcd
Cài: pip3 install luma.lcd RPi.GPIO --break-system-packages
"""
from luma.core.interface.serial import spi
from luma.lcd.device import st7789
from PIL import Image, ImageDraw
import RPi.GPIO as GPIO
import time

# GPIO pins (BCM)
DC = 24    # GPIO24 (pin 18)
RST = 25   # GPIO25 (pin 22)
BL = 18    # GPIO18 (pin 12) - Backlight

def setup_backlight():
    """Bật đèn nền LCD"""
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(BL, GPIO.OUT)
    GPIO.output(BL, GPIO.HIGH)
    print("Backlight: ON")

def main():
    print("="*50)
    print(" TEST LCD ST7789 - LUMA.LCD")
    print("="*50)
    
    # Bước 1: Bật backlight trước
    setup_backlight()
    time.sleep(0.5)
    
    # Bước 2: Khởi tạo SPI và LCD
    print("\nKhoi tao LCD...")
    try:
        serial = spi(
            port=0,
            device=0,
            gpio_DC=DC,
            gpio_RST=RST,
            bus_speed_hz=4000000
        )
        
        device = st7789(
            serial,
            width=240,
            height=240,
            rotate=0
        )
        print("LCD da khoi tao!")
        
    except Exception as e:
        print(f"Loi khoi tao: {e}")
        GPIO.cleanup()
        return
    
    # Bước 3: Test màu
    print("\nTest mau...")
    
    colors = [
        ("red", "DO"),
        ("green", "XANH LA"),
        ("blue", "XANH DUONG"),
        ("white", "TRANG"),
        ("yellow", "VANG"),
        ("black", "DEN")
    ]
    
    for color, name in colors:
        print(f"  Hien thi: {name}...")
        img = Image.new("RGB", (240, 240), color)
        device.display(img)
        time.sleep(0.8)
    
    # Bước 4: Vẽ text
    print("\nVe text...")
    img = Image.new("RGB", (240, 240), "black")
    draw = ImageDraw.Draw(img)
    draw.text((60, 100), "LCD OK!", fill="white")
    draw.rectangle([10, 10, 230, 230], outline="yellow", width=3)
    draw.ellipse([80, 150, 160, 200], fill="cyan")
    device.display(img)
    
    print("\n" + "="*50)
    print(" TEST HOAN TAT!")
    print("="*50)
    
    answer = input("\nThay mau tren LCD? (y/n): ").strip().lower()
    if answer == 'y':
        print("LCD hoat dong OK!")
    else:
        print("Kiem tra lai day noi...")
    
    # Cleanup
    GPIO.cleanup()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nDa huy.")
        GPIO.cleanup()
    except Exception as e:
        print(f"Loi: {e}")
        GPIO.cleanup()
