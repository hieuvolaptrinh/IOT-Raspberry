#!/usr/bin/env python3
"""
Hiển thị chữ "Hello" trên màn hình TFT ST7789 1.54"
Raspberry Pi 2.0 WH
"""
import st7789
from PIL import Image, ImageDraw, ImageFont
import time
import sys

# ============ CẤU HÌNH PIN ============
# Điều chỉnh theo cách bạn kết nối
PORT = 0
CS = 0          # CE0 (GPIO8, pin 24)
DC = 24         # GPIO24 (pin 18)  - Data/Command
RST = 25        # GPIO25 (pin 22) - Reset
BL = 18         # GPIO18 (pin 12) - Backlight

# ============ CẤU HÌNH MÀN HÌNH ============
WIDTH = 240
HEIGHT = 240
ROTATION = 0        # Thử 0, 90, 180, 270 nếu không đúng
INVERT = True       # ST7789 1.54" thường cần invert=True
SPI_SPEED = 40_000_000  # 40MHz, giảm xuống 10MHz nếu không ổn định

def check_python_version():
    """Kiểm tra version Python"""
    version = sys.version_info
    print(f"Python version: {version.major}.{version.minor}.{version.micro}")
    
    if version.major == 3 and version.minor >= 13:
        print("⚠️  CẢNH BÁO: Python 3.13+ có thể không tương thích với st7789!")
        print("   Khuyến nghị dùng Python 3.9-3.11")
        print("   Cài đặt: sudo apt install python3.11 python3.11-pip")
        print("   Chạy: python3.11 display_hello.py")
        print()
    return version

def init_display():
    """Khởi tạo màn hình LCD"""
    print("Đang khởi tạo màn hình ST7789...")
    
    try:
        disp = st7789.ST7789(
            port=PORT,
            cs=CS,
            dc=DC,
            rst=RST,
            backlight=BL,
            width=WIDTH,
            height=HEIGHT,
            rotation=ROTATION,
            invert=INVERT,
            spi_speed_hz=SPI_SPEED,
            offset_left=0,
            offset_top=0
        )
        disp.begin()
        print("✓ Khởi tạo thành công!")
        return disp
    except Exception as e:
        print(f"✗ Lỗi khởi tạo: {e}")
        print("\nKiểm tra:")
        print("  1. SPI đã được bật? (sudo raspi-config -> Interface -> SPI)")
        print("  2. Thư viện đã cài? (pip install st7789 spidev RPi.GPIO pillow)")
        print("  3. Kết nối dây đúng chưa?")
        return None

def display_hello(disp):
    """Hiển thị chữ Hello trên màn hình"""
    # Tạo image nền đen
    img = Image.new("RGB", (WIDTH, HEIGHT), color=(0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Thử load font, nếu không có thì dùng font mặc định
    try:
        # Font lớn - thử nhiều đường dẫn
        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
            "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
        ]
        font = None
        for path in font_paths:
            try:
                font = ImageFont.truetype(path, 48)
                break
            except:
                continue
        
        if font is None:
            font = ImageFont.load_default()
            print("Dùng font mặc định (nhỏ)")
    except:
        font = ImageFont.load_default()
    
    # Vẽ chữ "Hello" ở giữa màn hình
    text = "Hello"
    
    # Tính vị trí căn giữa
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (WIDTH - text_width) // 2
    y = (HEIGHT - text_height) // 2
    
    # Vẽ text màu trắng
    draw.text((x, y), text, font=font, fill=(255, 255, 255))
    
    # Vẽ thêm dòng nhỏ bên dưới
    try:
        small_font = ImageFont.truetype(font_paths[0], 20)
    except:
        small_font = ImageFont.load_default()
    
    sub_text = "ST7789 1.54\" LCD"
    bbox2 = draw.textbbox((0, 0), sub_text, font=small_font)
    sub_width = bbox2[2] - bbox2[0]
    draw.text(((WIDTH - sub_width) // 2, y + text_height + 20), 
              sub_text, font=small_font, fill=(0, 255, 0))
    
    # Hiển thị lên màn hình
    disp.display(img)
    print("✓ Đã hiển thị 'Hello' trên màn hình!")

def display_colors_test(disp):
    """Test hiển thị các màu cơ bản"""
    colors = [
        ("Đỏ", (255, 0, 0)),
        ("Xanh lá", (0, 255, 0)),
        ("Xanh dương", (0, 0, 255)),
        ("Trắng", (255, 255, 255)),
        ("Vàng", (255, 255, 0)),
    ]
    
    for name, color in colors:
        print(f"  Hiển thị màu: {name}")
        img = Image.new("RGB", (WIDTH, HEIGHT), color=color)
        disp.display(img)
        time.sleep(0.5)

def main():
    print("=" * 50)
    print(" HIỂN THỊ 'HELLO' - ST7789 1.54\" TFT LCD")
    print("=" * 50)
    
    # Kiểm tra Python version
    check_python_version()
    
    # Khởi tạo display
    disp = init_display()
    if disp is None:
        return
    
    # Test màu trước
    print("\n--- Test màu cơ bản ---")
    display_colors_test(disp)
    
    # Hiển thị Hello
    print("\n--- Hiển thị Hello ---")
    display_hello(disp)
    
    print("\n✓ Hoàn tất! Chữ 'Hello' đang hiển thị trên màn hình.")
    print("  Nhấn Ctrl+C để thoát.")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nThoát.")

if __name__ == "__main__":
    main()
