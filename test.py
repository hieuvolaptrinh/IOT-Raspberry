#!/usr/bin/env python3
"""
Hardware Debug Test for ST7789 1.54" LCD
Direct SPI communication - bypass library issues
"""
import RPi.GPIO as GPIO
import spidev
import time

# GPIO Configuration
DC = 25     # Data/Command
RST = 27    # Reset
BL = 18     # Backlight
CS = 8      # Chip Select (CE0)

# Display size
WIDTH = 240
HEIGHT = 240

class ST7789_Direct:
    def __init__(self):
        # Setup GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        GPIO.setup(DC, GPIO.OUT)
        GPIO.setup(RST, GPIO.OUT)
        GPIO.setup(BL, GPIO.OUT)
        
        # Setup SPI
        self.spi = spidev.SpiDev()
        self.spi.open(0, 0)
        self.spi.max_speed_hz = 40000000
        self.spi.mode = 0
        
        # Turn on backlight
        GPIO.output(BL, GPIO.HIGH)
        
        # Initialize display
        self._init_display()
    
    def _command(self, cmd):
        """Send command"""
        GPIO.output(DC, GPIO.LOW)
        self.spi.xfer2([cmd])
    
    def _data(self, data):
        """Send data"""
        GPIO.output(DC, GPIO.HIGH)
        if isinstance(data, list):
            self.spi.xfer2(data)
        else:
            self.spi.xfer2([data])
    
    def _reset(self):
        """Hardware reset"""
        GPIO.output(RST, GPIO.HIGH)
        time.sleep(0.05)
        GPIO.output(RST, GPIO.LOW)
        time.sleep(0.05)
        GPIO.output(RST, GPIO.HIGH)
        time.sleep(0.15)
    
    def _init_display(self):
        """Initialize ST7789 display"""
        print("Đang khởi tạo ST7789...")
        
        self._reset()
        
        # Software reset
        self._command(0x01)
        time.sleep(0.15)
        
        # Sleep out
        self._command(0x11)
        time.sleep(0.15)
        
        # Memory Data Access Control
        self._command(0x36)
        self._data(0x00)
        
        # Interface Pixel Format - 16bit/pixel
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
        
        # Positive Voltage Gamma Control
        self._command(0xE0)
        self._data([0xD0, 0x04, 0x0D, 0x11, 0x13, 0x2B, 0x3F, 0x54, 0x4C, 0x18, 0x0D, 0x0B, 0x1F, 0x23])
        
        # Negative Voltage Gamma Control
        self._command(0xE1)
        self._data([0xD0, 0x04, 0x0C, 0x11, 0x13, 0x2C, 0x3F, 0x44, 0x51, 0x2F, 0x1F, 0x1F, 0x20, 0x23])
        
        # Display Inversion On (some displays need this)
        self._command(0x21)
        
        # Display ON
        self._command(0x29)
        time.sleep(0.1)
        
        print("✓ Khởi tạo hoàn tất!")
    
    def set_window(self, x0, y0, x1, y1):
        """Set display window"""
        # Column Address Set
        self._command(0x2A)
        self._data([x0 >> 8, x0 & 0xFF, x1 >> 8, x1 & 0xFF])
        
        # Row Address Set
        self._command(0x2B)
        self._data([y0 >> 8, y0 & 0xFF, y1 >> 8, y1 & 0xFF])
        
        # Memory Write
        self._command(0x2C)
    
    def fill_color(self, color):
        """Fill entire screen with RGB565 color"""
        print(f"Đang fill màn hình với màu 0x{color:04X}...")
        
        self.set_window(0, 0, WIDTH - 1, HEIGHT - 1)
        
        # Prepare color data
        high = (color >> 8) & 0xFF
        low = color & 0xFF
        
        GPIO.output(DC, GPIO.HIGH)
        
        # Send in chunks for speed
        chunk_size = 4096
        pixel_data = [high, low] * (chunk_size // 2)
        total_pixels = WIDTH * HEIGHT
        
        for i in range(0, total_pixels * 2, chunk_size):
            remaining = min(chunk_size, total_pixels * 2 - i)
            self.spi.xfer2(pixel_data[:remaining])
        
        print("✓ Fill hoàn tất!")
    
    def fill_test_pattern(self):
        """Display test pattern with multiple colors"""
        print("Đang hiển thị test pattern...")
        
        colors = [
            (0xF800, "Đỏ"),      # Red
            (0x07E0, "Xanh lá"), # Green
            (0x001F, "Xanh dương"), # Blue
            (0xFFE0, "Vàng"),    # Yellow
            (0xFFFF, "Trắng"),   # White
        ]
        
        section_height = HEIGHT // len(colors)
        
        for i, (color, name) in enumerate(colors):
            y0 = i * section_height
            y1 = (i + 1) * section_height - 1
            
            self.set_window(0, y0, WIDTH - 1, y1)
            
            high = (color >> 8) & 0xFF
            low = color & 0xFF
            
            GPIO.output(DC, GPIO.HIGH)
            
            pixels = section_height * WIDTH
            chunk_size = 4096
            pixel_data = [high, low] * (chunk_size // 2)
            
            for j in range(0, pixels * 2, chunk_size):
                remaining = min(chunk_size, pixels * 2 - j)
                self.spi.xfer2(pixel_data[:remaining])
            
            print(f"  ✓ {name}")
        
        print("✓ Test pattern hoàn tất!")
    
    def cleanup(self):
        """Cleanup GPIO"""
        self.spi.close()
        GPIO.cleanup()


def main():
    print("=" * 50)
    print("  ST7789 Direct SPI Test")
    print("=" * 50)
    print()
    
    try:
        display = ST7789_Direct()
        
        # Test 1: Fill đỏ
        print("\n[TEST 1] Fill màu ĐỎ...")
        display.fill_color(0xF800)
        input("Nhấn Enter để tiếp tục...")
        
        # Test 2: Fill xanh lá
        print("\n[TEST 2] Fill màu XANH LÁ...")
        display.fill_color(0x07E0)
        input("Nhấn Enter để tiếp tục...")
        
        # Test 3: Fill xanh dương
        print("\n[TEST 3] Fill màu XANH DƯƠNG...")
        display.fill_color(0x001F)
        input("Nhấn Enter để tiếp tục...")
        
        # Test 4: Pattern
        print("\n[TEST 4] Test pattern nhiều màu...")
        display.fill_test_pattern()
        
        print("\n" + "=" * 50)
        print("  TEST HOÀN TẤT!")
        print("=" * 50)
        print("\nBạn có thấy màu sắc trên màn hình không?")
        print("- Nếu CÓ: LCD hoạt động tốt!")
        print("- Nếu KHÔNG: Có thể LCD bị lỗi hoặc cần kiểm tra dây")
        print("\nNhấn Ctrl+C để thoát...")
        
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nĐã dừng.")
    except Exception as e:
        print(f"\n❌ Lỗi: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            display.cleanup()
        except:
            pass


if __name__ == "__main__":
    main()