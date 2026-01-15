#!/usr/bin/env python3
"""
Debug LCD toàn diện - Thử tất cả các cấu hình có thể
Khắc phục lỗi "Device busy" bằng cách cleanup đúng cách
"""

import spidev
import RPi.GPIO as GPIO
from PIL import Image, ImageDraw
import time
import sys

# GPIO pins (BCM)
DC_PIN = 24
RST_PIN = 25
BL_PIN = 18

def cleanup():
    """Dọn dẹp GPIO và SPI"""
    try:
        GPIO.cleanup()
    except:
        pass

def init_gpio():
    """Khởi tạo GPIO"""
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(DC_PIN, GPIO.OUT)
    GPIO.setup(RST_PIN, GPIO.OUT)
    GPIO.setup(BL_PIN, GPIO.OUT)
    GPIO.output(BL_PIN, GPIO.HIGH)  # Bật backlight

def reset_display():
    """Reset màn hình"""
    GPIO.output(RST_PIN, GPIO.HIGH)
    time.sleep(0.05)
    GPIO.output(RST_PIN, GPIO.LOW)
    time.sleep(0.05)
    GPIO.output(RST_PIN, GPIO.HIGH)
    time.sleep(0.15)

def command(spi, cmd):
    """Gửi command"""
    GPIO.output(DC_PIN, GPIO.LOW)
    spi.writebytes([cmd])

def data(spi, dat):
    """Gửi data"""
    GPIO.output(DC_PIN, GPIO.HIGH)
    if isinstance(dat, int):
        spi.writebytes([dat])
    else:
        chunk_size = 4096
        for i in range(0, len(dat), chunk_size):
            spi.writebytes(dat[i:i+chunk_size])

def init_st7789(spi, invert=True, rotation=0, x_offset=0, y_offset=0):
    """Khởi tạo ST7789 với các tùy chọn"""
    reset_display()
    
    # Sleep Out
    command(spi, 0x11)
    time.sleep(0.12)
    
    # Memory Data Access Control (Rotation)
    command(spi, 0x36)
    rotations = [0x00, 0x60, 0xC0, 0xA0]
    data(spi, rotations[rotation % 4])
    
    # Interface Pixel Format - 16bit RGB565
    command(spi, 0x3A)
    data(spi, 0x55)
    
    # Porch Setting
    command(spi, 0xB2)
    data(spi, [0x0C, 0x0C, 0x00, 0x33, 0x33])
    
    # Gate Control
    command(spi, 0xB7)
    data(spi, 0x35)
    
    # VCOM
    command(spi, 0xBB)
    data(spi, 0x19)
    
    # LCM Control
    command(spi, 0xC0)
    data(spi, 0x2C)
    
    # VDV and VRH Enable
    command(spi, 0xC2)
    data(spi, 0x01)
    
    # VRH Set
    command(spi, 0xC3)
    data(spi, 0x12)
    
    # VDV Set
    command(spi, 0xC4)
    data(spi, 0x20)
    
    # Frame Rate
    command(spi, 0xC6)
    data(spi, 0x0F)
    
    # Power Control 1
    command(spi, 0xD0)
    data(spi, [0xA4, 0xA1])
    
    # Gamma
    command(spi, 0xE0)
    data(spi, [0xD0, 0x04, 0x0D, 0x11, 0x13, 0x2B, 0x3F, 0x54, 0x4C, 0x18, 0x0D, 0x0B, 0x1F, 0x23])
    command(spi, 0xE1)
    data(spi, [0xD0, 0x04, 0x0C, 0x11, 0x13, 0x2C, 0x3F, 0x44, 0x51, 0x2F, 0x1F, 0x1F, 0x20, 0x23])
    
    # Display Inversion
    if invert:
        command(spi, 0x21)  # Inversion ON
    else:
        command(spi, 0x20)  # Inversion OFF
    
    # Display ON
    command(spi, 0x29)
    time.sleep(0.1)

def fill_color(spi, color, width=240, height=240, x_offset=0, y_offset=0):
    """Tô màu toàn màn hình"""
    r, g, b = color
    
    # Set window
    x0, y0 = 0, 0
    x1, y1 = width - 1, height - 1
    
    # Column Address Set
    command(spi, 0x2A)
    data(spi, [(x0 + x_offset) >> 8, (x0 + x_offset) & 0xFF,
               (x1 + x_offset) >> 8, (x1 + x_offset) & 0xFF])
    
    # Row Address Set
    command(spi, 0x2B)
    data(spi, [(y0 + y_offset) >> 8, (y0 + y_offset) & 0xFF,
               (y1 + y_offset) >> 8, (y1 + y_offset) & 0xFF])
    
    # Write to RAM
    command(spi, 0x2C)
    
    # Convert RGB to RGB565
    rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
    pixel = [rgb565 >> 8, rgb565 & 0xFF]
    
    # Send pixels
    buffer = pixel * (width * height)
    data(spi, buffer)

