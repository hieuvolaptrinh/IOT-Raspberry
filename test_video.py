import st7789
from PIL import Image
import time

PORT = 0
CS = 0          # CE0 (pin 24)
DC = 24         # GPIO24 (pin 18)
RST = 25        # GPIO25 (pin 22)
BL = 18         # GPIO18 (pin 12)

def show(disp, color, t=0.8):
    img = Image.new("RGB", (240, 240), color=color)
    disp.display(img)
    time.sleep(t)

tests = [
    # (rotation, invert, offset_left, offset_top)
    (0,  True,  0,  0),
    (90, True,  0,  0),
    (180,True,  0,  0),
    (270,True,  0,  0),
    (0,  False, 0,  0),
    (90, False, 0,  0),
    (180,False, 0,  0),
    (270,False, 0,  0),

    # hay gặp với panel 240x240 dùng RAM 240x320
    (0,  True,  0, 80),
    (90, True,  0, 80),
    (0,  True, 80, 0),
    (90, True, 80, 0),
]

for rot, inv, offl, offt in tests:
    print("Test:", "rot", rot, "invert", inv, "offL", offl, "offT", offt)
    disp = st7789.ST7789(
        port=PORT,
        cs=CS,
        dc=DC,
        rst=RST,
        backlight=BL,
        width=240,
        height=240,
        rotation=rot,
        invert=inv,
        spi_speed_hz=4_000_000,   # TEST 4MHz trước cho chắc
        offset_left=offl,
        offset_top=offt
    )
    disp.begin()

    show(disp, "red")
    show(disp, "green")
    show(disp, "blue")
    show(disp, "black", 0.3)

print("Done.")
