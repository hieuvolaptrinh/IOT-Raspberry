import cv2
import ST7789
from PIL import Image

# 1. Khởi tạo màn hình (Kiểm tra lại số chân DC, RST bạn đã nối)
disp = ST7789.ST7789(
    port=0,
    cs=0,  # Pin 24
    dc=5,  # Pin 18 (WiringPi 5)
    rst=6, # Pin 22 (WiringPi 6)
    backlight=1, # Pin 12
    spi_speed_hz=80 * 1000 * 1000
)
disp.begin()

# 2. Mở file video
video_path = "video_cua_ban.mp4"
cap = cv2.VideoCapture(video_path)

while cap.isOpened():
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

cap.release()