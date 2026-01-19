#!/usr/bin/env python3
"""
Hiển thị hình ảnh trên màn hình ST7789 LCD bằng thư viện Luma
Raspberry Pi Zero 2 W + ST7789 1.54" SPI LCD (240x240)

Cài đặt:
    pip install luma.lcd pillow RPi.GPIO spidev

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
import RPi.GPIO as GPIO

# ============ CẤU HÌNH PIN ============
DC_PIN = 24      # GPIO24 (Pin 18) - Data/Command
RST_PIN = 25     # GPIO25 (Pin 22) - Reset
BL_PIN = 18      # GPIO18 (Pin 12) - Backlight

# ============ CẤU HÌNH MÀN HÌNH ============
WIDTH = 240
HEIGHT = 240
# Thử các giá trị khác nếu hình bị lệch
H_OFFSET = 0     # Offset ngang (thử 0, 40, 80)
V_OFFSET = 0     # Offset dọc (thử 0, 40, 80)


def setup_backlight():
    """Bật backlight"""
    try:
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(BL_PIN, GPIO.OUT)
        GPIO.output(BL_PIN, GPIO.HIGH)
        print("✓ Backlight: ON")
        return True
    except Exception as e:
        print(f"⚠ Backlight lỗi: {e}")
        return False


def init_display():
    """Khởi tạo màn hình LCD"""
    print("\nĐang khởi tạo màn hình ST7789...")
    
    try:
        # Cấu hình SPI - giảm tốc độ nếu không ổn định
        serial = spi(
            port=0, 
            device=0,         # CE0 (GPIO8)
            gpio_DC=DC_PIN,   # Data/Command pin
            gpio_RST=RST_PIN, # Reset pin
            bus_speed_hz=16000000  # 16MHz (ổn định hơn 40MHz)
        )
        
        # Khởi tạo device ST7789
        # Lưu ý: luma.lcd không có tham số invert, 
        # màn hình 1.54" thường tự xử lý
        device = st7789(
            serial,
            width=WIDTH,
            height=HEIGHT,
            h_offset=H_OFFSET,
            v_offset=V_OFFSET,
            rotate=0,    # 0, 1, 2, 3 = 0°, 90°, 180°, 270°
            bgr=True     # True cho hầu hết màn ST7789
        )
        
        print("✓ Khởi tạo ST7789 thành công!")
        print(f"  - Kích thước: {WIDTH}x{HEIGHT}")
        print(f"  - Offset: H={H_OFFSET}, V={V_OFFSET}")
        return device
    
    except Exception as e:
        print(f"✗ Lỗi khởi tạo: {e}")
        print("\n=== KIỂM TRA ===")
        print("1. SPI đã bật? Chạy: sudo raspi-config -> Interface -> SPI -> Enable")
        print("2. Đã cài thư viện? pip install luma.lcd pillow spidev RPi.GPIO")
        print("3. Dây nối đúng chưa? Kiểm tra lại theo sơ đồ")
        print("4. Kiểm tra SPI: ls /dev/spi*")
        return None


def display_solid_color(device, color, name=""):
    """Hiển thị màu đơn sắc"""
    img = Image.new("RGB", (WIDTH, HEIGHT), color)
    device.display(img)
    if name:
        print(f"  ✓ Đã hiển thị: {name}")


def display_hello(device):
    """Hiển thị chữ Hello"""
    img = Image.new("RGB", (WIDTH, HEIGHT), "black")
    draw = ImageDraw.Draw(img)
    
    # Load font
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
        small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
    except:
        font = ImageFont.load_default()
        small_font = font
        print("  (Dùng font mặc định)")
    
    # Vẽ "Hello" ở giữa
    text = "Hello"
    bbox = draw.textbbox((0, 0), text, font=font)
    x = (WIDTH - (bbox[2] - bbox[0])) // 2
    y = (HEIGHT - (bbox[3] - bbox[1])) // 2 - 20
    draw.text((x, y), text, font=font, fill="white")
    
    # Vẽ dòng phụ
    sub = "Raspberry Pi"
    bbox2 = draw.textbbox((0, 0), sub, font=small_font)
    x2 = (WIDTH - (bbox2[2] - bbox2[0])) // 2
    draw.text((x2, y + 60), sub, font=small_font, fill="lime")
    
    device.display(img)
    print("✓ Đã hiển thị 'Hello'!")


def display_test_pattern(device):
    """Hiển thị test pattern để debug"""
    img = Image.new("RGB", (WIDTH, HEIGHT), "black")
    draw = ImageDraw.Draw(img)
    
    # Vẽ 4 góc màu khác nhau
    draw.rectangle([0, 0, 60, 60], fill="red")           # Góc trái trên
    draw.rectangle([180, 0, 240, 60], fill="green")      # Góc phải trên
    draw.rectangle([0, 180, 60, 240], fill="blue")       # Góc trái dưới
    draw.rectangle([180, 180, 240, 240], fill="yellow")  # Góc phải dưới
    
    # Vẽ chữ thập ở giữa
    draw.line([(120, 0), (120, 240)], fill="white", width=2)
    draw.line([(0, 120), (240, 120)], fill="white", width=2)
    
    # Vẽ viền
    draw.rectangle([0, 0, 239, 239], outline="white", width=2)
    
    device.display(img)
    print("✓ Đã hiển thị test pattern!")
    print("  - Đỏ: góc trái trên")
    print("  - Xanh lá: góc phải trên")
    print("  - Xanh dương: góc trái dưới")
    print("  - Vàng: góc phải dưới")


def display_colors_test(device):
    """Test các màu cơ bản"""
    colors = [
        ("white", "Trắng"),
        ("red", "Đỏ"),
        ("green", "Xanh lá"),
        ("blue", "Xanh dương"),
        ("yellow", "Vàng"),
        ("black", "Đen"),
    ]
    
    for color, name in colors:
        display_solid_color(device, color, name)
        time.sleep(0.5)


def main():
    print("=" * 50)
    print(" ST7789 1.54\" LCD - LUMA LIBRARY TEST")
    print("=" * 50)
    
    # Bước 1: Bật backlight
    print("\n[1] Bật backlight...")
    setup_backlight()
    
    # Bước 2: Khởi tạo display
    print("\n[2] Khởi tạo màn hình...")
    device = init_display()
    if device is None:
        return
    
    # Bước 3: Hiển thị màu trắng đầu tiên (dễ nhận biết nhất)
    print("\n[3] Hiển thị màu trắng full màn hình...")
    display_solid_color(device, "white", "TRẮNG - Nếu thấy màn hình sáng trắng là OK!")
    time.sleep(2)
    
    # Bước 4: Test pattern
    print("\n[4] Hiển thị test pattern...")
    display_test_pattern(device)
    time.sleep(2)
    
    # Bước 5: Test màu
    print("\n[5] Test các màu...")
    display_colors_test(device)
    
    # Bước 6: Hiển thị Hello
    print("\n[6] Hiển thị Hello...")
    display_hello(device)
    
    print("\n" + "=" * 50)
    print("✓ HOÀN TẤT! Nếu không thấy gì, kiểm tra:")
    print("  1. Dây BL (backlight) nối đúng?")
    print("  2. Dây VCC có điện 3.3V?")
    print("  3. Thử đổi H_OFFSET, V_OFFSET trong code")
    print("=" * 50)
    print("\nNhấn Ctrl+C để thoát.")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        GPIO.cleanup()
        print("\nĐã thoát và cleanup GPIO.")


if __name__ == "__main__":
    main()
