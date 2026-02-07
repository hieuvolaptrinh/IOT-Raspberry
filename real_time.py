#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import cv2
import numpy as np
import spidev
import RPi.GPIO as GPIO
import time
import os
import subprocess
import asyncio
import websockets
import json
import threading
import re
import struct
import queue
from collections import deque
from pathlib import Path
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont
from dataclasses import dataclass
from typing import List, Optional

# WebRTC VAD for speech detection
try:
    import webrtcvad
    VAD_AVAILABLE = True
except ImportError:
    VAD_AVAILABLE = False
    print("⚠️ webrtcvad not installed. Install: pip install webrtcvad")

# ============ LOAD .ENV ============
load_dotenv()
_api_url = os.getenv("API_URL", "ws://172.20.10.11:8000")

# Auto-convert http:// to ws://
if _api_url.startswith("http://"):
    API_URL = _api_url.replace("http://", "ws://", 1)
elif _api_url.startswith("https://"):
    API_URL = _api_url.replace("https://", "wss://", 1)
else:
    API_URL = _api_url

WS_ENDPOINT = "/api/realtime/ws/vsl"

VIDEO_SPEED = 2.0
FINGERSPELL_SPEED = 2.5

# ============ CONNECTION SETTINGS ============
RECONNECT_DELAY = 3
MAX_RECONNECT_ATTEMPTS = 5

# ============ VAD SETTINGS (BALANCED) ============
SAMPLE_RATE = 16000
CHANNELS = 1

FRAME_DURATION_MS = 30
FRAME_SIZE = SAMPLE_RATE * FRAME_DURATION_MS // 1000  # 480 samples

PREROLL_FRAMES = 10                    # 300ms - đủ để không cắt đầu
HANGOVER_FRAMES = 15                   # 450ms - giảm gộp noise
MIN_SPEECH_FRAMES = 7                  # 210ms - tránh segment quá ngắn

SEND_INTERVAL_NORMAL = 0.05
SEND_INTERVAL_VIDEO = 0.1

MIN_RMS_THRESHOLD = 120                # cân bằng
MAX_RMS_THRESHOLD = 32000

PLAYBACK_COOLDOWN_MS = 500             # cooldown sau video
NOISE_CALIBRATION_FRAMES = 50          # ~1.5s calibration

MAX_PENDING_BATCHES = 5

# ============ DISPLAY SETTINGS ============
MIRROR_MODE = True
TARGET_LCD_FPS = 18  # Giới hạn LCD refresh rate
LCD_FRAME_TIME = 1.0 / TARGET_LCD_FPS  # ~55ms per frame

# ============ GPIO PINS ============
BUTTON_PIN = 17
DC_PIN = 24
RST_PIN = 25
BL_PIN = 18

# ============ PATHS ============
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
VIDEO_DIR = os.path.join(SCRIPT_DIR, "video")
FONT_PATH = os.path.join(SCRIPT_DIR, "SVN-Arial Regular.ttf")

# ============ STATE ============
class State:
    IDLE = 0        # Chưa kết nối
    CONNECTING = 1  # Đang kết nối WebSocket
    RECORDING = 2   # Đang ghi âm (kết nối + stream)
    PLAYING = 3     # Đang phát video (vẫn stream audio)

current_state = State.IDLE
is_recording = False  # Toggle for recording mode
stop_streaming = False
stop_video = False
websocket_connected = False
reconnect_count = 0
ws_thread = None

# ============ AUDIO DEVICE ============
def get_usb_audio_device():
    """Auto-detect USB audio device."""
    try:
        result = subprocess.run(['arecord', '-l'], capture_output=True, text=True)
        for line in result.stdout.split('\n'):
            if 'card' in line.lower() and ('usb' in line.lower() or 'pnp' in line.lower()):
                match = re.search(r'card (\d+):', line)
                if match:
                    device = f"plughw:{match.group(1)},0"
                    print(f"🎤 USB Audio: {device}")
                    return device
        return "plughw:0,0"
    except Exception:
        return "plughw:0,0"

