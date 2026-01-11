#!/usr/bin/env python3
"""
Voice to VSL - Raspberry Pi Zero 2 W
=====================================
Script ghi âm từ microphone, gửi đến API và hiển thị kết quả lên LCD.

Hardware Setup (Raspberry Pi Zero 2 W):
┌─────────────────────────────────────────────────────────────────┐
│  RASPBERRY PI ZERO 2 W - 40 PIN GPIO HEADER                    │
├─────────────────────────────────────────────────────────────────┤
│  LCD 16x2 I2C (gắn trực tiếp vào GPIO header):                 │
│    - VCC  → Pin 2 hoặc 4 (5V)                                  │
│    - GND  → Pin 6 (GND)                                        │
│    - SDA  → Pin 3 (GPIO 2 / SDA1)                              │
│    - SCL  → Pin 5 (GPIO 3 / SCL1)                              │
│                                                                 │
│  NÚT NHẤN (gắn vào GPIO header):                               │
│    - Chân 1 → Pin 11 (GPIO 17)                                 │
│    - Chân 2 → Pin 9 (GND)                                      │
│                                                                 │
│  LED TRẠNG THÁI (optional):                                    │
│    - (+) → 220Ω resistor → Pin 13 (GPIO 27)                    │
│    - (-) → Pin 14 (GND)                                        │
│                                                                 │
│  MICROPHONE:                                                   │
│    - Gắn qua cổng Micro-B USB (cổng DATA, không phải PWR)      │
│    - Sử dụng USB OTG adapter nếu cần                           │
└─────────────────────────────────────────────────────────────────┘

Cách sử dụng:
1. SSH vào Raspberry Pi: ssh pi@<ip-address>
2. Chỉnh API_URL bên dưới cho phù hợp với IP của PC server
3. Chạy script: python3 voice_to_vsl.py
4. Nhấn nút để bắt đầu ghi âm (LED sáng)
5. Nhấn lại để dừng và gửi đến API
"""

import os
import sys
import time
import wave
import threading
import requests
from datetime import datetime

# ============================================
# CẤU HÌNH - CHỈNH SỬA Ở ĐÂY KHI SSH
# ============================================

# URL của API server (IP PC của bạn chạy backend)
# Chỉnh IP này khi SSH vào Raspberry Pi
# Ví dụ: "http://192.168.1.100:8000" hoặc "http://172.20.10.8:8000"
API_URL = "http://172.20.10.8:8000"

# Endpoint API
API_ENDPOINT = "/api/vsl/convert-audio-simple"

# ============================================
# GPIO PINS (theo BCM numbering)
# ============================================
BUTTON_PIN = 17      # Pin 11 trên header - Nút nhấn
LED_PIN = 27         # Pin 13 trên header - LED trạng thái

# ============================================
# LCD I2C SETTINGS (gắn vào GPIO header)
# ============================================
LCD_ADDRESS = 0x27   # Địa chỉ I2C (chạy i2cdetect -y 1 để kiểm tra)
LCD_COLS = 16        # Số cột LCD (16 hoặc 20)
LCD_ROWS = 2         # Số hàng LCD (2 hoặc 4)

# ============================================
# AUDIO SETTINGS (Mic USB qua cổng Micro-B)
# ============================================
AUDIO_DEVICE = "plughw:1,0"  # USB mic thường là device 1 (chạy arecord -l để kiểm tra)
AUDIO_RATE = 44100           # Sample rate
AUDIO_CHANNELS = 1           # Mono
AUDIO_CHUNK = 1024           # Chunk size

# ============================================
# RECORDING SETTINGS
# ============================================
RECORDING_DIR = "/home/pi/recordings"  # Thư mục lưu file ghi âm
MAX_RECORDING_TIME = 60  # Thời gian ghi âm tối đa (giây)

# ============================================
# LIBRARY IMPORTS (với fallback cho testing)
# ============================================

# Try importing hardware libraries
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
    print("⚠️  RPi.GPIO không có sẵn - chạy ở chế độ test")

try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False
    print("⚠️  PyAudio không có sẵn - chạy ở chế độ test")