def test_config(config_name, invert, rotation, x_offset, y_offset, spi_speed):
    """Test một cấu hình"""
    print(f"\n{'='*60}")
    print(f"Config: {config_name}")
    print(f"  Invert={invert}, Rotation={rotation}, Offset=({x_offset},{y_offset})")
    print(f"  SPI Speed={spi_speed/1_000_000}MHz")
    print("="*60)
    
    cleanup()
    time.sleep(0.2)
    
    try:
        init_gpio()
        
        spi = spidev.SpiDev()
        spi.open(0, 0)
        spi.max_speed_hz = spi_speed
        spi.mode = 0
        
        init_st7789(spi, invert=invert, rotation=rotation, 
                   x_offset=x_offset, y_offset=y_offset)
        
        # Test colors
        colors = [
            ((255, 0, 0), "ĐỎ"),
            ((0, 255, 0), "XANH LÁ"),
            ((0, 0, 255), "XANH DƯƠNG"),
            ((255, 255, 255), "TRẮNG"),
        ]
        
        for color, name in colors:
            print(f"  Hiển thị màu {name}...")
            fill_color(spi, color, x_offset=x_offset, y_offset=y_offset)
            time.sleep(0.8)
        
        spi.close()
        
        answer = input("\n  ❓ LCD có hiển thị màu không? (y/n/q): ").strip().lower()
        cleanup()
        return answer
        
    except Exception as e:
        print(f"  ❌ Lỗi: {e}")
        cleanup()
        return 'e'

def main():
    print("="*60)
    print(" DEBUG LCD ST7789 - PHIÊN BẢN ĐẦY ĐỦ")
    print(" Test nhiều cấu hình display khác nhau")
    print("="*60)
    
    # Các cấu hình cần test
    configs = [
        # (name, invert, rotation, x_offset, y_offset, spi_speed)
        ("Mặc định (Invert ON)", True, 0, 0, 0, 40_000_000),
        ("Invert OFF", False, 0, 0, 0, 40_000_000),
        ("Rotation 1 (90°)", True, 1, 0, 0, 40_000_000),
        ("Rotation 2 (180°)", True, 2, 0, 0, 40_000_000),
        ("Offset 40,53 (cho LCD 1.3\")", True, 0, 40, 53, 40_000_000),
        ("Offset 80,0 (cho LCD 240x135)", True, 0, 80, 0, 40_000_000),
        ("SPI chậm 10MHz", True, 0, 0, 0, 10_000_000),
        ("SPI rất chậm 4MHz", True, 0, 0, 0, 4_000_000),
    ]
    
    for i, (name, invert, rotation, x_off, y_off, speed) in enumerate(configs):
        result = test_config(name, invert, rotation, x_off, y_off, speed)
        
        if result == 'y':
            print("\n" + "🎉"*30)
            print(f"\n TÌM THẤY CẤU HÌNH ĐÚNG: {name}")
            print(f" Invert={invert}, Rotation={rotation}")
            print(f" Offset=({x_off}, {y_off}), SPI={speed/1_000_000}MHz")
            print("\n" + "🎉"*30)
            return
        elif result == 'q':
            print("\nThoát...")
            break
    
    print("\n" + "="*60)
    print(" ❌ KHÔNG TÌM THẤY CẤU HÌNH NÀO HOẠT ĐỘNG")
    print("="*60)
    print("""
💡 Các nguyên nhân có thể:
1. LCD không phải ST7789 - kiểm tra chip driver trên module
2. Dây SDA/SCL bị đảo - thử đổi 2 dây GPIO 10 và 11
3. Module LCD bị lỗi - thử với LCD khác
4. SPI không hoạt động: chạy 'ls -la /dev/spidev*'
5. Nguồn điện yếu - thử nguồn USB khác mạnh hơn

📌 Chạy lệnh sau để kiểm tra SPI:
   dmesg | grep -i spi
   ls -la /dev/spidev*
""")
    cleanup()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nĐã hủy bởi người dùng")
    finally:
        cleanup()
