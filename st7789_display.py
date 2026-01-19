#!/usr/bin/env python3
"""
Hiển thị hình ảnh trên màn hình ST7789 LCD bằng thư viện Luma
Raspberry Pi Zero 2 W + ST7789 1.54" SPI LCD

Cài đặt:
    pip install luma.lcd pillow

Nối dây:
    LCD Pin     Raspberry Pi
    -------     ------------
    GND         Pin 6  (GND)
    VCC         Pin 1  (3.3V)
    SCL         Pin 23 (GPIO11/SCLK)
    SDA         Pin 19 (GPIO10/MOSI)
    DC          Pin 18 (GPIO24)
    RST         Pin 22 (GPIO25)
    CS          Pin 24 (GPIO8/CE0)
    BL          Pin 12 (GPIO18)
"""

from luma.core.interface.serial import spi
from luma.lcd.device import st7789
from PIL import Image, ImageDraw, ImageFont
import time

# ============ CẤU HÌNH ============
DC_PIN = 24      # GPIO24 (Pin 18)
RST_PIN = 25     # GPIO25 (Pin 22)
BL_PIN = 18      # GPIO18 (Pin 12) - Backlight
WIDTH = 240
HEIGHT = 240

def init_display():
    """Khởi tạo màn hình LCD"""
    print("Đang khởi tạo màn hình ST7789...")
    
    try:
        # Cấu hình SPI
        serial = spi(
            port=0, 
            device=0,  # CE0
            gpio_DC=DC_PIN,
            gpio_RST=RST_PIN,
            bus_speed_hz=40000000  # 40MHz
        )
        
        # Khởi tạo device ST7789
        device = st7789(
            serial,
            width=WIDTH,
            height=HEIGHT,
            rotate=0,  # 0, 1, 2, 3 (0°, 90°, 180°, 270°)
            bgr=True   # Thử True/False nếu màu sai
        )
        
        print("✓ Khởi tạo thành công!")
        return device
    
    except Exception as e:
        print(f"✗ Lỗi: {e}")
        print("\nKiểm tra:")
        print("  1. SPI đã bật? (sudo raspi-config -> Interface -> SPI)")
        print("  2. Đã cài luma.lcd? (pip install luma.lcd)")
        print("  3. Dây nối đúng chưa?")
        return None


def display_hello(device):
    """Hiển thị chữ Hello"""
    # Tạo image nền đen
    img = Image.new("RGB", (WIDTH, HEIGHT), "black")
    draw = ImageDraw.Draw(img)
    
    # Load font
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
        small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
    except:
        font = ImageFont.load_default()
        small_font = font
    
    # Vẽ "Hello" ở giữa
    text = "Hello"
    bbox = draw.textbbox((0, 0), text, font=font)
    x = (WIDTH - (bbox[2] - bbox[0])) // 2
    y = (HEIGHT - (bbox[3] - bbox[1])) // 2 - 20
    draw.text((x, y), text, font=font, fill="white")
    
    # Vẽ dòng phụ
    sub = "Luma LCD"
    bbox2 = draw.textbbox((0, 0), sub, font=small_font)
    x2 = (WIDTH - (bbox2[2] - bbox2[0])) // 2
    draw.text((x2, y + 60), sub, font=small_font, fill="lime")
    
    # Hiển thị
    device.display(img)
    print("✓ Đã hiển thị 'Hello'!")


def display_image(device, image_path):
    """Hiển thị hình ảnh từ file"""
    print(f"Đang hiển thị: {image_path}")
    
    try:
        img = Image.open(image_path)
        img = img.resize((WIDTH, HEIGHT))
        img = img.convert("RGB")
        device.display(img)
        print("✓ Đã hiển thị hình ảnh!")
    except Exception as e:
        print(f"✗ Lỗi: {e}")


def display_colors_test(device):
    """Test các màu cơ bản"""
    colors = [
        ("Đỏ", "red"),
        ("Xanh lá", "green"),
        ("Xanh dương", "blue"),
        ("Trắng", "white"),
        ("Vàng", "yellow"),
    ]
    
    for name, color in colors:
        print(f"  Màu: {name}")
        img = Image.new("RGB", (WIDTH, HEIGHT), color)
        device.display(img)
        time.sleep(0.5)


def main():
    print("=" * 50)
    print(" ST7789 LCD - LUMA LIBRARY")
    print("=" * 50)
    
    # Bật backlight (nếu cần)
    try:
        import RPi.GPIO as GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(BL_PIN, GPIO.OUT)
        GPIO.output(BL_PIN, GPIO.HIGH)
        print("✓ Backlight ON")
    except:
        print("⚠ Không thể điều khiển backlight")
    
    # Khởi tạo
    device = init_display()
    if device is None:
        return
    
    # Test màu
    print("\n--- Test màu ---")
    display_colors_test(device)
    
    # Hiển thị Hello
    print("\n--- Hiển thị Hello ---")
    display_hello(device)
    
    # Để hiển thị hình ảnh, bỏ comment dòng dưới:
    # display_image(device, "/path/to/your/image.jpg")
    
    print("\n✓ Hoàn tất! Nhấn Ctrl+C để thoát.")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nThoát.")


if __name__ == "__main__":
    main()
