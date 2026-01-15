#!/usr/bin/env python3
"""
Debug LCD nâng cao - Thử nhiều cấu hình khác nhau
Chạy: python3 debug_lcd_advanced.py
"""

import st7789
from PIL import Image, ImageDraw, ImageFont
import time

def create_test_image(text, color=(255, 255, 255), bg=(255, 0, 0)):
    """Tạo ảnh test với text"""
    img = Image.new('RGB', (240, 240), bg)
    draw = ImageDraw.Draw(img)
    # Vẽ text ở giữa
    draw.text((60, 100), text, fill=color)
    # Vẽ border để dễ nhận biết
    draw.rectangle([5, 5, 235, 235], outline=(255, 255, 0), width=3)
    return img

configs = [
    # Config 1: Cấu hình gốc từ test_video.py
    {
        "name": "Config gốc (DC=24, RST=25)",
        "dc": 24, "rst": 25, "cs": 0, "backlight": 18,
        "spi_speed": 40_000_000
    },
    # Config 2: Đảo DC và RST
    {
        "name": "Đảo DC/RST (DC=25, RST=24)",
        "dc": 25, "rst": 24, "cs": 0, "backlight": 18,
        "spi_speed": 40_000_000
    },
    # Config 3: Tốc độ SPI thấp hơn
    {
        "name": "SPI chậm 10MHz (DC=24, RST=25)",
        "dc": 24, "rst": 25, "cs": 0, "backlight": 18,
        "spi_speed": 10_000_000
    },
    # Config 4: Tốc độ SPI rất thấp
    {
        "name": "SPI rất chậm 4MHz",
        "dc": 24, "rst": 25, "cs": 0, "backlight": 18,
        "spi_speed": 4_000_000
    },
    # Config 5: Dùng CE1 thay vì CE0
    {
        "name": "Dùng CE1 (cs=1)",
        "dc": 24, "rst": 25, "cs": 1, "backlight": 18,
        "spi_speed": 40_000_000
    },
    # Config 6: Không dùng backlight GPIO
    {
        "name": "Không control backlight",
        "dc": 24, "rst": 25, "cs": 0, "backlight": None,
        "spi_speed": 40_000_000
    },
]

print("="*60)
print(" DEBUG LCD - Thử nhiều cấu hình")
print(" Nhấn Enter để chuyển sang config tiếp theo")
print(" Nhập 'q' để thoát")
print("="*60)

for i, cfg in enumerate(configs):
    print(f"\n[{i+1}/{len(configs)}] Đang thử: {cfg['name']}")
    print(f"    DC={cfg['dc']}, RST={cfg['rst']}, CS={cfg['cs']}")
    print(f"    SPI Speed={cfg['spi_speed']/1_000_000}MHz, Backlight={cfg['backlight']}")
    
    try:
        disp = st7789.ST7789(
            port=0,
            cs=cfg['cs'],
            dc=cfg['dc'],
            rst=cfg['rst'],
            backlight=cfg['backlight'],
            spi_speed_hz=cfg['spi_speed']
        )
        disp.begin()
        
        # Hiển thị màu đỏ với text
        img = create_test_image(f"TEST {i+1}", (255, 255, 255), (255, 0, 0))
        disp.display(img)
        time.sleep(0.5)
        
        # Hiển thị màu xanh
        img = create_test_image(f"TEST {i+1}", (0, 0, 0), (0, 255, 0))
        disp.display(img)
        
        print("    ✅ Không có lỗi khi gửi dữ liệu")
        
    except Exception as e:
        print(f"    ❌ Lỗi: {e}")
        continue
    
    answer = input("    ❓ LCD có hiển thị không? (y/n/q): ").strip().lower()
    if answer == 'y':
        print("\n" + "="*60)
        print(f" 🎉 TÌM THẤY CẤU HÌNH ĐÚNG!")
        print(f" Config: {cfg['name']}")
        print(f" DC={cfg['dc']}, RST={cfg['rst']}, CS={cfg['cs']}")
        print(f" SPI Speed={cfg['spi_speed']/1_000_000}MHz")
        print("="*60)
        
        # Cập nhật test_video.py với config đúng
        print("\n📝 Cập nhật file test_video.py với config này:")
        print(f"""
disp = st7789.ST7789(
    port=0,
    cs={cfg['cs']},
    dc={cfg['dc']},
    rst={cfg['rst']},
    backlight={cfg['backlight']},
    spi_speed_hz={cfg['spi_speed']}
)
""")
        break
    elif answer == 'q':
        print("Thoát...")
        break

else:
    print("\n" + "="*60)
    print(" ❌ KHÔNG TÌM THẤY CẤU HÌNH NÀO HOẠT ĐỘNG!")
    print("="*60)
    print("""
💡 Các bước tiếp theo:
1. Kiểm tra lại dây nối vật lý một lần nữa
2. Đảm bảo VCC nối vào 3.3V (KHÔNG nối 5V!)
3. Kiểm tra xem module LCD có bị hỏng không
4. Thử đảo dây SDA và SCL (GPIO 10 và 11)
5. Chạy lệnh: dmesg | grep -i spi để xem log

📌 Nếu dùng module LCD khác (không phải ST7789):
   - ILI9341: pip3 install luma.lcd
   - SSD1351: dùng driver khác
""")
