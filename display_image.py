#!/usr/bin/env python3
"""
ST7789 LCD Display Module - SPI Mode 3
Raspberry Pi Zero 2 W + ST7789 1.54" 240x240 LCD (Màn hình Trung Quốc)

Cấu hình đã test thành công:
- SPI Mode: 3 (CPOL=1, CPHA=1)
- SPI Speed: 40MHz (có thể dùng 1-40MHz đều hoạt động)
- DC: GPIO24
- RST: GPIO25
- BL: GPIO18
"""
import spidev
import RPi.GPIO as GPIO
import time
from PIL import Image

# ============ CẤU HÌNH ============
DC_PIN = 24       # Data/Command
RST_PIN = 25      # Reset
BL_PIN = 18       # Backlight

SPI_MODE = 3      # QUAN TRỌNG: Phải dùng Mode 3 cho màn hình TQ
SPI_SPEED = 40000000  # 40MHz

WIDTH = 240
HEIGHT = 240


class ST7789Display:
    """Driver cho ST7789 LCD sử dụng SPI Mode 3"""
    
    def __init__(self, dc=DC_PIN, rst=RST_PIN, bl=BL_PIN, 
                 spi_mode=SPI_MODE, spi_speed=SPI_SPEED):
        self.dc = dc
        self.rst = rst
        self.bl = bl
        self.spi_mode = spi_mode
        self.spi_speed = spi_speed
        
        # Setup GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(self.dc, GPIO.OUT)
        GPIO.setup(self.rst, GPIO.OUT)
        GPIO.setup(self.bl, GPIO.OUT)
        
        # Setup SPI với Mode 3
        self.spi = spidev.SpiDev()
        self.spi.open(0, 0)
        self.spi.max_speed_hz = self.spi_speed
        self.spi.mode = self.spi_mode
        
        # Bật backlight
        GPIO.output(self.bl, GPIO.HIGH)
        
        # Khởi tạo display
        self._init_display()
    
    def _send_cmd(self, cmd):
        GPIO.output(self.dc, GPIO.LOW)
        self.spi.xfer2([cmd])
    
    def _send_data(self, data):
        GPIO.output(self.dc, GPIO.HIGH)
        if isinstance(data, int):
            self.spi.xfer2([data])
        else:
            data = list(data)
            for i in range(0, len(data), 4096):
                self.spi.xfer2(data[i:i+4096])
    
    def _reset(self):
        GPIO.output(self.rst, GPIO.HIGH)
        time.sleep(0.05)
        GPIO.output(self.rst, GPIO.LOW)
        time.sleep(0.05)
        GPIO.output(self.rst, GPIO.HIGH)
        time.sleep(0.2)
    
    def _init_display(self):
        """Khởi tạo ST7789"""
        self._reset()
        
        self._send_cmd(0x01)  # Software Reset
        time.sleep(0.15)
        
        self._send_cmd(0x11)  # Sleep Out
        time.sleep(0.15)
        
        self._send_cmd(0x36)  # MADCTL
        self._send_data(0x00)
        
        self._send_cmd(0x3A)  # Pixel Format - 16bit RGB565
        self._send_data(0x55)
        
        self._send_cmd(0xB2)  # Porch Setting
        self._send_data([0x0C, 0x0C, 0x00, 0x33, 0x33])
        
        self._send_cmd(0xB7)  # Gate Control
        self._send_data(0x35)
        
        self._send_cmd(0xBB)  # VCOM
        self._send_data(0x28)
        
        self._send_cmd(0xC0)  # LCM Control
        self._send_data(0x0C)
        
        self._send_cmd(0xC2)  # VDV VRH Enable
        self._send_data([0x01, 0xFF])
        
        self._send_cmd(0xC3)  # VRH Set
        self._send_data(0x10)
        
        self._send_cmd(0xC4)  # VDV Set
        self._send_data(0x20)
        
        self._send_cmd(0xC6)  # Frame Rate
        self._send_data(0x0F)
        
        self._send_cmd(0xD0)  # Power Control
        self._send_data([0xA4, 0xA1])
        
        self._send_cmd(0x21)  # Display Inversion ON
        
        self._send_cmd(0x13)  # Normal Mode
        time.sleep(0.01)
        
        self._send_cmd(0x29)  # Display ON
        time.sleep(0.15)
    
    def display_image(self, image_path):
        """Hiển thị ảnh từ file"""
        img = Image.open(image_path)
        self.display(img)
    
    def display(self, img):
        """Hiển thị PIL Image"""
        # Resize nếu cần
        if img.size != (WIDTH, HEIGHT):
            img = img.resize((WIDTH, HEIGHT), Image.LANCZOS)
        
        # Convert sang RGB
        if img.mode != "RGB":
            img = img.convert("RGB")
        
        # Set window
        self._send_cmd(0x2A)  # Column Address
        self._send_data([0x00, 0x00, 0x00, 0xEF])
        
        self._send_cmd(0x2B)  # Row Address
        self._send_data([0x00, 0x00, 0x00, 0xEF])
        
        self._send_cmd(0x2C)  # Write RAM
        
        # Convert RGB888 to RGB565
        pixels = img.tobytes()
        buffer = []
        for i in range(0, len(pixels), 3):
            r = pixels[i]
            g = pixels[i + 1]
            b = pixels[i + 2]
            # RGB565: RRRRRGGG GGGBBBBB
            c565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
            buffer.append((c565 >> 8) & 0xFF)
            buffer.append(c565 & 0xFF)
        
        self._send_data(buffer)
    
    def fill(self, color):
        """Fill màn hình với màu (r, g, b) hoặc tên màu"""
        if isinstance(color, str):
            from PIL import ImageColor
            r, g, b = ImageColor.getrgb(color)
        else:
            r, g, b = color
        
        self._send_cmd(0x2A)
        self._send_data([0x00, 0x00, 0x00, 0xEF])
        self._send_cmd(0x2B)
        self._send_data([0x00, 0x00, 0x00, 0xEF])
        self._send_cmd(0x2C)
        
        c565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
        buffer = [(c565 >> 8) & 0xFF, c565 & 0xFF] * (WIDTH * HEIGHT)
        self._send_data(buffer)
    
    def set_backlight(self, on):
        """Bật/tắt backlight"""
        GPIO.output(self.bl, GPIO.HIGH if on else GPIO.LOW)
    
    def cleanup(self):
        """Dọn dẹp tài nguyên"""
        self.spi.close()
        GPIO.cleanup()


# ============ MAIN ============
if __name__ == "__main__":
    print("=" * 50)
    print(" ST7789 LCD - Hiển thị hình ảnh")
    print(" SPI Mode 3 | 240x240 | Raspberry Pi Zero 2 W")
    print("=" * 50)
    
    display = None
    try:
        print("\n[1] Khởi tạo display...")
        display = ST7789Display()
        print("    ✓ Thành công!")
        
        print("\n[2] Hiển thị hình ảnh...")
        display.display_image("logo.JPG")
        print("    ✓ Đã hiển thị logo.JPG!")
        
        print("\n" + "=" * 50)
        print(" ✓ HOÀN TẤT!")
        print("=" * 50)
        print("\nNhấn Ctrl+C để thoát...")
        
        while True:
            time.sleep(1)
            
    except FileNotFoundError:
        print("\n❌ Không tìm thấy file image.png!")
        print("   Đảm bảo file nằm cùng thư mục với script.")
    except KeyboardInterrupt:
        print("\n\nĐang thoát...")
    except Exception as e:
        print(f"\n❌ Lỗi: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if display:
            display.cleanup()
        print("✓ Cleanup xong!")
