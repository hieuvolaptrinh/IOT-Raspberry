

import cv2
import numpy as np
import spidev
import RPi.GPIO as GPIO
import time
import os
import subprocess
import requests
import threading
from datetime import datetime
from dotenv import load_dotenv

# ============ LOAD .ENV ============
load_dotenv()
API_URL = os.getenv("API_URL", "http://172.20.10.3:8000")
API_ENDPOINT = "/api/vsl/convert-audio-simple"

# ============ GPIO PINS ============
BUTTON_PIN = 17  # Pin 11
DC_PIN = 24
RST_PIN = 25
BL_PIN = 18

# ============ AUDIO SETTINGS ============
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
AUDIO_DEVICE = "plughw:CARD=Device,DEV=0"  # USB PnP Sound Device
SAMPLE_RATE = 44100
CHANNELS = 1

# ============ SPI SETTINGS ============
SPI_MODE = 3
SPI_SPEED = 32000000

# ============ TRẠNG THÁI ============
class State:
    IDLE = 0           # Chờ nhấn nút
    RECORDING = 1      # Đang ghi âm
    PROCESSING = 2     # Đang gửi API
    PLAYING = 3        # Đang phát video

current_state = State.IDLE
record_process = None
current_audio_file = None
video_thread = None
stop_video_flag = False
last_button_time = 0

# ============ GPIO + SPI SETUP ============
try:
    GPIO.cleanup()
except:
    pass

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(DC_PIN, GPIO.OUT)
GPIO.setup(RST_PIN, GPIO.OUT)
GPIO.setup(BL_PIN, GPIO.OUT)
GPIO.output(BL_PIN, GPIO.HIGH)

spi = spidev.SpiDev()
spi.open(0, 0)
spi.max_speed_hz = SPI_SPEED
spi.mode = SPI_MODE

# ============ LCD FUNCTIONS ============
def cmd(c):
    GPIO.output(DC_PIN, GPIO.LOW)
    spi.xfer2([c])

def data(d):
    GPIO.output(DC_PIN, GPIO.HIGH)
    if isinstance(d, list):
        spi.xfer2(d)
    else:
        spi.xfer2([d])

def data_bulk(d):
    GPIO.output(DC_PIN, GPIO.HIGH)
    for i in range(0, len(d), 4096):
        spi.xfer2(d[i:i+4096])

def init_lcd():
    GPIO.output(RST_PIN, GPIO.HIGH)
    time.sleep(0.05)
    GPIO.output(RST_PIN, GPIO.LOW)
    time.sleep(0.05)
    GPIO.output(RST_PIN, GPIO.HIGH)
    time.sleep(0.15)
    
    cmd(0x01); time.sleep(0.15)
    cmd(0x11); time.sleep(0.12)
    cmd(0x36); data(0x08)
    cmd(0x3A); data(0x55)
    cmd(0xB2); data([0x0C, 0x0C, 0x00, 0x33, 0x33])
    cmd(0xB7); data(0x35)
    cmd(0xBB); data(0x28)
    cmd(0xC0); data(0x0C)
    cmd(0xC2); data([0x01, 0xFF])
    cmd(0xC3); data(0x10)
    cmd(0xC4); data(0x20)
    cmd(0xC6); data(0x0F)
    cmd(0xD0); data([0xA4, 0xA1])
    cmd(0x21)
    cmd(0x13); time.sleep(0.01)
    cmd(0x29); time.sleep(0.12)

def show_frame(frame):
    frame = cv2.resize(frame, (240, 240), interpolation=cv2.INTER_NEAREST)
    b = frame[:, :, 0].astype(np.uint16)
    g = frame[:, :, 1].astype(np.uint16)
    r = frame[:, :, 2].astype(np.uint16)
    rgb565 = ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)
    buffer = np.empty((240, 240, 2), dtype=np.uint8)
    buffer[:, :, 0] = (rgb565 >> 8) & 0xFF
    buffer[:, :, 1] = rgb565 & 0xFF
    cmd(0x2A); data([0, 0, 0, 239])
    cmd(0x2B); data([0, 0, 0, 239])
    cmd(0x2C)
    data_bulk(buffer.flatten().tolist())

