#!/usr/bin/env python3
"""
ST7789 LCD - RAW SPI DRIVER
Raspberry Pi Zero 2 W + ST7789 1.54" 240x240 LCD
Không dùng thư viện bên ngoài, chỉ spidev + RPi.GPIO

=============================================
         SƠ ĐỒ NỐI DÂY (8 PIN)
=============================================
LCD         Raspberry Pi Zero 2 W
-----       ----------------------
GND    -->  Pin 6  (GND)
VCC    -->  Pin 1  (3.3V)
SCL    -->  Pin 23 (GPIO11 - SCLK)
SDA    -->  Pin 19 (GPIO10 - MOSI)
DC     -->  Pin 18 (GPIO24)
RST    -->  Pin 22 (GPIO25)
CS     -->  Pin 24 (GPIO8 - CE0)
BL     -->  Pin 12 (GPIO18)
=============================================
"""

import time
import spidev
import RPi.GPIO as GPIO
from PIL import Image, ImageDraw, ImageFont

# ============ CẤU HÌNH GPIO (BCM) ============
DC_PIN = 24    # Data/Command - Pin 18
RST_PIN = 25   # Reset - Pin 22
BL_PIN = 18    # Backlight - Pin 12

# ============ CẤU HÌNH MÀN HÌNH ============
WIDTH = 240
HEIGHT = 240
X_OFFSET = 0   # Offset X (thử 0 hoặc 80 nếu bị lệch)
Y_OFFSET = 0   # Offset Y (thử 0 hoặc 80 nếu bị lệch)

# ============ SPI ============
SPI_SPEED = 40000000  # 40MHz (giảm xuống 10MHz nếu không ổn định)
SPI_MODE = 0b00       # Mode 0 cho ST7789

# ============ ST7789 COMMANDS ============
ST7789_NOP = 0x00
ST7789_SWRESET = 0x01
ST7789_SLPOUT = 0x11
ST7789_NORON = 0x13
ST7789_INVOFF = 0x20
ST7789_INVON = 0x21
ST7789_DISPOFF = 0x28
ST7789_DISPON = 0x29
ST7789_CASET = 0x2A
ST7789_RASET = 0x2B
ST7789_RAMWR = 0x2C
ST7789_MADCTL = 0x36
ST7789_COLMOD = 0x3A

# ============ GLOBAL SPI ============
spi = None


def init_gpio():
    """Khởi tạo GPIO"""
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(DC_PIN, GPIO.OUT)
    GPIO.setup(RST_PIN, GPIO.OUT)
    GPIO.setup(BL_PIN, GPIO.OUT)
    
    # Bật backlight
    GPIO.output(BL_PIN, GPIO.HIGH)
    print("✓ GPIO initialized, Backlight ON")


def init_spi():
    """Khởi tạo SPI"""
    global spi
    spi = spidev.SpiDev()
    spi.open(0, 0)  # Bus 0, Device 0 (CE0)
    spi.max_speed_hz = SPI_SPEED
    spi.mode = SPI_MODE
    print(f"✓ SPI initialized: {SPI_SPEED/1000000}MHz, Mode {SPI_MODE}")


def write_cmd(cmd):
    """Gửi command tới LCD"""
    GPIO.output(DC_PIN, GPIO.LOW)  # DC LOW = Command
    spi.xfer2([cmd])


def write_data(data):
    """Gửi data tới LCD"""
    GPIO.output(DC_PIN, GPIO.HIGH)  # DC HIGH = Data
    if isinstance(data, int):
        spi.xfer2([data])
    else:
        # Gửi từng chunk 4096 bytes
        for i in range(0, len(data), 4096):
            spi.xfer2(data[i:i+4096])


def hardware_reset():
    """Hardware reset LCD"""
    GPIO.output(RST_PIN, GPIO.HIGH)
    time.sleep(0.05)
    GPIO.output(RST_PIN, GPIO.LOW)
    time.sleep(0.05)
    GPIO.output(RST_PIN, GPIO.HIGH)
    time.sleep(0.15)
    print("✓ Hardware reset complete")


def init_display():
    """Khởi tạo ST7789"""
    print("\nInitializing ST7789...")
    
    # Hardware reset
    hardware_reset()
    
    # Software reset
    write_cmd(ST7789_SWRESET)
    time.sleep(0.15)
    
    # Sleep out
    write_cmd(ST7789_SLPOUT)
    time.sleep(0.12)
    
    # Memory Access Control (orientation)
    # 0x00: Normal
    # 0x60: Rotate 90
    # 0xC0: Rotate 180
    # 0xA0: Rotate 270
    write_cmd(ST7789_MADCTL)
    write_data(0x00)
    
    # Interface Pixel Format: 16bit/pixel (RGB565)
    write_cmd(ST7789_COLMOD)
    write_data(0x55)
    
    # Porch Setting
    write_cmd(0xB2)
    write_data([0x0C, 0x0C, 0x00, 0x33, 0x33])
    
    # Gate Control
    write_cmd(0xB7)
    write_data(0x35)
    
    # VCOM Setting
    write_cmd(0xBB)
    write_data(0x1F)
    
    # LCM Control
    write_cmd(0xC0)
    write_data(0x2C)
    
    # VDV and VRH Command Enable
    write_cmd(0xC2)
    write_data(0x01)
    
    # VRH Set
    write_cmd(0xC3)
    write_data(0x12)
    
    # VDV Set
    write_cmd(0xC4)
    write_data(0x20)
    
    # Frame Rate Control
    write_cmd(0xC6)
    write_data(0x0F)
    
    # Power Control 1
    write_cmd(0xD0)
    write_data([0xA4, 0xA1])
    
    # Positive Voltage Gamma Control
    write_cmd(0xE0)
    write_data([0xD0, 0x08, 0x11, 0x08, 0x0C, 0x15, 0x39, 0x33, 0x50, 0x36, 0x13, 0x14, 0x29, 0x2D])
    
    # Negative Voltage Gamma Control
    write_cmd(0xE1)
    write_data([0xD0, 0x08, 0x10, 0x08, 0x06, 0x06, 0x39, 0x44, 0x51, 0x0B, 0x16, 0x14, 0x2F, 0x31])
    
    # Display Inversion ON (thường cần cho ST7789 1.54")
    write_cmd(ST7789_INVON)
    
    # Normal Display Mode ON
    write_cmd(ST7789_NORON)
    time.sleep(0.01)
    
    # Display ON
    write_cmd(ST7789_DISPON)
    time.sleep(0.1)
    
    print("✓ ST7789 initialized")