try:
    from RPLCD.i2c import CharLCD
    LCD_AVAILABLE = True
except ImportError:
    LCD_AVAILABLE = False
    print("⚠️  RPLCD không có sẵn - chạy ở chế độ test")

# ============================================
# GLOBAL VARIABLES
# ============================================

is_recording = False
recording_thread = None
audio_frames = []
last_video_url = ""
last_transcript = ""

# ============================================
# LCD FUNCTIONS
# ============================================

lcd = None

def init_lcd():
    """Khởi tạo LCD"""
    global lcd
    if LCD_AVAILABLE:
        try:
            lcd = CharLCD(i2c_expander='PCF8574', address=LCD_ADDRESS,
                         port=1, cols=LCD_COLS, rows=LCD_ROWS,
                         dotsize=8, charmap='A02', auto_linebreaks=True)
            lcd.clear()
            lcd_print("Voice to VSL", "Ready!")
            print("✅ LCD initialized")
        except Exception as e:
            print(f"❌ LCD init error: {e}")
            lcd = None
    else:
        print("📺 LCD (simulated)")

def lcd_print(line1, line2=""):
    """Hiển thị text lên LCD"""
    if lcd:
        try:
            lcd.clear()
            lcd.write_string(line1[:LCD_COLS])
            if line2:
                lcd.crlf()
                lcd.write_string(line2[:LCD_COLS])
        except Exception as e:
            print(f"LCD error: {e}")
    else:
        print(f"📺 LCD: {line1}")
        if line2:
            print(f"📺      {line2}")

def lcd_scroll_url(url, delay=0.3):
    """Cuộn URL dài trên LCD"""
    if len(url) <= LCD_COLS:
        lcd_print("Video URL:", url)
        return
    
    # Cuộn text
    text = url + "   "
    for i in range(len(text) - LCD_COLS + 1):
        lcd_print("Video URL:", text[i:i + LCD_COLS])
        time.sleep(delay)

# ============================================
# GPIO FUNCTIONS
# ============================================

def init_gpio():
    """Khởi tạo GPIO"""
    if GPIO_AVAILABLE:
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(LED_PIN, GPIO.OUT)
        GPIO.output(LED_PIN, GPIO.LOW)
        print("✅ GPIO initialized")
    else:
        print("🔌 GPIO (simulated)")

def led_on():
    """Bật LED"""
    if GPIO_AVAILABLE:
        GPIO.output(LED_PIN, GPIO.HIGH)
    print("💡 LED ON")

def led_off():
    """Tắt LED"""
    if GPIO_AVAILABLE:
        GPIO.output(LED_PIN, GPIO.LOW)
    print("💡 LED OFF")

def led_blink(times=3, delay=0.2):
    """Nháy LED"""
    for _ in range(times):
        led_on()
        time.sleep(delay)
        led_off()
        time.sleep(delay)

# ============================================
# AUDIO RECORDING FUNCTIONS
# ============================================

def record_audio():
    """Ghi âm từ microphone"""
    global audio_frames, is_recording
    
    if not PYAUDIO_AVAILABLE:
        print("⚠️  PyAudio không có sẵn, sử dụng arecord")
        return record_audio_alsa()
    
    audio_frames = []
    p = pyaudio.PyAudio()
    
    try:
        stream = p.open(
            format=pyaudio.paInt16,
            channels=AUDIO_CHANNELS,
            rate=AUDIO_RATE,
            input=True,
            frames_per_buffer=AUDIO_CHUNK
        )
        
        print("🎤 Recording started...")
        start_time = time.time()
        
        while is_recording:
            if time.time() - start_time > MAX_RECORDING_TIME:
                print("⏱️ Max recording time reached")
                break
            data = stream.read(AUDIO_CHUNK, exception_on_overflow=False)
            audio_frames.append(data)
        
        stream.stop_stream()
        stream.close()
        print("🎤 Recording stopped")
        
    except Exception as e:
        print(f"❌ Recording error: {e}")
    finally:
        p.terminate()

