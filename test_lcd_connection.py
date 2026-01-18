#!/usr/bin/env python3
"""
TEST LCD ST7789 - Hiển thị text trên màn hình
Sử dụng thư viện st7789

Cài đặt thư viện cho Python 3.13:
    pip3 install st7789 --break-system-packages
    pip3 install pillow --break-system-packages
    pip3 install numpy --break-system-packages

Nối dây:
    VCC  → Pin 1 (3.3V)
    GND  → Pin 6
    SCL  → Pin 23 (GPIO 11)
    SDA  → Pin 19 (GPIO 10)
    CS   → Pin 24 (GPIO 8)
    DC   → Pin 18 (GPIO 24)
    RST  → Pin 22 (GPIO 25)
    BL   → Pin 12 (GPIO 18)

Chạy: python3 test_lcd_connection.py
"""

import time
import sys

print("=" * 55)
print(" TEST LCD ST7789 - HIỂN THỊ TEXT")
print("=" * 55)

# ========== KIỂM TRA THƯ VIỆN ==========
print("\n[1] KIỂM TRA THƯ VIỆN...")

libs_ok = True

try:
    import st7789
    print("  ✅ st7789: OK")
except ImportError:
    print("  ❌ st7789: THIẾU")
    print("     Cài: pip3 install st7789 --break-system-packages")
    libs_ok = False

try:
    from PIL import Image, ImageDraw, ImageFont
    print("  ✅ Pillow: OK")
except ImportError:
    print("  ❌ Pillow: THIẾU")
    print("     Cài: pip3 install pillow --break-system-packages")
    libs_ok = False

try:
    import RPi.GPIO as GPIO
    print("  ✅ RPi.GPIO: OK")
except ImportError:
    print("  ❌ RPi.GPIO: THIẾU")
    print("     Cài: pip3 install RPi.GPIO --break-system-packages")
    libs_ok = False

if not libs_ok:
    print("\n⚠️  Vui lòng cài đủ thư viện!")
    print("\n📦 Lệnh cài tất cả:")
    print("   pip3 install st7789 pillow RPi.GPIO numpy --break-system-packages")
    sys.exit(1)

# ========== CẤU HÌNH LCD ==========
print("\n[2] KHỞI TẠO LCD...")

# Cấu hình pin
LCD_WIDTH = 240
LCD_HEIGHT = 240
DC_PIN = 24      # GPIO 24 (Pin 18)
RST_PIN = 25     # GPIO 25 (Pin 22)
BL_PIN = 18      # GPIO 18 (Pin 12)
CS_PIN = 8       # GPIO 8 (Pin 24) - CE0

try:
    # Khởi tạo LCD
    disp = st7789.ST7789(
        height=LCD_HEIGHT,
        width=LCD_WIDTH,
        rotation=0,
        port=0,
        cs=0,               # CE0
        dc=DC_PIN,
        backlight=BL_PIN,
        rst=RST_PIN,
        spi_speed_hz=40000000
    )
    print("  ✅ LCD khởi tạo thành công!")
except Exception as e:
    print(f"  ❌ Lỗi khởi tạo LCD: {e}")
    sys.exit(1)

# ========== TẠO HÌNH ẢNH VÀ HIỂN THỊ TEXT ==========
print("\n[3] HIỂN THỊ TEXT LÊN LCD...")

def display_text(display, lines, bg_color=(0, 0, 0), text_color=(255, 255, 255)):
    """
    Hiển thị nhiều dòng text lên LCD
    
    Args:
        display: đối tượng ST7789
        lines: list các dòng text
        bg_color: màu nền (R, G, B)
        text_color: màu chữ (R, G, B)
    """
    # Tạo image
    img = Image.new('RGB', (LCD_WIDTH, LCD_HEIGHT), color=bg_color)
    draw = ImageDraw.Draw(img)
    
    # Thử load font, nếu không có dùng font mặc định
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
    except:
        font = ImageFont.load_default()
        font_small = font
    
    # Vẽ các dòng text
    y_position = 20
    line_height = 30
    
    for i, line in enumerate(lines):
        # Dòng đầu dùng font lớn
        current_font = font if i == 0 else font_small
        draw.text((10, y_position), str(line), font=current_font, fill=text_color)
        y_position += line_height
    
    # Hiển thị lên LCD
    display.display(img)

def display_color_test(display):
    """Test màu sắc cơ bản"""
    colors = [
        ((255, 0, 0), "ĐỎ"),
        ((0, 255, 0), "XANH LÁ"),
        ((0, 0, 255), "XANH DƯƠNG"),
        ((255, 255, 0), "VÀNG"),
        ((255, 0, 255), "HỒNG"),
        ((0, 255, 255), "CYAN"),
        ((255, 255, 255), "TRẮNG"),
    ]
    
    for color, name in colors:
        img = Image.new('RGB', (LCD_WIDTH, LCD_HEIGHT), color=color)
        draw = ImageDraw.Draw(img)
        
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
        except:
            font = ImageFont.load_default()
        
        # Text màu đen để dễ đọc
        text_color = (0, 0, 0) if color != (0, 0, 0) else (255, 255, 255)
        draw.text((LCD_WIDTH//2 - 50, LCD_HEIGHT//2 - 15), name, font=font, fill=text_color)
        
        display.display(img)
        time.sleep(0.5)

# ========== CHẠY TEST ==========
try:
    # Test 1: Hiển thị thông tin
    print("  📺 Hiển thị thông tin hệ thống...")
    display_text(disp, [
        "LCD ST7789",
        "240x240 pixels",
        "Raspberry Pi Zero 2",
        "Python 3.13",
        "",
        "Test OK!"
    ], bg_color=(0, 0, 50), text_color=(255, 255, 255))
    time.sleep(2)
    
    # Test 2: Test màu
    print("  🎨 Test các màu cơ bản...")
    display_color_test(disp)
    
    # Test 3: Hiển thị kết quả cuối
    print("  ✅ Hiển thị kết quả...")
    display_text(disp, [
        "✓ TEST THÀNH CÔNG!",
        "",
        "LCD hoạt động tốt",
        "SPI: OK",
        "Backlight: OK",
        "",
        "Chúc mừng bạn!"
    ], bg_color=(0, 80, 0), text_color=(255, 255, 255))
    
    print("\n" + "=" * 55)
    print(" 🎉 TEST HOÀN TẤT - LCD HOẠT ĐỘNG TỐT!")
    print("=" * 55)
    
except KeyboardInterrupt:
    print("\n⚠️  Đã dừng test.")
except Exception as e:
    print(f"\n❌ Lỗi: {e}")
    import traceback
    traceback.print_exc()
finally:
    # Cleanup
    try:
        GPIO.cleanup()
    except:
        pass