def show_message(lines, color=(255, 255, 255), bg_color=(0, 0, 0)):
    """Hiển thị text lên LCD"""
    frame = np.full((240, 240, 3), bg_color, dtype=np.uint8)
    font = cv2.FONT_HERSHEY_SIMPLEX
    
    if isinstance(lines, str):
        lines = lines.split('\n')
    
    total_height = len(lines) * 35
    start_y = (240 - total_height) // 2 + 25
    
    for i, line in enumerate(lines):
        text_size = cv2.getTextSize(line, font, 0.6, 2)[0]
        x = (240 - text_size[0]) // 2
        y = start_y + i * 35
        cv2.putText(frame, line, (x, y), font, 0.6, color, 2)
    
    show_frame(frame)

# ============ RECORDING FUNCTIONS ============
def start_recording():
    global record_process, current_audio_file, current_state
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    current_audio_file = f"{SCRIPT_DIR}/recording_{timestamp}.wav"
    
    print(f"🔴 BẮT ĐẦU GHI ÂM: {current_audio_file}")
    show_message(["RECORDING...", "", "Press button", "to stop"], (255, 100, 100), (50, 0, 0))
    
    record_process = subprocess.Popen([
        'arecord', '-D', AUDIO_DEVICE,
        '-f', 'S16_LE', '-r', str(SAMPLE_RATE),
        '-c', str(CHANNELS), '-t', 'wav',
        current_audio_file
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    current_state = State.RECORDING

def stop_recording():
    global record_process, current_state
    
    if record_process:
        record_process.terminate()
        record_process.wait()
        record_process = None
    
    # Chờ file được flush hoàn toàn
    time.sleep(0.5)
    
    print("⏹️ DỪNG GHI ÂM")
    
    # Kiểm tra file
    if current_audio_file and os.path.exists(current_audio_file):
        size = os.path.getsize(current_audio_file)
        print(f"✅ Đã lưu: {current_audio_file}")
        print(f"📊 Kích thước: {size / 1024:.1f} KB")
    else:
        print("❌ Lỗi: Không lưu được file!")
    
    current_state = State.PROCESSING

# ============ API FUNCTIONS ============
def send_to_api(audio_path):
    """Gửi audio đến API và trả về video_url"""
    url = f"{API_URL}{API_ENDPOINT}"
    print(f"📤 Gửi đến: {url}")
    show_message(["Sending...", "", "Please wait"], (255, 255, 100), (50, 50, 0))
    
    try:
        with open(audio_path, 'rb') as f:
            files = {'file': (os.path.basename(audio_path), f, 'audio/wav')}
            response = requests.post(url, files=files, timeout=120)
        
        if response.status_code == 200:
            data = response.json()
            video_url = data.get('data', {}).get('video_url', '')
            transcript = data.get('data', {}).get('transcript', '')
            
            print(f"✅ SUCCESS!")
            print(f"📹 Video: {video_url}")
            print(f"📝 Text: {transcript}")
            
            return video_url, transcript
        else:
            print(f"❌ API Error: {response.status_code}")
            return None, None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None, None

# ============ VIDEO PLAYBACK ============
def play_video(video_url):
    """Phát video từ URL (chạy trong thread riêng)"""
    global current_state, stop_video_flag
    
    print(f"🎬 Đang phát video...")
    show_message(["Loading video...", "", "Please wait"], (100, 255, 100), (0, 50, 0))
    
    cap = cv2.VideoCapture(video_url)
    if not cap.isOpened():
        print("❌ Không mở được video!")
        show_message(["Error!", "Cannot open video"], (255, 100, 100), (50, 0, 0))
        current_state = State.IDLE
        return
    
    current_state = State.PLAYING
    
    try:
        while not stop_video_flag:
            ret, frame = cap.read()
            if not ret:
                # Loop lại từ đầu
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue
            show_frame(frame)
    except Exception as e:
        print(f"Video error: {e}")
    finally:
        cap.release()
        print("⏹️ Video dừng")
        current_state = State.IDLE
        stop_video_flag = False
        show_message(["Ready!", "", "Press button", "to record"], (100, 255, 100))

def start_video_thread(video_url):
    """Bắt đầu phát video trong thread riêng"""
    global video_thread, stop_video_flag
    
    stop_video_flag = False
    video_thread = threading.Thread(target=play_video, args=(video_url,))
    video_thread.start()

def stop_video():
    """Dừng phát video"""
    global stop_video_flag
    stop_video_flag = True
    print("🛑 Yêu cầu dừng video...")

# ============ BUTTON HANDLER ============
def handle_button():
    """Xử lý khi nhấn nút"""
    global current_state, last_button_time, current_audio_file
    
    current_time = time.time()
    double_press = (current_time - last_button_time) < 0.5  # Double press trong 0.5s
    last_button_time = current_time
    
    print(f"🔘 Nút nhấn! State: {current_state}, Double: {double_press}")
    
    # Nếu đang phát video và nhấn đúp → dừng video
    if current_state == State.PLAYING and double_press:
        stop_video()
        return
    
    # State machine
    if current_state == State.IDLE:
        # Bắt đầu ghi âm
        start_recording()
        
    elif current_state == State.RECORDING:
        # Dừng ghi âm và gửi API
        stop_recording()
        
        if current_audio_file and os.path.exists(current_audio_file) and os.path.getsize(current_audio_file) > 1000:
            video_url, transcript = send_to_api(current_audio_file)
            
            # Xóa file audio sau khi gửi
            try:
                os.remove(current_audio_file)
                print(f"🗑️ Đã xóa: {current_audio_file}")
            except:
                pass
            
            if video_url:
                # Phát video
                start_video_thread(video_url)
            else:
                show_message(["API Error!", "", "Try again"], (255, 100, 100))
                time.sleep(2)
                current_state = State.IDLE
                show_message(["Ready!", "", "Press button", "to record"], (100, 255, 100))
        else:
            show_message(["No audio!", "", "Try again"], (255, 100, 100))
            time.sleep(2)
            current_state = State.IDLE
            show_message(["Ready!", "", "Press button", "to record"], (100, 255, 100))
    
    elif current_state == State.PLAYING:
        # Nhấn 1 lần khi đang phát → không làm gì (cần nhấn đúp)
        print("ℹ️ Nhấn đúp để dừng video")

# ============ MAIN ============
def main():
    global current_state
    
    print("=" * 50)
    print("🎤 VOICE TO VSL - Raspberry Pi")
    print("=" * 50)
    print(f"📡 API: {API_URL}")
    print(f"🔘 Button: GPIO {BUTTON_PIN}")
    print("=" * 50)
    
    print("Khởi tạo LCD...")
    init_lcd()
    print("✅ LCD OK!")
    
    show_message(["Voice to VSL", "", "Press button", "to record"], (100, 255, 100))
    
    last_state = GPIO.HIGH
    
    print("\n✅ Sẵn sàng! Nhấn nút để ghi âm...")
    print("   Nhấn Ctrl+C để thoát\n")
    
    try:
        while True:
            current_btn = GPIO.input(BUTTON_PIN)
            
            if last_state == GPIO.HIGH and current_btn == GPIO.LOW:
                handle_button()
                time.sleep(0.3)  # Debounce
            
            last_state = current_btn
            time.sleep(0.01)
            
    except KeyboardInterrupt:
        print("\n👋 Đang thoát...")
        if current_state == State.RECORDING:
            stop_recording()
        if current_state == State.PLAYING:
            stop_video()

if __name__ == "__main__":
    try:
        main()
    finally:
        spi.close()
        GPIO.cleanup()
        print("✅ Cleanup xong!")
