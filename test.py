#!/usr/bin/env python3
"""
ST7789 LCD - RAW SPI DRIVER (Không cần thư viện ngoài)
Raspberry Pi Zero 2 W + ST7789 1.54" 240x240 LCD
Chỉ dùng: spidev, RPi.GPIO, Pillow

=============================================
         SƠ ĐỒ NỐI DÂY (8 PIN)
=============================================
LCD         Raspberry Pi Zero 2 W
-----       ----------------------
GND    -->  Pin 6  (GND)
VCC    -->  Pin 1  (3.3V)
SCL    -->  Pin 23 (GPIO11 - SCLK)
SDA    -->  Pin 19 (GPIO10 - MOSI)
DC     -->  Pin 22 (GPIO25)
RST    -->  Pin 18 (GPIO24)
CS     -->  Pin 24 (GPIO8 - CE0)
BL     -->  Pin 12 (GPIO18)
=============================================
"""

import time
import struct
import spidev
import RPi.GPIO as GPIO
from PIL import Image, ImageDraw, ImageFont

# ============ PIN CONFIG (BCM) ============
DC_PIN = 25    # Data/Command - Pin 22
RST_PIN = 24   # Reset - Pin 18
BL_PIN = 18    # Backlight - Pin 12

# ============ DISPLAY CONFIG ============
WIDTH = 240
HEIGHT = 240
ROTATION = 0   # 0, 1, 2, 3

# ============ SPI CONFIG ============
SPI_SPEED = 62500000  # 62.5MHz max cho ST7789
SPI_MODE = 0

# ============ ROTATION SETTINGS ============
MADCTL_ROTATION = {
    0: 0x00,   # 0 degree
    1: 0x60,   # 90 degree
    2: 0xC0,   # 180 degree
    3: 0xA0,   # 270 degree
}


