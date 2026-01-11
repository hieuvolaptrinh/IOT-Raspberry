#!/usr/bin/env python3
"""
Test LCD 1.54" ST7789 240x240
Dành riêng cho màn hình 1.54 inch với offset đúng
"""

import spidev
import RPi.GPIO as GPIO
from PIL import Image
import time
import struct

# GPIO pins (BCM numbering)
DC_PIN = 24    # Pin 18
RST_PIN = 25   # Pin 22  
BL_PIN = 18    # Pin 12

# LCD 1.54" có offset khác
WIDTH = 240
HEIGHT = 240
X_OFFSET = 0
Y_OFFSET = 0

# Rotation: 0, 1, 2, 3 (0°, 90°, 180°, 270°)
ROTATION = 0

class ST7789_154:
    def __init__(self):
        self.width = WIDTH
        self.height = HEIGHT
        
        # Setup GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(DC_PIN, GPIO.OUT)
        GPIO.setup(RST_PIN, GPIO.OUT)
        GPIO.setup(BL_PIN, GPIO.OUT)
        
        # Setup SPI
        self.spi = spidev.SpiDev()
        self.spi.open(0, 0)
        self.spi.max_speed_hz = 40000000  # 40MHz
        self.spi.mode = 0
        
        # Turn on backlight
        GPIO.output(BL_PIN, GPIO.HIGH)
        
        # Initialize display
        self._init_display()
    
    def _command(self, cmd):
        GPIO.output(DC_PIN, GPIO.LOW)
        self.spi.writebytes([cmd])
    
    def _data(self, data):
        GPIO.output(DC_PIN, GPIO.HIGH)
        if isinstance(data, int):
            self.spi.writebytes([data])
        else:
            # Split into chunks for large data
            chunk_size = 4096
            for i in range(0, len(data), chunk_size):
                self.spi.writebytes(data[i:i+chunk_size])
    
    def _reset(self):
        GPIO.output(RST_PIN, GPIO.HIGH)
        time.sleep(0.05)
        GPIO.output(RST_PIN, GPIO.LOW)
        time.sleep(0.05)
        GPIO.output(RST_PIN, GPIO.HIGH)
        time.sleep(0.15)
    
    def _init_display(self):
        self._reset()
        
        # Sleep out
        self._command(0x11)
        time.sleep(0.12)
        
        # Memory Data Access Control
        self._command(0x36)
        if ROTATION == 0:
            self._data(0x00)
        elif ROTATION == 1:
            self._data(0x60)
        elif ROTATION == 2:
            self._data(0xC0)
        elif ROTATION == 3:
            self._data(0xA0)
        
        # Interface Pixel Format (16-bit RGB565)
        self._command(0x3A)
        self._data(0x55)
        
        # Porch Setting
        self._command(0xB2)
        self._data([0x0C, 0x0C, 0x00, 0x33, 0x33])
        
        # Gate Control
        self._command(0xB7)
        self._data(0x35)
        
        # VCOM Setting
        self._command(0xBB)
        self._data(0x19)
        
        # LCM Control
        self._command(0xC0)
        self._data(0x2C)
        
        # VDV and VRH Command Enable
        self._command(0xC2)
        self._data(0x01)
        
        # VRH Set
        self._command(0xC3)
        self._data(0x12)
        
        # VDV Set
        self._command(0xC4)
        self._data(0x20)
        
        # Frame Rate Control
        self._command(0xC6)
        self._data(0x0F)
        
        # Power Control 1
        self._command(0xD0)
        self._data([0xA4, 0xA1])
        
        # Positive Voltage Gamma
        self._command(0xE0)
        self._data([0xD0, 0x04, 0x0D, 0x11, 0x13, 0x2B, 0x3F, 0x54, 0x4C, 0x18, 0x0D, 0x0B, 0x1F, 0x23])
        
        # Negative Voltage Gamma
        self._command(0xE1)
        self._data([0xD0, 0x04, 0x0C, 0x11, 0x13, 0x2C, 0x3F, 0x44, 0x51, 0x2F, 0x1F, 0x1F, 0x20, 0x23])
        
        # Display Inversion On (một số màn hình cần, một số không)
        self._command(0x21)
        
        # Display On
        self._command(0x29)
        time.sleep(0.1)
        
        print("Display initialized!")
    
    def set_window(self, x0, y0, x1, y1):
        # Column Address Set
        self._command(0x2A)
        self._data([
            (x0 + X_OFFSET) >> 8,
            (x0 + X_OFFSET) & 0xFF,
            (x1 + X_OFFSET) >> 8,
            (x1 + X_OFFSET) & 0xFF
        ])
        
        # Row Address Set
        self._command(0x2B)
        self._data([
            (y0 + Y_OFFSET) >> 8,
            (y0 + Y_OFFSET) & 0xFF,
            (y1 + Y_OFFSET) >> 8,
            (y1 + Y_OFFSET) & 0xFF
        ])
        
        # Memory Write
        self._command(0x2C)
    
    def display(self, image):
        """Display a PIL Image"""
        if image.size != (self.width, self.height):
            image = image.resize((self.width, self.height))
        
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Convert to RGB565
        pixels = list(image.getdata())
        buffer = []
        for r, g, b in pixels:
            # RGB565: RRRRRGGG GGGBBBBB
            rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
            buffer.append(rgb565 >> 8)
            buffer.append(rgb565 & 0xFF)
        
        self.set_window(0, 0, self.width - 1, self.height - 1)
        self._data(buffer)
    
    def fill(self, color):
        """Fill screen with RGB tuple"""
        image = Image.new('RGB', (self.width, self.height), color)
        self.display(image)
    
    def cleanup(self):
        GPIO.cleanup()
        self.spi.close()


if __name__ == "__main__":
    print("="*50)
    print("TEST LCD 1.54 inch ST7789")
    print("="*50)
    
    lcd = ST7789_154()
    
    print("\nTest 1: Màu đỏ...")
    lcd.fill((255, 0, 0))
    time.sleep(2)
    
    print("Test 2: Màu xanh lá...")
    lcd.fill((0, 255, 0))
    time.sleep(2)
    
    print("Test 3: Màu xanh dương...")
    lcd.fill((0, 0, 255))
    time.sleep(2)
    
    print("Test 4: Màu trắng...")
    lcd.fill((255, 255, 255))
    time.sleep(2)
    
    print("Test 5: Màu đen...")
    lcd.fill((0, 0, 0))
    time.sleep(1)
    
    print("\n✅ Test hoàn tất!")
    print("Nếu màn hình hiển thị đúng các màu → LCD hoạt động OK!")
    print("Nếu màu bị đảo ngược (ví dụ: đỏ thành xanh) → Cần điều chỉnh ROTATION")
    
    lcd.cleanup()
