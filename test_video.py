import cv2
import st7789
from PIL import Image
import time

# 1. Khởi tạo màn hình - GPIO BCM đúng theo sơ đồ Raspberry Pi Zero
disp = st7789.ST7789(
    port=0,
    cs=0,           # Pin 24 -> CE0 (SPI)
    dc=24,          # Pin 18 -> GPIO 24 (BCM)
    rst=25,         # Pin 22 -> GPIO 25 (BCM)
    backlight=18,   # Pin 12 -> GPIO 18 (BCM) - hoặc None nếu nối trực tiếp 3.3V
    spi_speed_hz=80 * 1000 * 1000
)
disp.begin()

# 2. Mở file video
video_path = "zero.mp4"
cap = cv2.VideoCapture(video_path)

# Lấy FPS của video để điều chỉnh tốc độ phát
fps = cap.get(cv2.CAP_PROP_FPS)
delay = 1.0 / fps if fps > 0 else 1.0 / 30

while cap.isOpened():
    start_time = time.time()
    
    ret, frame = cap.read()
    if not ret:
        break

    # Chuyển đổi màu từ BGR (OpenCV) sang RGB
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    # Resize khung hình video về đúng kích thước màn hình
    img = Image.fromarray(frame)
    img = img.resize((240, 240))

    # Hiển thị lên LCD
    disp.display(img)
    
    # Điều chỉnh FPS - chờ để video chạy đúng tốc độ
    elapsed = time.time() - start_time
    sleep_time = delay - elapsed
    if sleep_time > 0:
        time.sleep(sleep_time)

cap.release()