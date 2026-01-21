#!/usr/bin/env python3
from luma.core.interface.serial import spi
from luma.lcd.device import st7789
from PIL import Image

# Cấu hình SPI
serial = spi(port=0, device=0, gpio_DC=25, gpio_RST=24, bus_speed_hz=40000000)

# Khởi tạo display (thử đổi bgr=True nếu màu bị sai)
device = st7789(serial, width=240, height=240, rotate=0, bgr=True)

# Test màu đỏ
img = Image.new("RGB", (240, 240), "red")
device.display(img)
print("Done!")