AUDIO_DEVICE = get_usb_audio_device()

def boost_mic_capture_volume():
    # fail-open: không phụ thuộc card cụ thể
    for cmd in [
        ["amixer", "set", "Capture", "80%"],
        ["amixer", "set", "Mic", "80%"],
        ["amixer", "set", "PCM", "80%"],
        ["amixer", "set", "Auto Gain Control", "off"],
    ]:
        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except:
            pass

boost_mic_capture_volume()

# ============ FONT ============
try:
    FONT_VN = ImageFont.truetype(FONT_PATH, 22)
    FONT_SMALL = ImageFont.truetype(FONT_PATH, 16)
    FONT_LARGE = ImageFont.truetype(FONT_PATH, 28)
except:
    FONT_VN = ImageFont.load_default()
    FONT_SMALL = ImageFont.load_default()
    FONT_LARGE = ImageFont.load_default()

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
spi.max_speed_hz = 32000000
spi.mode = 3

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
    CHUNK = 32768
    d_bytes = bytes(d) if not isinstance(d, bytes) else d
    for i in range(0, len(d_bytes), CHUNK):
        spi.writebytes2(d_bytes[i:i + CHUNK])

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

_display_buffer = np.empty((240, 240, 2), dtype=np.uint8)
_rgb565_buffer = np.empty((240, 240), dtype=np.uint16)

