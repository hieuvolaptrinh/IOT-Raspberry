import cv2
from display_image import ST7789Display
from PIL import Image

display = ST7789Display()
cap = cv2.VideoCapture("video.mp4")

while True:
    ret, frame = cap.read()
    if not ret:
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # Loop lại
        continue
    
    # BGR → RGB → PIL → Display
    img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    display.display(img.resize((240, 240)))

cap.release()