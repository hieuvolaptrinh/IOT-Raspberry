#!/usr/bin/env python3
"""
TEST VIDEO - ST7789 LCD với SPI Mode 3
Raspberry Pi Zero 2 W + ST7789 1.54" 240x240 LCD

Cài đặt:
    pip install opencv-python pillow numpy spidev RPi.GPIO
"""
import cv2
from display_image import ST7789Display
from PIL import Image

print("=" * 50)
print(" PLAY VIDEO - ST7789 LCD | SPI Mode 3")
print("=" * 50)

display = ST7789Display()
cap = cv2.VideoCapture("video.mp4")

if not cap.isOpened():
    print("❌ Không mở được file video.mp4!")
    print("   Đảm bảo file video.mp4 nằm cùng thư mục.")
    display.cleanup()
    exit(1)

print("\n▶ Đang phát video... (Ctrl+C để dừng)")

try:
    while True:
        ret, frame = cap.read()
        if not ret:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # Loop lại
            continue
        
        # BGR → RGB → PIL → Display
        img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        display.display(img.resize((240, 240)))

except KeyboardInterrupt:
    print("\n\n⏹ Đã dừng video.")

finally:
    cap.release()
    display.cleanup()
    print("✓ Cleanup xong!")