def record_audio_alsa():
    """Ghi âm sử dụng arecord (fallback)"""
    global is_recording
    
    os.makedirs(RECORDING_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    audio_path = f"{RECORDING_DIR}/recording_{timestamp}.wav"
    
    print("🎤 Recording with arecord...")
    
    # Chạy arecord trong background
    import subprocess
    process = subprocess.Popen([
        'arecord',
        '-D', 'plughw:1,0',  # USB mic thường là device 1
        '-f', 'S16_LE',
        '-r', str(AUDIO_RATE),
        '-c', str(AUDIO_CHANNELS),
        audio_path
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    start_time = time.time()
    while is_recording:
        if time.time() - start_time > MAX_RECORDING_TIME:
            break
        time.sleep(0.1)
    
    process.terminate()
    process.wait()
    
    print(f"🎤 Audio saved: {audio_path}")
    return audio_path

def save_audio(filename):
    """Lưu audio frames thành file WAV"""
    if not audio_frames:
        print("⚠️ No audio to save")
        return None
    
    os.makedirs(RECORDING_DIR, exist_ok=True)
    filepath = os.path.join(RECORDING_DIR, filename)
    
    try:
        wf = wave.open(filepath, 'wb')
        wf.setnchannels(AUDIO_CHANNELS)
        wf.setsampwidth(2)  # 16-bit = 2 bytes
        wf.setframerate(AUDIO_RATE)
        wf.writeframes(b''.join(audio_frames))
        wf.close()
        print(f"💾 Audio saved: {filepath}")
        return filepath
    except Exception as e:
        print(f"❌ Save error: {e}")
        return None

# ============================================
# API FUNCTIONS
# ============================================

def send_audio_to_api(audio_path):
    """Gửi audio file đến API và nhận video URL"""
    global last_video_url, last_transcript
    
    url = f"{API_URL}{API_ENDPOINT}"
    print(f"📤 Sending to: {url}")
    
    try:
        with open(audio_path, 'rb') as f:
            files = {'file': (os.path.basename(audio_path), f, 'audio/wav')}
            response = requests.post(url, files=files, timeout=120)
        
        if response.status_code == 200:
            data = response.json()
            
            # Handle response format
            if 'data' in data:
                result = data['data']
            else:
                result = data
            
            last_video_url = result.get('video_url', 'N/A')
            last_transcript = result.get('transcript', 'N/A')
            
            print(f"✅ Success!")
            print(f"📹 Video URL: {last_video_url}")
            print(f"📝 Transcript: {last_transcript}")
            
            return True
        else:
            print(f"❌ API Error: {response.status_code}")
            print(response.text)
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to {API_URL}")
        print("   Kiểm tra: PC có đang chạy server không?")
        print("   Kiểm tra: IP address đúng chưa?")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

# ============================================
# MAIN BUTTON HANDLER
# ============================================

def button_callback(channel=None):
    """Xử lý khi nhấn nút"""
    global is_recording, recording_thread
    
    if not is_recording:
        # Bắt đầu ghi âm
        is_recording = True
        led_on()
        lcd_print("Recording...", "Press to stop")
        
        recording_thread = threading.Thread(target=record_audio)
        recording_thread.start()
        
    else:
        # Dừng ghi âm và gửi đến API
        is_recording = False
        led_off()
        lcd_print("Processing...", "Please wait")
        
        if recording_thread:
            recording_thread.join()
        
        # Lưu audio
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        audio_path = save_audio(f"recording_{timestamp}.wav")
        
        if audio_path and os.path.exists(audio_path):
            lcd_print("Sending...", "to API")
            
            # Gửi đến API
            if send_audio_to_api(audio_path):
                led_blink(3, 0.1)
                
                # Hiển thị kết quả
                lcd_print("Success!", "")
                time.sleep(1)
                
                # Hiển thị transcript (rút gọn)
                short_transcript = last_transcript[:LCD_COLS] if last_transcript else "N/A"
                lcd_print("Transcript:", short_transcript)
                time.sleep(2)
                
                # Hiển thị URL (cuộn nếu dài)
                lcd_scroll_url(last_video_url)
                
            else:
                lcd_print("Error!", "Check API")
                led_blink(5, 0.1)
        else:
            lcd_print("No audio!", "Try again")
        
        # Cleanup
        if audio_path and os.path.exists(audio_path):
            try:
                os.remove(audio_path)
                print(f"🗑️ Deleted: {audio_path}")
            except:
                pass
        
        time.sleep(2)
        lcd_print("Voice to VSL", "Ready!")

# ============================================
# TEST MODE (không cần hardware)
# ============================================

def test_api():
    """Test gọi API với file audio có sẵn"""
    print("\n" + "="*50)
    print("🧪 TEST MODE - Gọi API với file test")
    print("="*50)
    
    # Tìm file test
    test_files = [
        "test-voice-AI.m4a",
        "/home/pi/test.wav",
        "test.wav"
    ]
    
    test_file = None
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    for f in test_files:
        path = os.path.join(script_dir, f) if not f.startswith('/') else f
        if os.path.exists(path):
            test_file = path
            break
    
    if not test_file:
        print("❌ Không tìm thấy file test")
        print("   Đặt file audio vào cùng thư mục với script")
        return
    
    print(f"📁 Using: {test_file}")
    print(f"🌐 API: {API_URL}{API_ENDPOINT}")
    print()
    
    if send_audio_to_api(test_file):
        print("\n✅ TEST PASSED!")
        print(f"📹 Video: {last_video_url}")
        print(f"📝 Text: {last_transcript}")
    else:
        print("\n❌ TEST FAILED!")

def interactive_test():
    """Chế độ test tương tác (không cần hardware)"""
    print("\n" + "="*50)
    print("🎮 INTERACTIVE TEST MODE")
    print("="*50)
    print("Commands:")
    print("  r - Simulate record start")
    print("  s - Simulate record stop (send to API)")
    print("  t - Test API with sample file")
    print("  u - Change API URL")
    print("  q - Quit")
    print("="*50)
    
    while True:
        cmd = input("\n> ").strip().lower()
        
        if cmd == 'r':
            print("🔴 [SIMULATED] Recording started...")
            print("   (Press 's' to stop and send)")
        
        elif cmd == 's':
            print("⏹️ [SIMULATED] Recording stopped")
            test_api()
        
        elif cmd == 't':
            test_api()
        
        elif cmd == 'u':
            global API_URL
            new_url = input("Enter new API URL: ").strip()
            if new_url:
                API_URL = new_url
                print(f"✅ API URL updated: {API_URL}")
        
        elif cmd == 'q':
            print("Goodbye!")
            break
        
        else:
            print("Unknown command")

# ============================================
# MAIN
# ============================================

def main():
    """Main function"""
    print("\n" + "="*50)
    print("🎤 Voice to VSL - Raspberry Pi Zero 2 W")
    print("="*50)
    print(f"API URL: {API_URL}")
    print(f"Endpoint: {API_ENDPOINT}")
    print("="*50 + "\n")
    
    # Check arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == 'test':
            test_api()
            return
        elif sys.argv[1] == 'interactive':
            interactive_test()
            return
        elif sys.argv[1].startswith('http'):
            global API_URL
            API_URL = sys.argv[1]
            print(f"✅ API URL set to: {API_URL}")
    
    # Initialize hardware
    init_gpio()
    init_lcd()
    
    if not GPIO_AVAILABLE:
        print("\n⚠️  Không có GPIO - chuyển sang chế độ interactive")
        interactive_test()
        return
    
    # Setup button interrupt
    GPIO.add_event_detect(
        BUTTON_PIN,
        GPIO.FALLING,
        callback=button_callback,
        bouncetime=500
    )
    
    print("✅ Ready! Press button to record.")
    print("   Press Ctrl+C to exit.\n")
    
    lcd_print("Voice to VSL", "Press button")
    
    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n👋 Exiting...")
    finally:
        if GPIO_AVAILABLE:
            GPIO.cleanup()
        if lcd:
            lcd.clear()
            lcd.write_string("Goodbye!")

if __name__ == "__main__":
    main()
