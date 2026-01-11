#!/usr/bin/env python3
"""
DEBUG: Thử nhiều cấu hình GPIO khác nhau
Chạy: python3 test_gpio_combo.py
"""

import spidev
import RPi.GPIO as GPIO
import time

print("="*50)
print("TEST NHIỀU CẤU HÌNH GPIO")
print("="*50)

# Danh sách các cấu hình GPIO phổ biến
# (DC, RST) - CS luôn là CE0
GPIO_CONFIGS = [
    (24, 25, "DC=GPIO24(Pin18), RST=GPIO25(Pin22)"),  # Config hiện tại
    (25, 24, "DC=GPIO25(Pin22), RST=GPIO24(Pin18)"),  # Đảo ngược
    (5, 6, "DC=GPIO5(Pin29), RST=GPIO6(Pin31)"),      # GPIO thấp
    (6, 5, "DC=GPIO6(Pin31), RST=GPIO5(Pin29)"),      # Đảo ngược
    (17, 27, "DC=GPIO17(Pin11), RST=GPIO27(Pin13)"),  # Cấu hình khác
    (22, 23, "DC=GPIO22(Pin15), RST=GPIO23(Pin16)"),  # Cấu hình khác
]

BL_PIN = 18  # Backlight - Pin 12

def test_config(dc_pin, rst_pin, description):
    print(f"\n>>> Testing: {description}")
    
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    
    try:
        GPIO.setup(dc_pin, GPIO.OUT)
        GPIO.setup(rst_pin, GPIO.OUT)
        GPIO.setup(BL_PIN, GPIO.OUT)
        GPIO.output(BL_PIN, GPIO.HIGH)
        
        spi = spidev.SpiDev()
        spi.open(0, 0)
        spi.max_speed_hz = 10000000
        spi.mode = 0
        
        # Reset
        GPIO.output(rst_pin, GPIO.HIGH)
        time.sleep(0.05)
        GPIO.output(rst_pin, GPIO.LOW)
        time.sleep(0.05)
        GPIO.output(rst_pin, GPIO.HIGH)
        time.sleep(0.15)
        
        def cmd(c):
            GPIO.output(dc_pin, GPIO.LOW)
            spi.writebytes([c])
        
        def data(d):
            GPIO.output(dc_pin, GPIO.HIGH)
            if isinstance(d, int):
                spi.writebytes([d])
            else:
                spi.writebytes(list(d))
        
        # Init sequence
        cmd(0x11)  # Sleep out
        time.sleep(0.12)
        cmd(0x36)  # Memory Access
        data(0x00)
        cmd(0x3A)  # Pixel Format
        data(0x55)
        cmd(0x21)  # Inversion ON
        cmd(0x29)  # Display ON
        time.sleep(0.1)
        
        # Fill RED
        cmd(0x2A)
        data([0x00, 0x00, 0x00, 0xEF])
        cmd(0x2B)
        data([0x00, 0x00, 0x00, 0xEF])
        cmd(0x2C)
        
        # Send red pixels (RGB565: 0xF800)
        red = [0xF8, 0x00] * 240 * 10  # Send rows in chunks
        for _ in range(24):
            data(red)
        
        print(f"    ✓ Sent RED color to display")
        print(f"    → Màn hình có hiện màu đỏ không? (y/n)")
        
        spi.close()
        return True
        
    except Exception as e:
        print(f"    ✗ Lỗi: {e}")
        return False
    finally:
        GPIO.cleanup()

# Test từng cấu hình
print("\nNhấn Enter sau mỗi test để tiếp tục...")
print("Nếu thấy màn hình hiện màu ĐỎ, ghi nhớ cấu hình đó!\n")

for dc, rst, desc in GPIO_CONFIGS:
    test_config(dc, rst, desc)
    input("Nhấn Enter để test cấu hình tiếp theo...")

print("\n" + "="*50)
print("HOÀN TẤT!")
print("Nếu không cấu hình nào hiển thị được:")
print("1. Kiểm tra lại dây nối")
print("2. Có thể màn hình bị lỗi")
print("3. Thử nối CS vào CE1 (Pin 26) thay vì CE0 (Pin 24)")
print("="*50)