def set_window(x0, y0, x1, y1):
    """Set vùng vẽ"""
    # Column address
    write_cmd(ST7789_CASET)
    write_data([
        (x0 + X_OFFSET) >> 8, (x0 + X_OFFSET) & 0xFF,
        (x1 + X_OFFSET) >> 8, (x1 + X_OFFSET) & 0xFF
    ])
    
    # Row address
    write_cmd(ST7789_RASET)
    write_data([
        (y0 + Y_OFFSET) >> 8, (y0 + Y_OFFSET) & 0xFF,
        (y1 + Y_OFFSET) >> 8, (y1 + Y_OFFSET) & 0xFF
    ])
    
    # Write to RAM
    write_cmd(ST7789_RAMWR)


def fill_screen(color):
    """Fill toàn màn hình với 1 màu (RGB565)"""
    set_window(0, 0, WIDTH - 1, HEIGHT - 1)
    
    high = (color >> 8) & 0xFF
    low = color & 0xFF
    
    # Tạo buffer
    buffer = [high, low] * (WIDTH * HEIGHT)
    write_data(buffer)


def fill_color_rgb(r, g, b):
    """Fill màn hình với màu RGB (0-255)"""
    # Convert RGB888 to RGB565
    color = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
    fill_screen(color)


def display_image(img):
    """Hiển thị PIL Image"""
    # Ensure correct size
    if img.size != (WIDTH, HEIGHT):
        img = img.resize((WIDTH, HEIGHT))
    
    # Convert to RGB
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    set_window(0, 0, WIDTH - 1, HEIGHT - 1)
    
    # Convert to RGB565
    pixels = list(img.getdata())
    buffer = []
    for r, g, b in pixels:
        color = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
        buffer.append((color >> 8) & 0xFF)
        buffer.append(color & 0xFF)
    
    write_data(buffer)


def display_text(text, font_size=48, text_color=(255, 255, 255), bg_color=(0, 0, 0)):
    """Hiển thị text ở giữa màn hình"""
    # Tạo image
    img = Image.new('RGB', (WIDTH, HEIGHT), bg_color)
    draw = ImageDraw.Draw(img)
    
    # Load font
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
    except:
        font = ImageFont.load_default()
    
    # Tính vị trí căn giữa
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (WIDTH - text_width) // 2
    y = (HEIGHT - text_height) // 2
    
    # Vẽ text
    draw.text((x, y), text, font=font, fill=text_color)
    
    # Hiển thị
    display_image(img)


def test_colors():
    """Test các màu cơ bản"""
    colors = [
        ("WHITE", 255, 255, 255),
        ("RED", 255, 0, 0),
        ("GREEN", 0, 255, 0),
        ("BLUE", 0, 0, 255),
        ("YELLOW", 255, 255, 0),
        ("CYAN", 0, 255, 255),
        ("MAGENTA", 255, 0, 255),
        ("BLACK", 0, 0, 0),
    ]
    
    for name, r, g, b in colors:
        print(f"  → {name}")
        fill_color_rgb(r, g, b)
        time.sleep(0.5)


def cleanup():
    """Dọn dẹp"""
    if spi:
        spi.close()
    GPIO.cleanup()
    print("✓ Cleanup complete")


def main():
    print("=" * 50)
    print("   ST7789 RAW SPI DRIVER TEST")
    print("=" * 50)
    
    try:
        # Initialize
        print("\n[1] Initializing GPIO...")
        init_gpio()
        
        print("\n[2] Initializing SPI...")
        init_spi()
        
        print("\n[3] Initializing Display...")
        init_display()
        
        # Test colors
        print("\n[4] Testing colors...")
        test_colors()
        
        # Display Hello
        print("\n[5] Displaying 'Hello'...")
        display_text("Hello", font_size=60, text_color=(255, 255, 255), bg_color=(0, 0, 128))
        
        print("\n" + "=" * 50)
        print("   TEST COMPLETE!")
        print("=" * 50)
        print("\nNếu không thấy gì, kiểm tra:")
        print("  1. Dây nối đúng theo sơ đồ?")
        print("  2. SPI đã bật? (sudo raspi-config)")
        print("  3. Thử giảm SPI_SPEED xuống 10000000")
        print("\nNhấn Ctrl+C để thoát...")
        
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\nExiting...")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cleanup()


if __name__ == "__main__":
    main()