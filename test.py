#!/usr/bin/env python3
"""
Display image on ST7789 1.54" TFT LCD
Raspberry Pi Zero 2 WH

Wiring (SPI):
- VCC  -> 3.3V (Pin 1)
- GND  -> GND (Pin 6)
- SCL  -> GPIO 11 / SCLK (Pin 23)
- SDA  -> GPIO 10 / MOSI (Pin 19)
- RES  -> GPIO 27 (Pin 13)
- DC   -> GPIO 25 (Pin 22)
- CS   -> GPIO 8 / CE0 (Pin 24)
- BLK  -> GPIO 18 (Pin 12) hoặc 3.3V
"""

import st7789
from PIL import Image
import time
import os

# ============== CẤU HÌNH GPIO ==============
DC_PIN = 25        # Data/Command
RST_PIN = 27       # Reset (nếu có)
BL_PIN = 18        # Backlight
CS_PIN = 0         # CE0 (Chip Select)
SPI_PORT = 0       # SPI0

# ============== CẤU HÌNH DISPLAY ==============
DISPLAY_WIDTH = 240
DISPLAY_HEIGHT = 240
SPI_SPEED = 40_000_000  # 40MHz - ổn định, có thể tăng lên 80MHz

# ============== ĐƯỜNG DẪN ẢNH ==============
# Lấy đường dẫn thư mục hiện tại của script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGE_PATH = os.path.join(SCRIPT_DIR, "image.png")


def init_display():
    """Khởi tạo màn hình ST7789"""
    print("Đang khởi tạo màn hình ST7789...")
    
    disp = st7789.ST7789(
        height=DISPLAY_HEIGHT,
        width=DISPLAY_WIDTH,
        rotation=0,              # 0, 90, 180, 270
        port=SPI_PORT,
        cs=CS_PIN,
        dc=DC_PIN,
        backlight=BL_PIN,
        spi_speed_hz=SPI_SPEED,
        offset_left=0,
        offset_top=0
    )
    
    print("✓ Khởi tạo thành công!")
    return disp


def load_and_resize_image(image_path, target_width, target_height):
    """Load và resize ảnh để vừa với màn hình"""
    print(f"Đang tải ảnh: {image_path}")
    
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Không tìm thấy file: {image_path}")
    
    # Mở ảnh
    img = Image.open(image_path)
    print(f"  Kích thước gốc: {img.size}")
    print(f"  Mode: {img.mode}")
    
    # Chuyển sang RGB nếu cần (loại bỏ alpha channel)
    if img.mode != 'RGB':
        img = img.convert('RGB')
        print("  Đã chuyển sang RGB")
    
    # Resize ảnh để vừa màn hình (giữ tỷ lệ)
    img_ratio = img.width / img.height
    screen_ratio = target_width / target_height
    
    if img_ratio > screen_ratio:
        # Ảnh rộng hơn màn hình
        new_width = target_width
        new_height = int(target_width / img_ratio)
    else:
        # Ảnh cao hơn màn hình
        new_height = target_height
        new_width = int(target_height * img_ratio)
    
    img = img.resize((new_width, new_height), Image.LANCZOS)
    print(f"  Resize thành: {img.size}")
    
    # Tạo background đen và paste ảnh vào giữa
    background = Image.new('RGB', (target_width, target_height), (0, 0, 0))
    offset_x = (target_width - new_width) // 2
    offset_y = (target_height - new_height) // 2
    background.paste(img, (offset_x, offset_y))
    
    print("✓ Tải ảnh thành công!")
    return background


def display_image(disp, image):
    """Hiển thị ảnh lên màn hình"""
    print("Đang hiển thị ảnh...")
    disp.display(image)
    print("✓ Hiển thị thành công!")


def main():
    print("=" * 50)
    print("  ST7789 Image Display Test")
    print("=" * 50)
    print()
    
    try:
        # 1. Khởi tạo display
        disp = init_display()
        
        # 2. Load và resize ảnh
        img = load_and_resize_image(IMAGE_PATH, DISPLAY_WIDTH, DISPLAY_HEIGHT)
        
        # 3. Hiển thị ảnh
        display_image(disp, img)
        
        print()
        print("=" * 50)
        print("  ✓ HOÀN THÀNH! Ảnh đang hiển thị trên LCD")
        print("=" * 50)
        print()
        print("Nhấn Ctrl+C để thoát...")
        
        # Giữ chương trình chạy
        while True:
            time.sleep(1)
            
    except FileNotFoundError as e:
        print(f"❌ Lỗi: {e}")
    except ImportError as e:
        print(f"❌ Lỗi thư viện: {e}")
        print("Vui lòng cài đặt: pip install st7789 pillow")
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        import traceback
        traceback.print_exc()
    except KeyboardInterrupt:
        print("\nĐã dừng chương trình.")


if __name__ == "__main__":
    main()