def _create_text_overlay(text: str) -> np.ndarray:
    """Tạo overlay text dưới dạng BGR numpy array (240x40)."""
    pil_img = Image.new('RGB', (240, 40), (0, 0, 0))
    draw = ImageDraw.Draw(pil_img)
    
    text = text[:30]
    try:
        bbox = draw.textbbox((0, 0), text, font=FONT_VN)
        text_width = bbox[2] - bbox[0]
    except:
        text_width = len(text) * 10
    
    x = max(5, (240 - text_width) // 2)
    draw.text((x, 10), text, font=FONT_VN, fill=(255, 255, 255))
    
    # Convert to BGR numpy array
    return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

def show_frame(frame, overlay_text=None):
    global _display_buffer, _rgb565_buffer

    frame = cv2.resize(frame, (240, 240), interpolation=cv2.INTER_NEAREST)

    # Composite overlay
    if overlay_text:
        overlay = _create_text_overlay(overlay_text)
        frame[200:240, :] = overlay  # Dán overlay vào bottom 40px

    if MIRROR_MODE:
        frame = cv2.flip(frame, 1)

    # Convert BGR to RGB565
    np.add(
        np.add(
            np.left_shift(frame[:, :, 2].astype(np.uint16) >> 3, 11),
            np.left_shift(frame[:, :, 1].astype(np.uint16) >> 2, 5)
        ),
        frame[:, :, 0].astype(np.uint16) >> 3,
        out=_rgb565_buffer
    )

    _display_buffer[:, :, 0] = (_rgb565_buffer >> 8).astype(np.uint8)
    _display_buffer[:, :, 1] = (_rgb565_buffer & 0xFF).astype(np.uint8)

    cmd(0x2A); data([0, 0, 0, 239])
    cmd(0x2B); data([0, 0, 0, 239])
    cmd(0x2C)
    data_bulk(_display_buffer.tobytes())

def show_message(lines, color=(255, 255, 255), bg_color=(0, 0, 0)):
    pil_img = Image.new('RGB', (240, 240), bg_color)
    draw = ImageDraw.Draw(pil_img)

    if isinstance(lines, str):
        lines = lines.split('\n')

    total_height = len(lines) * 35
    start_y = (240 - total_height) // 2

    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=FONT_VN)
        text_width = bbox[2] - bbox[0]
        x = max(5, (240 - text_width) // 2)
        y = start_y + i * 35
        draw.text((x, y), line, font=FONT_VN, fill=color)

    frame = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    show_frame(frame)

# ============ VIDEO MAPPER ============
class VideoMapper:
    RESERVED_NAMES = {'con', 'prn', 'aux', 'nul', 'com1', 'com2', 'lpt1'}
    TONE_MAP = {
        'à': 'a', 'á': 'a', 'ả': 'a', 'ã': 'a', 'ạ': 'a',
        'ă': 'ă', 'ằ': 'ă', 'ắ': 'ă', 'ẳ': 'ă', 'ẵ': 'ă', 'ặ': 'ă',
        'â': 'â', 'ầ': 'â', 'ấ': 'â', 'ẩ': 'â', 'ẫ': 'â', 'ậ': 'â',
        'è': 'e', 'é': 'e', 'ẻ': 'e', 'ẽ': 'e', 'ẹ': 'e',
        'ê': 'ê', 'ề': 'ê', 'ế': 'ê', 'ể': 'ê', 'ễ': 'ê', 'ệ': 'ê',
        'ì': 'i', 'í': 'i', 'ỉ': 'i', 'ĩ': 'i', 'ị': 'i',
        'ò': 'o', 'ó': 'o', 'ỏ': 'o', 'õ': 'o', 'ọ': 'o',
        'ô': 'ô', 'ồ': 'ô', 'ố': 'ô', 'ổ': 'ô', 'ỗ': 'ô', 'ộ': 'ô',
        'ơ': 'ơ', 'ờ': 'ơ', 'ớ': 'ơ', 'ở': 'ơ', 'ỡ': 'ơ', 'ợ': 'ơ',
        'ù': 'u', 'ú': 'u', 'ủ': 'u', 'ũ': 'u', 'ụ': 'u',
        'ư': 'ư', 'ừ': 'ư', 'ứ': 'ư', 'ử': 'ư', 'ữ': 'ư', 'ự': 'ư',
        'ỳ': 'y', 'ý': 'y', 'ỷ': 'y', 'ỹ': 'y', 'ỵ': 'y',
    }

    def __init__(self, video_dir: str):
        self.video_dir = Path(video_dir)
        self.video_cache = {}
        self._scan_videos()
        print(f"📹 VideoMapper: {len(self.video_cache)} videos")

    def _scan_videos(self):
        if not self.video_dir.exists():
            return
        for ext in ['*.mp4', '*.webm']:
            for f in self.video_dir.glob(ext):
                self.video_cache[f.stem.lower()] = f

    def normalize_for_pronunciation(self, text: str) -> str:
        return ''.join(self.TONE_MAP.get(c, c) for c in text.lower())

    def normalize_word(self, word: str) -> str:
        import string
        word = word.translate(str.maketrans('', '', string.punctuation))
        return word.lower().strip()

    def find_video(self, word: str):
        if not word:
            return None
        key = self.normalize_word(word)
        if not key:
            return None

        if key in self.video_cache and self.video_cache[key].exists():
            return self.video_cache[key]

        if key in self.RESERVED_NAMES:
            key_r = key + '_'
            if key_r in self.video_cache and self.video_cache[key_r].exists():
                return self.video_cache[key_r]

        key_u = key.replace(' ', '_')
        if key_u in self.video_cache and self.video_cache[key_u].exists():
            return self.video_cache[key_u]

        key_nt = self.normalize_for_pronunciation(key)
        if key_nt in self.video_cache and self.video_cache[key_nt].exists():
            return self.video_cache[key_nt]

        return None

    def get_fingerspell_videos(self, word: str) -> list:
        result = []
        for char in word.lower():
            if char.isalpha():
                norm = self.TONE_MAP.get(char, char)
                video = self.find_video(norm)
                if video:
                    result.append((norm, video))
                else:
                    return []
            elif char.isdigit():
                video = self.find_video(char)
                if video:
                    result.append((char, video))
                else:
                    return []
        return result

video_mapper = VideoMapper(VIDEO_DIR)

# ============ VIDEO JOB & QUEUE ============
@dataclass
class VideoJob:
    """Đóng gói một job phát video."""
    words: List[str]
    transcript: str
    vsl_text: str = ""
    confidence: float = 0.0

# Pending queue: maxlen=3 tự động drop oldest
pending_video_queue = deque(maxlen=3)
video_queue_lock = threading.Condition()
video_thread_running = True
currently_playing_job = None  # Job đang phát (KHÔNG tính vào pending)

def enqueue_video_job(job: VideoJob):
    """Thêm job vào pending queue. Tự động drop oldest nếu đầy (maxlen=3)."""
    with video_queue_lock:
        pending_video_queue.append(job)  # deque tự drop left nếu maxlen exceeded
        video_queue_lock.notify()  # Wake up worker
        print(f"📥 Enqueued: {job.words[:3] if len(job.words) > 3 else job.words}... | Pending: {len(pending_video_queue)}")

def play_single_video(video_path: str, overlay_word: str = "", max_duration: float = 10.0, speed_multiplier: float = 1.0):
    """
    Play video với frame skipping thông minh để đạt TARGET_LCD_FPS.
    Video vẫn chạy đúng tốc độ (speed_multiplier), nhưng chỉ hiển thị mỗi N frame.
    """
    global stop_video
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return

    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps if fps > 0 else 0

    if duration > max_duration or duration <= 0:
        cap.release()
        return

    # Tính toán frame skip
    effective_fps = fps * speed_multiplier  # FPS sau khi tăng tốc
    
    # Nếu effective_fps > TARGET_LCD_FPS, skip frame
    if effective_fps > TARGET_LCD_FPS:
        frame_skip = int(effective_fps / TARGET_LCD_FPS)
        display_interval = LCD_FRAME_TIME
    else:
        frame_skip = 1
        display_interval = 1.0 / effective_fps
    
    frame_count = 0
    last_display_time = time.time()
    start_time = time.time()

    try:
        while not stop_video:
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_count += 1
            
            # Chỉ hiển thị mỗi N frame
            if frame_count % frame_skip == 0:
                show_frame(frame, overlay_word)
                
                # Throttle LCD refresh
                elapsed = time.time() - last_display_time
                if elapsed < display_interval:
                    time.sleep(display_interval - elapsed)
                last_display_time = time.time()
            
            # Check timeout
            if time.time() - start_time >= max_duration:
                break
                
    finally:
        cap.release()

def video_playback_worker():
    """✅ Worker thread: lấy job từ pending queue và phát video (độc lập với websocket)."""
    global video_thread_running, current_state, stop_video, currently_playing_job
    
    while video_thread_running:
        job = None
        
        # ✅ Wait for job từ pending queue
        with video_queue_lock:
            while len(pending_video_queue) == 0 and video_thread_running:
                video_queue_lock.wait(timeout=0.5)
            
            if not video_thread_running:
                break
            
            if len(pending_video_queue) > 0:
                job = pending_video_queue.popleft()  # ✅ Remove từ pending
                currently_playing_job = job
        
        if job is None:
            continue
        
        try:
            # Set state PLAYING
            current_state = State.PLAYING
            stop_video = False
            
            print(f"🎬 Playing: {job.words} | Remaining pending: {len(pending_video_queue)}")
            
            # Phát từng video
            for word in job.words:
                if stop_video:
                    break
                    
                video_path = video_mapper.find_video(word)
                if video_path:
                    play_single_video(
                        str(video_path),
                        overlay_word=word,
                        speed_multiplier=VIDEO_SPEED
                    )
                else:
                    # Fingerspell fallback
                    letters = video_mapper.get_fingerspell_videos(word)
                    if letters:
                        for letter, letter_video in letters:
                            if stop_video:
                                break
                            play_single_video(
                                str(letter_video),
                                overlay_word=word,
                                speed_multiplier=FINGERSPELL_SPEED
                            )
            
            # ✅ Signal kết thúc phát video (cho UI)
            signal_playback_ended()
            
            # ✅ Về RECORDING nếu vẫn đang recording mode
            if not stop_video and is_recording:
                current_state = State.RECORDING
                show_message(["🔴 GHI ÂM", "", "Đang nghe...", "Nhấn nút để dừng"], (255, 100, 100), (50, 0, 0))
        
        except Exception as e:
            print(f"❌ Video worker error: {e}")
        finally:
            currently_playing_job = None

def play_video_sequence(words: list, transcript: str = "", vsl_text: str = "", confidence: float = 0.0):
    """✅ [BACKWARD COMPAT] Wrapper cho enqueue_video_job()."""
    job = VideoJob(words=words, transcript=transcript, vsl_text=vsl_text, confidence=confidence)
    enqueue_video_job(job)

video_thread = threading.Thread(target=video_playback_worker, daemon=True)
video_thread.start()

# ============ COOLDOWN SIGNAL (global) ============
_playback_end_time = 0.0

def signal_playback_ended():
    """Gọi khi video playback kết thúc để trigger cooldown."""
    global _playback_end_time
    _playback_end_time = time.time()

# ============ VAD-BASED AUDIO STREAMING (OPTIMIZED) ============
class VADAudioStreamer:
    """
    Optimized VAD Streamer cho Raspberry Pi Zero 2.
    - webrtcvad mode 2 (balanced)
    - Adaptive noise floor calibration
    - Cooldown sau video playback
    """
    MAX_SPEECH_SECONDS = 8.0  # Giảm để tránh Whisper hallucinate

    def __init__(self):
        # Mode 2 = balanced (giảm false positive, vẫn nhạy)
        self.vad = webrtcvad.Vad(2) if VAD_AVAILABLE else None

        self.preroll_buffer = deque(maxlen=PREROLL_FRAMES)
        self.speech_buffer = bytearray()

        self.in_speech = False
        self.hangover_counter = 0
        self.speech_frame_count = 0
        self.last_send_time = time.time()

        # Stats
        self.frames_processed = 0
        self.frames_sent = 0

    def _calculate_rms(self, audio_bytes: bytes) -> float:
        """RMS calculation using numpy for speed."""
        if len(audio_bytes) < 2:
            return 0.0
        samples = np.frombuffer(audio_bytes, dtype=np.int16)
        return float(np.sqrt(np.mean(samples.astype(np.float32) ** 2)))

    def process_frame(self, frame_bytes: bytes) -> bytes:
        self.frames_processed += 1

        # ❌ REMOVED COOLDOWN: Audio stream phải luôn chạy, kể cả khi phát video
        # Backend sẽ lo AEC/echo cancellation nếu cần

        rms = self._calculate_rms(frame_bytes)

        # Debug log mỗi 200 frames (~6s)
        if self.frames_processed % 200 == 0:
            print(f"🎤 RMS={rms:.0f} | in_speech={self.in_speech}")

        # Skip silence hoàn toàn (RMS < 5 = hoàn toàn im lặng)
        if rms < 5:
            if not self.in_speech:
                self.preroll_buffer.append(frame_bytes)
            return b''

        # Skip clipping
        if rms > MAX_RMS_THRESHOLD:
            return b''

        # Fixed threshold thấp - để Silero VAD backend lọc
        threshold = 80  # Threshold cố định thấp

        # VAD decision
        is_speech = False
        if self.vad:
            try:
                is_speech = self.vad.is_speech(frame_bytes, SAMPLE_RATE)
                # Chỉ reject nếu RMS quá thấp (< 50)
                if is_speech and rms < 50:
                    is_speech = False
            except:
                is_speech = rms > threshold
        else:
            # Không có VAD: dựa vào RMS
            is_speech = rms > threshold

        if is_speech:
            if not self.in_speech:
                self.in_speech = True
                self.speech_frame_count = 0
                print(f"🎙️ Speech START (rms={rms:.0f}, threshold={threshold:.0f})")
                for pf in self.preroll_buffer:
                    self.speech_buffer.extend(pf)
                self.preroll_buffer.clear()

            self.speech_buffer.extend(frame_bytes)
            self.speech_frame_count += 1
            self.hangover_counter = HANGOVER_FRAMES

            if self.speech_frame_count >= int(self.MAX_SPEECH_SECONDS * 1000 / FRAME_DURATION_MS):
                return self._flush()
        else:
            if self.in_speech:
                if self.hangover_counter > 0:
                    self.speech_buffer.extend(frame_bytes)
                    self.hangover_counter -= 1
                else:
                    return self._flush()
            else:
                self.preroll_buffer.append(frame_bytes)

        return b''

    def _flush(self) -> bytes:
        """Flush speech buffer if meets minimum length."""
        self.in_speech = False
        self.hangover_counter = 0
        
        if self.speech_frame_count >= MIN_SPEECH_FRAMES:
            result = bytes(self.speech_buffer)
            self.frames_sent += self.speech_frame_count
        else:
            result = b''
        
        self.speech_buffer = bytearray()
        self.speech_frame_count = 0
        return result

    def should_send_batch(self, is_video_playing: bool = False) -> bool:
        interval = SEND_INTERVAL_VIDEO if is_video_playing else SEND_INTERVAL_NORMAL
        return (time.time() - self.last_send_time) >= interval

    def mark_batch_sent(self):
        self.last_send_time = time.time()

    def flush(self) -> bytes:
        """Force flush remaining buffer."""
        return self._flush()

    def get_stats(self) -> dict:
        total = self.frames_processed or 1
        return {
            'processed': self.frames_processed,
            'sent': self.frames_sent,
            'reduction': f"{100 * (1 - self.frames_sent / total):.1f}%"
        }

async def stream_audio_to_server(ws):
    """Stream audio to server with VAD filtering."""
    global stop_streaming, current_state
    
    streamer = VADAudioStreamer()
    frame_bytes = FRAME_SIZE * 2  # 16-bit

    print(f"🎤 Starting audio stream (frame={FRAME_DURATION_MS}ms)")

    process = subprocess.Popen([
        'arecord', '-D', AUDIO_DEVICE,
        '-f', 'S16_LE', '-r', str(SAMPLE_RATE),
        '-c', str(CHANNELS), '-t', 'raw', '-'
    ], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=frame_bytes * 2)

    try:
        while not stop_streaming and websocket_connected:
            frame = process.stdout.read(frame_bytes)
            if not frame or len(frame) < frame_bytes:
                break

            # Xử lý VAD và gửi khi có speech
            speech_data = streamer.process_frame(frame)

            if speech_data:
                try:
                    await ws.send(speech_data)
                    print(f"📤 Sent {len(speech_data)} bytes")
                except websockets.exceptions.ConnectionClosed:
                    print("🔌 Connection closed during send")
                    break
                except Exception as e:
                    print(f"❌ Send error: {e}")
                    break
            
            # Nhỏ delay để không block asyncio
            await asyncio.sleep(0.001)

    finally:
        # Flush remaining
        if websocket_connected:
            try:
                remain = streamer.flush()
                if remain:
                    await ws.send(remain)
                await ws.send(json.dumps({'type': 'flush'}))
            except:
                pass

        process.terminate()
        process.wait()
        print(f"🎤 Stream ended: {streamer.get_stats()}")

async def receive_results(ws):
    """✅ Receive results và CHỈ enqueue job. KHÔNG phát video ở đây (avoid blocking)."""
    global current_state, stop_streaming, websocket_connected

    try:
        async for message in ws:
            if stop_streaming:
                break

            try:
                data = json.loads(message)
                msg_type = data.get('type', '')

                if msg_type == 'connected':
                    websocket_connected = True
                    print(f"✅ Connected: {data.get('message', '')}")
                    current_state = State.RECORDING
                    show_message(["🔴 ĐANG GHI ÂM", "", "Nói vào micro...", "Nhấn nút để dừng"], (255, 100, 100), (50, 0, 0))

                elif msg_type == 'buffering':
                    progress = data.get('progress', 0)
                    print(f"   📊 Buffering: {progress*100:.0f}%")

                elif msg_type == 'result':
                    transcript = data.get('transcript', '')
                    words = data.get('words', [])
                    vsl_text = data.get('vsl_text', '')
                    confidence = data.get('confidence', 0)
                    
                    print(f"📝 Result: {transcript} → {words}")
                    print(f"   VSL: {vsl_text} | Conf: {confidence:.2f}")
                    
                    if words:
                        # ✅ CHỈ enqueue, KHÔNG block receive loop
                        job = VideoJob(
                            words=words,
                            transcript=transcript,
                            vsl_text=vsl_text,
                            confidence=confidence
                        )
                        enqueue_video_job(job)
                    else:
                        print(f"⚠️ Empty words: {transcript}")

                elif msg_type == 'filtered':
                    reason = data.get('reason', 'unknown')
                    transcript = data.get('transcript', '')
                    print(f"🚫 Filtered: {transcript} ({reason})")
                    # Brief non-blocking message
                    if current_state == State.RECORDING:
                        show_message(["🚫 ĐÃ LỌC", "", transcript[:30], f"({reason})"], (255, 200, 0), (50, 30, 0))
                        await asyncio.sleep(1.0)
                        if current_state == State.RECORDING:  # Re-check
                            show_message(["🔴 GHI ÂM", "", "Đang nghe...", "Nhấn nút để dừng"], (255, 100, 100), (50, 0, 0))

                elif msg_type == 'error':
                    error_msg = data.get('error', 'Unknown error')
                    print(f"❌ Server error: {error_msg}")
                    show_message(["❌ Lỗi", "", error_msg[:30]], (255, 100, 100))

                elif msg_type == 'pong':
                    pass  # Heartbeat response

                # Free memory
                del data

            except json.JSONDecodeError as e:
                print(f"❌ JSON decode error: {e}")
            except Exception as e:
                print(f"❌ Message handling error: {e}")

    except websockets.exceptions.ConnectionClosed as e:
        print(f"🔌 Connection closed: {e.code if hasattr(e, 'code') else 'unknown'}")
    except Exception as e:
        print(f"❌ Receive error: {e}")
    finally:
        websocket_connected = False

# ❌ REMOVED: play_video_sequence_direct()
# Lý do: Function này BLOCK receive_results loop → không nhận result mới khi phát video
# ✅ Thay bằng: enqueue_video_job() + video_playback_worker() thread độc lập

async def send_heartbeat(ws):
    """Send periodic heartbeat."""
    try:
        while not stop_streaming and websocket_connected:
            await asyncio.sleep(15)
            if websocket_connected:
                try:
                    await ws.send(json.dumps({'type': 'ping'}))
                except:
                    break
    except:
        pass

async def websocket_session():
    """Main WebSocket session - uses asyncio.wait like old working code."""
    global current_state, stop_streaming, websocket_connected, reconnect_count, is_recording

    ws_url = f"{API_URL}{WS_ENDPOINT}"
    print(f"🔌 Connecting to: {ws_url}")

    try:
        async with websockets.connect(
            ws_url,
            ping_interval=30,
            ping_timeout=60,
            close_timeout=10
        ) as ws:
            websocket_connected = True
            current_state = State.RECORDING
            reconnect_count = 0
            
            show_message(["🔴 ĐANG GHI ÂM", "", "Nói vào micro...", "Nhấn nút để dừng"], (255, 100, 100), (50, 0, 0))

            # Tạo tasks
            sender = asyncio.create_task(stream_audio_to_server(ws))
            receiver = asyncio.create_task(receive_results(ws))
            heartbeat = asyncio.create_task(send_heartbeat(ws))

            # Chờ bất kỳ task nào hoàn thành (giống code cũ)
            done, pending = await asyncio.wait(
                [sender, receiver, heartbeat],
                return_when=asyncio.FIRST_COMPLETED
            )

            # Cancel pending tasks
            for task in pending:
                task.cancel()

    except websockets.exceptions.ConnectionClosed:
        print("🔌 Connection closed")
    except ConnectionRefusedError:
        print("❌ Connection refused - is server running?")
        show_message(["Không thể kết nối!", "Server chưa chạy?"], (255, 100, 100))
    except Exception as e:
        print(f"❌ Connection error: {e}")
        show_message(["Lỗi kết nối!", str(e)[:20]], (255, 100, 100))
    finally:
        websocket_connected = False
        current_state = State.IDLE

async def websocket_session_with_reconnect():
    global reconnect_count, stop_streaming

    while not stop_streaming and reconnect_count < MAX_RECONNECT_ATTEMPTS:
        await websocket_session()

        if stop_streaming:
            break

        reconnect_count += 1
        if reconnect_count < MAX_RECONNECT_ATTEMPTS:
            print(f"🔄 Reconnecting ({reconnect_count}/{MAX_RECONNECT_ATTEMPTS})...")
            await asyncio.sleep(RECONNECT_DELAY)

def start_websocket_thread():
    global stop_streaming, reconnect_count
    stop_streaming = False
    reconnect_count = 0

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(websocket_session_with_reconnect())
    finally:
        loop.close()

# ============ BUTTON HANDLER (TOGGLE MODE) ============
def handle_button():
    """
    Simple toggle button flow:
    - Press 1: Connect + Start recording
    - Press 2: Stop recording + Disconnect
    - During video: Stop video
    """
    global current_state, is_recording, stop_streaming, stop_video, ws_thread

    state_names = {0: 'IDLE', 1: 'CONNECTING', 2: 'RECORDING', 3: 'PLAYING'}
    print(f"🔘 Button! State: {state_names.get(current_state, current_state)}, Recording: {is_recording}")

    # === Đang phát video → Dừng video ===
    if current_state == State.PLAYING:
        print("⏹️ Stopping video...")
        stop_video = True
        # ✅ Clear pending queue
        with video_queue_lock:
            pending_video_queue.clear()
            print(f"🧹 Cleared pending queue")
        return

    # === Toggle recording ===
    if not is_recording:
        # ===== START RECORDING =====
        print("� Starting recording...")
        is_recording = True
        stop_streaming = False
        stop_video = False
        current_state = State.CONNECTING

        show_message(["🔴 GHI ÂM", "", "Đang kết nối...", "Nhấn nút để dừng"], (255, 100, 100), (50, 0, 0))

        # Start WebSocket in background thread
        ws_thread = threading.Thread(target=start_websocket_thread, daemon=True)
        ws_thread.start()

    else:
        # ===== STOP RECORDING =====
        print("⏹️ Stopping recording...")
        is_recording = False
        stop_streaming = True
        stop_video = True

        # ✅ Clear pending queue
        with video_queue_lock:
            pending_video_queue.clear()
            print(f"🧹 Cleared pending queue")

        current_state = State.IDLE
        show_message(["Đã dừng ghi âm", "", "Nhấn nút để", "ghi lại"], (100, 255, 100))

# ============ MAIN ============
def main():
    global current_state

    print(f"📡 Server: {API_URL}")
    print(f"📹 Videos: {len(video_mapper.video_cache)}")
    print(f"🎙️ VAD: {'ENABLED' if VAD_AVAILABLE else 'DISABLED (RMS only)'}")
    print(f"🔧 Frame: {FRAME_DURATION_MS}ms, Pre-roll: {PREROLL_FRAMES * FRAME_DURATION_MS}ms, Hangover: {HANGOVER_FRAMES * FRAME_DURATION_MS}ms")
    print("=" * 50)

    init_lcd()
    print("✅ LCD OK!")

    show_message(["Real-Time VSL", "", "Nhấn nút để", "bắt đầu"], (100, 255, 100))

    last_state = GPIO.HIGH
    print("\n✅ Ready! Press button to start...")

    try:
        while True:
            current_btn = GPIO.input(BUTTON_PIN)

            if last_state == GPIO.HIGH and current_btn == GPIO.LOW:
                handle_button()
                time.sleep(0.3)

            last_state = current_btn
            time.sleep(0.01)

    except KeyboardInterrupt:
        print("\n👋 Exiting...")
        stop_streaming = True
        stop_video = True

if __name__ == "__main__":
    try:
        main()
    finally:
        spi.close()
        GPIO.cleanup()
        print("✅ Cleanup done!")
