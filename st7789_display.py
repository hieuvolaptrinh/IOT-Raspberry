#!/usr/bin/env python3
"""
ST7789 LCD với Adafruit CircuitPython / Blinka
Raspberry Pi Zero 2 W + ST7789 1.54" 240x240 LCD

=============================================
         SƠ ĐỒ NỐI DÂY (8 PIN)
=============================================
LCD         Raspberry Pi Zero 2 W
-----       ----------------------
GND    -->  Pin 6  (GND)
VCC    -->  Pin 1  (3.3V)
SCL    -->  Pin 23 (GPIO11 - SCLK)
SDA    -->  Pin 19 (GPIO10 - MOSI)
DC     -->  Pin 22 (GPIO25) ← ĐỔI
RST    -->  Pin 18 (GPIO24) ← ĐỔI
CS     -->  Pin 24 (GPIO8 - CE0)
BL     -->  Pin 12 (GPIO18)
=============================================

CÀI ĐẶT:
    pip install adafruit-blinka
    pip install adafruit-circuitpython-rgb-display
    pip install pillow
"""

import time
import digitalio
import board
from PIL import Image, ImageDraw, ImageFont
import adafruit_rgb_display.st7789 as st7789

# ============ CẤU HÌNH ============
# Theo chuẩn Adafruit
CS_PIN = board.CE0       # GPIO8
DC_PIN = board.D25       # GPIO25
RST_PIN = board.D24      # GPIO24 (có thể None nếu ko dùng)
BL_PIN = board.D18       # GPIO18 - Backlight

# Kích thước màn hình
WIDTH = 240
HEIGHT = 240
ROTATION = 180  # Thử 0, 90, 180, 270 nếu hình bị ngược

# Tốc độ SPI (Hz)
BAUDRATE = 24000000  # 24MHz


def init_display():
    """Khởi tạo màn hình ST7789"""
    print("Đang khởi tạo ST7789...")
    
    # Cấu hình pin
    cs = digitalio.DigitalInOut(CS_PIN)
    dc = digitalio.DigitalInOut(DC_PIN)
    rst = digitalio.DigitalInOut(RST_PIN)
    
    # Bật backlight
    bl = digitalio.DigitalInOut(BL_PIN)
    bl.direction = digitalio.Direction.OUTPUT
    bl.value = True
    print("  → Backlight: ON")
    
    # Khởi tạo SPI
    spi = board.SPI()
    
    # Tạo display object
    disp = st7789.ST7789(
        spi,
        cs=cs,
        dc=dc,
        rst=rst,
        baudrate=BAUDRATE,
        width=WIDTH,
        height=HEIGHT,
        x_offset=0,
        y_offset=0,
        rotation=ROTATION
    )
    
    print(f"  → Display: {WIDTH}x{HEIGHT}, rotation={ROTATION}")
    print("✓ Khởi tạo thành công!")
    
    return disp, bl


def fill_color(disp, color):
    """Fill toàn màn hình với 1 màu"""
    img = Image.new("RGB", (WIDTH, HEIGHT), color)
    disp.image(img)


def display_text(disp, text, font_size=48, text_color="white", bg_color="navy"):
    """Hiển thị text ở giữa màn hình"""
    # Tạo image
    img = Image.new("RGB", (WIDTH, HEIGHT), bg_color)
    draw = ImageDraw.Draw(img)
    
    # Load font
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
    except:
        font = ImageFont.load_default()
        print("  (Dùng font mặc định)")
    
    # Tính vị trí căn giữa
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (WIDTH - text_w) // 2
    y = (HEIGHT - text_h) // 2
    
    # Vẽ text
    draw.text((x, y), text, font=font, fill=text_color)
    
    # Hiển thị
    disp.image(img)


def test_pattern(disp):
    """Hiển thị test pattern"""
    img = Image.new("RGB", (WIDTH, HEIGHT), "black")
    draw = ImageDraw.Draw(img)
    
    # 4 góc màu khác nhau
    draw.rectangle([0, 0, 60, 60], fill="red")
    draw.rectangle([180, 0, 240, 60], fill="green")
    draw.rectangle([0, 180, 60, 240], fill="blue")
    draw.rectangle([180, 180, 240, 240], fill="yellow")
    
    # Chữ thập giữa
    draw.line([(120, 0), (120, 240)], fill="white", width=2)
    draw.line([(0, 120), (240, 120)], fill="white", width=2)
    
    # Viền
    draw.rectangle([0, 0, 239, 239], outline="white", width=2)
    
    disp.image(img)


def test_colors(disp):
    """Test các màu cơ bản"""
    colors = [
        ("red", "ĐỎ"),
        ("green", "XANH LÁ"),
        ("blue", "XANH DƯƠNG"),
        ("white", "TRẮNG"),
        ("yellow", "VÀNG"),
        ("cyan", "CYAN"),
        ("magenta", "HỒNG"),
        ("black", "ĐEN"),
    ]
    
    for color, name in colors:
        print(f"  → {name}")
        fill_color(disp, color)
        time.sleep(0.5)


def main():
    print("=" * 50)
    print("  ST7789 - ADAFRUIT CIRCUITPYTHON")
    print("=" * 50)
    
    try:
        # Khởi tạo
        print("\n[1] Khởi tạo display...")
        disp, bl = init_display()
        
        # Test màu trắng trước
        print("\n[2] Fill màu trắng...")
        fill_color(disp, "white")
        time.sleep(1)
        
        # Test pattern
        print("\n[3] Test pattern...")
        test_pattern(disp)
        time.sleep(1)
        
        # Test colors
        print("\n[4] Test các màu...")
        test_colors(disp)
        
        # Hello
        print("\n[5] Hiển thị 'Hello'...")
        display_text(disp, "Hello", font_size=60, text_color="white", bg_color="darkblue")
        
        print("\n" + "=" * 50)
        print("  ✓ TEST HOÀN TẤT!")
        print("=" * 50)
        print("\nNhấn Ctrl+C để thoát...")
        
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\nĐang thoát...")
    except Exception as e:
        print(f"\n✗ LỖI: {e}")
        import traceback
        traceback.print_exc()
        print("\n=== KIỂM TRA ===")
        print("1. Đã cài thư viện chưa?")
        print("   pip install adafruit-blinka adafruit-circuitpython-rgb-display pillow")
        print("2. SPI đã bật? sudo raspi-config → Interface → SPI")
        print("3. Dây nối đúng theo sơ đồ?")


if __name__ == "__main__":
    main()
