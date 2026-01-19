import digitalio
import board
from PIL import Image, ImageDraw
from adafruit_rgb_display import st7789
import time
# GPIO Configuration
cs_pin = digitalio.DigitalInOut(board.CE0)
dc_pin = digitalio.DigitalInOut(board.D25)
reset_pin = digitalio.DigitalInOut(board.D27)
backlight_pin = digitalio.DigitalInOut(board.D18)
# Bật backlight
backlight_pin.switch_to_output()
backlight_pin.value = True
print("=" * 50)
print("  Adafruit ST7789 Test")
print("=" * 50)
# Khởi tạo SPI
spi = board.SPI()
# Khởi tạo display - thử nhiều config
disp = st7789.ST7789(
    spi,
    cs=cs_pin,
    dc=dc_pin,
    rst=reset_pin,
    baudrate=40000000,
    width=240,
    height=240,
    x_offset=0,
    y_offset=0,
    rotation=0
)
print("✓ Khởi tạo thành công!")
# Tạo ảnh test
width = disp.width
height = disp.height
image = Image.new("RGB", (width, height))
draw = ImageDraw.Draw(image)
# Fill màu đỏ
draw.rectangle((0, 0, width, height), fill=(255, 0, 0))
# Vẽ các hình
draw.rectangle([10, 10, 80, 80], fill=(0, 255, 0))      # Xanh lá
draw.rectangle([90, 10, 160, 80], fill=(0, 0, 255))     # Xanh dương
draw.rectangle([170, 10, 230, 80], fill=(255, 255, 0))  # Vàng
draw.ellipse([80, 100, 160, 180], fill=(255, 255, 255)) # Tròn trắng
draw.text((60, 200), "ADAFRUIT TEST", fill=(255, 255, 255))
print("Đang hiển thị...")
disp.image(image)
print("✓ Hoàn thành! Kiểm tra màn hình.")
print("Nhấn Ctrl+C để thoát...")
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\nĐã dừng.")