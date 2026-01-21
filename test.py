#!/usr/bin/env python3
import st7789
from PIL import Image
# THỬ ĐỔI DC/RST NẾU CHƯA ĐÚNG
disp = st7789.ST7789(
    port=0,
    cs=0,                    # CE0
    dc=25,                   # THỬ: 24 hoặc 25
    rst=24,                  # THỬ: 25 hoặc 24  
    backlight=18,
    width=240,
    height=240,
    rotation=0,
    invert=True,             # Quan trọng cho 1.54"
    spi_speed_hz=40000000
)
# Fill màu đỏ
img = Image.new("RGB", (240, 240), "red")
disp.display(img)
print("Done! Màn hình phải hiện màu đỏ")