class ST7789:
    """Raw SPI driver cho ST7789"""
    
    def __init__(self, dc=DC_PIN, rst=RST_PIN, bl=BL_PIN, 
                 width=WIDTH, height=HEIGHT, rotation=ROTATION,
                 spi_speed=SPI_SPEED):
        self.dc = dc
        self.rst = rst
        self.bl = bl
        self.width = width
        self.height = height
        self.rotation = rotation
        self.spi_speed = spi_speed
        
        # Setup GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(self.dc, GPIO.OUT)
        GPIO.setup(self.rst, GPIO.OUT)
        GPIO.setup(self.bl, GPIO.OUT)
        
        # Setup SPI
        self.spi = spidev.SpiDev()
        self.spi.open(0, 0)
        self.spi.max_speed_hz = self.spi_speed
        self.spi.mode = SPI_MODE
        
        # Backlight ON
        GPIO.output(self.bl, GPIO.HIGH)
        
        # Initialize display
        self._init_display()
    
    def _write_cmd(self, cmd):
        """Gửi command"""
        GPIO.output(self.dc, GPIO.LOW)
        self.spi.xfer2([cmd])
    
    def _write_data(self, data):
        """Gửi data"""
        GPIO.output(self.dc, GPIO.HIGH)
        if isinstance(data, int):
            self.spi.xfer2([data])
        elif isinstance(data, (list, bytes, bytearray)):
            # Gửi từng chunk 4096 bytes
            data = list(data)
            for i in range(0, len(data), 4096):
                self.spi.xfer2(data[i:i+4096])
    
    def _hardware_reset(self):
        """Hardware reset"""
        GPIO.output(self.rst, GPIO.HIGH)
        time.sleep(0.01)
        GPIO.output(self.rst, GPIO.LOW)
        time.sleep(0.01)
        GPIO.output(self.rst, GPIO.HIGH)
        time.sleep(0.15)
    
    def _init_display(self):
        """Khởi tạo ST7789"""
        self._hardware_reset()
        
        # Software Reset
        self._write_cmd(0x01)
        time.sleep(0.15)
        
        # Sleep Out
        self._write_cmd(0x11)
        time.sleep(0.12)
        
        # Memory Data Access Control
        self._write_cmd(0x36)
        madctl = MADCTL_ROTATION.get(self.rotation, 0x00)
        self._write_data(madctl)
        
        # Interface Pixel Format (16bit RGB565)
        self._write_cmd(0x3A)
        self._write_data(0x55)
        
        # Porch Setting
        self._write_cmd(0xB2)
        self._write_data([0x0C, 0x0C, 0x00, 0x33, 0x33])
        
        # Gate Control
        self._write_cmd(0xB7)
        self._write_data(0x35)
        
        # VCOM Setting
        self._write_cmd(0xBB)
        self._write_data(0x28)
        
        # LCM Control
        self._write_cmd(0xC0)
        self._write_data(0x0C)
        
        # VDV and VRH Command Enable
        self._write_cmd(0xC2)
        self._write_data([0x01, 0xFF])
        
        # VRH Set
        self._write_cmd(0xC3)
        self._write_data(0x10)
        
        # VDV Set
        self._write_cmd(0xC4)
        self._write_data(0x20)
        
        # Frame Rate Control
        self._write_cmd(0xC6)
        self._write_data(0x0F)
        
        # Power Control 1
        self._write_cmd(0xD0)
        self._write_data([0xA4, 0xA1])
        
        # Positive Voltage Gamma
        self._write_cmd(0xE0)
        self._write_data([
            0xD0, 0x00, 0x02, 0x07, 0x0A, 0x28, 0x32, 0x44,
            0x42, 0x06, 0x0E, 0x12, 0x14, 0x17
        ])
        
        # Negative Voltage Gamma
        self._write_cmd(0xE1)
        self._write_data([
            0xD0, 0x00, 0x02, 0x07, 0x0A, 0x28, 0x31, 0x54,
            0x47, 0x0E, 0x1C, 0x17, 0x1B, 0x1E
        ])
        
        # Display Inversion ON (cần cho hầu hết ST7789)
        self._write_cmd(0x21)
        
        # Normal Display Mode ON
        self._write_cmd(0x13)
        time.sleep(0.01)
        
        # Display ON
        self._write_cmd(0x29)
        time.sleep(0.12)
    
    def _set_window(self, x0, y0, x1, y1):
        """Set vùng vẽ"""
        # Column address
        self._write_cmd(0x2A)
        self._write_data([x0 >> 8, x0 & 0xFF, x1 >> 8, x1 & 0xFF])
        
        # Row address
        self._write_cmd(0x2B)
        self._write_data([y0 >> 8, y0 & 0xFF, y1 >> 8, y1 & 0xFF])
        
        # Write to RAM
        self._write_cmd(0x2C)
    
    def fill(self, color):
        """Fill màn hình với màu RGB tuple hoặc hex"""
        if isinstance(color, tuple):
            r, g, b = color
        elif isinstance(color, str):
            # Convert color name to RGB
            from PIL import ImageColor
            r, g, b = ImageColor.getrgb(color)
        else:
            r, g, b = color, color, color
        
        # Convert RGB888 to RGB565
        c565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
        high = (c565 >> 8) & 0xFF
        low = c565 & 0xFF
        
        self._set_window(0, 0, self.width - 1, self.height - 1)
        
        # Tạo buffer
        size = self.width * self.height
        buffer = [high, low] * size
        self._write_data(buffer)
    
    def image(self, img):
        """Hiển thị PIL Image"""
        if img.size != (self.width, self.height):
            img = img.resize((self.width, self.height))
        
        if img.mode != "RGB":
            img = img.convert("RGB")
        
        self._set_window(0, 0, self.width - 1, self.height - 1)
        
        # Convert to RGB565
        pixels = img.tobytes()
        buffer = []
        for i in range(0, len(pixels), 3):
            r = pixels[i]
            g = pixels[i + 1]
            b = pixels[i + 2]
            c565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
            buffer.append((c565 >> 8) & 0xFF)
            buffer.append(c565 & 0xFF)
        
        self._write_data(buffer)
    
    def text(self, text, font_size=48, color="white", bg="black"):
        """Hiển thị text ở giữa màn hình"""
        img = Image.new("RGB", (self.width, self.height), bg)
        draw = ImageDraw.Draw(img)
        
        try:
            font = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 
                font_size
            )
        except:
            font = ImageFont.load_default()
        
        bbox = draw.textbbox((0, 0), text, font=font)
        x = (self.width - (bbox[2] - bbox[0])) // 2
        y = (self.height - (bbox[3] - bbox[1])) // 2
        draw.text((x, y), text, font=font, fill=color)
        
        self.image(img)
    
    def cleanup(self):
        """Dọn dẹp"""
        self.spi.close()
        GPIO.cleanup()


def main():
    print("=" * 50)
    print("  ST7789 RAW SPI DRIVER")
    print("=" * 50)
    
    disp = None
    try:
        print("\n[1] Khởi tạo display...")
        disp = ST7789(
            dc=DC_PIN,
            rst=RST_PIN,
            bl=BL_PIN,
            width=WIDTH,
            height=HEIGHT,
            rotation=ROTATION,
            spi_speed=SPI_SPEED
        )
        print("✓ Khởi tạo thành công!")
        
        print("\n[2] Fill màu TRẮNG...")
        disp.fill("white")
        time.sleep(1)
        
        print("\n[3] Fill màu ĐỎ...")
        disp.fill("red")
        time.sleep(0.5)
        
        print("\n[4] Fill màu XANH LÁ...")
        disp.fill("green")
        time.sleep(0.5)
        
        print("\n[5] Fill màu XANH DƯƠNG...")
        disp.fill("blue")
        time.sleep(0.5)
        
        print("\n[6] Hiển thị 'Hello'...")
        disp.text("Hello", font_size=60, color="white", bg="navy")
        
        print("\n" + "=" * 50)
        print("  ✓ TEST HOÀN TẤT!")
        print("=" * 50)
        print("\nNhấn Ctrl+C để thoát...")
        
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\nĐang thoát...")
    except Exception as e:
        print(f"\n✗ Lỗi: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if disp:
            disp.cleanup()
        print("✓ Cleanup xong!")


if __name__ == "__main__":
    main()