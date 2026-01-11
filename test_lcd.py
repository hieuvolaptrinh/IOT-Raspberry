import st7789
from PIL import Image, ImageDraw
import time

# Thử giảm SPI speed nếu màn hình chớp
# 80MHz -> 40MHz -> 20MHz
SPI_SPEED = 40 * 1000 * 1000  # Thử 40MHz trước

print("Đang khởi tạo màn hình...")
disp = st7789.ST7789(
    port=0,
    cs=0,           # Pin 24 -> CE0 (SPI)
    dc=24,          # Pin 18 -> GPIO 24 (BCM)
    rst=25,         # Pin 22 -> GPIO 25 (BCM)
    backlight=18,   # Pin 12 -> GPIO 18 (BCM)
    spi_speed_hz=SPI_SPEED
)
disp.begin()
print(f"Màn hình đã khởi tạo! SPI Speed: {SPI_SPEED/1000000}MHz")

# Test 1: Màn hình đỏ
print("Test 1: Hiển thị màu đỏ...")
img_red = Image.new('RGB', (240, 240), color='red')
disp.display(img_red)
time.sleep(2)

# Test 2: Màn hình xanh lá
print("Test 2: Hiển thị màu xanh lá...")
img_green = Image.new('RGB', (240, 240), color='green')
disp.display(img_green)
time.sleep(2)

# Test 3: Màn hình xanh dương
print("Test 3: Hiển thị màu xanh dương...")
img_blue = Image.new('RGB', (240, 240), color='blue')
disp.display(img_blue)
time.sleep(2)

# Test 4: Hiển thị text
print("Test 4: Hiển thị text...")
img = Image.new('RGB', (240, 240), color='black')
draw = ImageDraw.Draw(img)
draw.text((50, 100), "LCD OK!", fill='white')
disp.display(img)
time.sleep(2)

print("Test hoàn tất!")
