
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
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont

# WebRTC VAD for speech detection
try:
    import webrtcvad
    VAD_AVAILABLE = True
except ImportError:
    VAD_AVAILABLE = False
    print("⚠️ webrtcvad not installed. Install: pip install webrtcvad")

# ============ LOAD .ENV ============
load_dotenv()
_api_url = os.getenv("API_URL", "ws://172.20.10.3:8000")

# Auto-convert http:// to ws://
if _api_url.startswith("http://"):
    API_URL = _api_url.replace("http://", "ws://", 1)
elif _api_url.startswith("https://"):
    API_URL = _api_url.replace("https://", "wss://", 1)
else:
    API_URL = _api_url

WS_ENDPOINT = "/api/realtime/ws/vsl"

VIDEO_SPEED = 2.0
FINGERSPELL_SPEED = 2.0

# ============ CONNECTION SETTINGS ============
RECONNECT_DELAY = 3
MAX_RECONNECT_ATTEMPTS = 5

# ============ VAD SETTINGS (OPTIMIZED) ============
SAMPLE_RATE = 16000
CHANNELS = 1
FRAME_DURATION_MS = 20          # WebRTC VAD frame size (10, 20, or 30ms)
FRAME_SIZE = SAMPLE_RATE * FRAME_DURATION_MS // 1000  # 320 samples at 16kHz

# Speech detection thresholds
PREROLL_FRAMES = 12             # 240ms pre-roll buffer (keep before speech start)
HANGOVER_FRAMES = 35            # 700ms hangover (keep after speech end)
MIN_SPEECH_FRAMES = 5           # Minimum 100ms speech to send

# Batch sending (reduce WebSocket overhead)
SEND_INTERVAL_NORMAL = 0.12     # 120ms batch while recording
SEND_INTERVAL_VIDEO = 0.24      # 240ms batch while video playing

# RMS backup threshold (reject wind/fan noise)
MIN_RMS_THRESHOLD = 300
MAX_RMS_THRESHOLD = 25000       # Reject clipping/too loud

# Queue limit to prevent memory overflow
MAX_PENDING_BATCHES = 3

# ============ DISPLAY SETTINGS ============
MIRROR_MODE = True


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
    IDLE = 0
    CONNECTING = 1
    RECORDING = 2
    PROCESSING = 3
    PLAYING = 4

current_state = State.IDLE
is_recording = False
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
        spi.writebytes2(d_bytes[i:i+CHUNK])


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


def show_frame(frame, overlay_text=None):
    """Display frame on LCD with optional text overlay."""
    global _display_buffer, _rgb565_buffer
    
    frame = cv2.resize(frame, (240, 240), interpolation=cv2.INTER_NEAREST)
    
    if overlay_text:
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(frame_rgb)
        draw = ImageDraw.Draw(pil_img)
        draw.rectangle([(0, 200), (240, 240)], fill=(0, 0, 0))
        text = overlay_text[:30]
        try:
            bbox = draw.textbbox((0, 0), text, font=FONT_VN)
            text_width = bbox[2] - bbox[0]
        except:
            text_width = len(text) * 10
        x = max(5, (240 - text_width) // 2)
        draw.text((x, 210), text, font=FONT_VN, fill=(255, 255, 255))
        frame = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    
    if MIRROR_MODE:
        frame = cv2.flip(frame, 1)
    
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
    """Display text message on LCD."""
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
    """Map words to local video files."""
    
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
    
    def find_video(self, word: str) -> Path:
        if not word:
            return None
        
        key = self.normalize_word(word)
        if not key:
            return None
        
        # Exact match
        if key in self.video_cache and self.video_cache[key].exists():
            return self.video_cache[key]
        
        # Reserved names (con -> con_)
        if key in self.RESERVED_NAMES:
            key_r = key + '_'
            if key_r in self.video_cache and self.video_cache[key_r].exists():
                return self.video_cache[key_r]
        
        # Underscore format
        key_u = key.replace(' ', '_')
        if key_u in self.video_cache and self.video_cache[key_u].exists():
            return self.video_cache[key_u]
        
        # No tone
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


# ============ VIDEO PLAYBACK ============
video_queue = queue.Queue()
video_thread_running = True


def video_playback_worker():
    global video_thread_running, current_state, stop_video
    
    while video_thread_running:
        try:
            task = video_queue.get(timeout=0.5)
            if task is None:
                continue
            
            words, transcript = task
            current_state = State.PLAYING
            stop_video = False
            
            for word in words:
                if stop_video:
                    break
                
                video_path = video_mapper.find_video(word)
                
                if video_path:
                    play_single_video(str(video_path), transcript, speed_multiplier=VIDEO_SPEED)
                else:
                    letters = video_mapper.get_fingerspell_videos(word)
                    if letters:
                        for letter, lv in letters:
                            if stop_video:
                                break
                            play_single_video(str(lv), transcript, speed_multiplier=FINGERSPELL_SPEED)
            
            current_state = State.RECORDING
            stop_video = False
            video_queue.task_done()
            
        except queue.Empty:
            continue
        except Exception as e:
            print(f"Video error: {e}")


def play_video_sequence(words: list, transcript: str = ""):
    video_queue.put((words, transcript))


video_thread = threading.Thread(target=video_playback_worker, daemon=True)
video_thread.start()


def play_single_video(video_path: str, overlay_word: str = "", max_duration: float = 10.0, speed_multiplier: float = 1.0):
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
    
    frame_delay = (1.0 / fps if fps > 0 else 0.04) / speed_multiplier
    start_time = time.time()
    
    try:
        while not stop_video:
            ret, frame = cap.read()
            if not ret:
                break
            
            show_frame(frame, overlay_word)
            
            if time.time() - start_time >= max_duration:
                break
            
            time.sleep(frame_delay)
    finally:
        cap.release()


# ============ VAD-BASED AUDIO STREAMING ============
class VADAudioStreamer:
    """
    WebRTC VAD-based audio streamer with pre-roll, hangover, and batch sending.
    Only sends speech segments to reduce bandwidth by 70-90%.
    """
    
    # Max speech segment duration to prevent memory overflow
    MAX_SPEECH_SECONDS = 8.0
    
    def __init__(self):
        # Initialize VAD (mode 3 = aggressive)
        if VAD_AVAILABLE:
            self.vad = webrtcvad.Vad(3)
        else:
            self.vad = None
        
        # Pre-roll buffer (keep N frames before speech detected)
        self.preroll_buffer = deque(maxlen=PREROLL_FRAMES)
        
        # Current speech segment buffer
        self.speech_buffer = bytearray()
        
        # State
        self.in_speech = False
        self.hangover_counter = 0
        self.speech_frame_count = 0
        
        # Batch timing
        self.last_send_time = time.time()
        
        # Adaptive noise floor
        self.noise_floor = MIN_RMS_THRESHOLD
        self.noise_samples = deque(maxlen=50)  # ~1 second of samples
        
        # Stats
        self.frames_processed = 0
        self.frames_sent = 0
        self.noise_rejected = 0
    
    def calculate_rms(self, audio_bytes: bytes) -> float:
        """Calculate RMS of audio for noise detection."""
        if len(audio_bytes) < 2:
            return 0.0
        n_samples = len(audio_bytes) // 2
        samples = struct.unpack(f'<{n_samples}h', audio_bytes)
        return (sum(s*s for s in samples) / n_samples) ** 0.5 if samples else 0
    
    def update_noise_floor(self, rms: float, is_speech: bool):
        """Update adaptive noise floor from silence frames."""
        if not is_speech and rms > 50 and rms < 2000:
            self.noise_samples.append(rms)
            if len(self.noise_samples) >= 10:
                # Noise floor = 1.5x median of recent silence
                sorted_samples = sorted(self.noise_samples)
                median = sorted_samples[len(sorted_samples) // 2]
                self.noise_floor = max(MIN_RMS_THRESHOLD * 0.5, min(median * 1.5, MIN_RMS_THRESHOLD * 2))
    
    def process_frame(self, frame_bytes: bytes) -> bytes:
        """
        Process a single 20ms frame through VAD.
        Returns bytes to send when speech segment completes.
        """
        self.frames_processed += 1
        
        # Calculate RMS
        rms = self.calculate_rms(frame_bytes)
        
        # Initial VAD check
        is_speech = False
        if self.vad:
            try:
                is_speech = self.vad.is_speech(frame_bytes, SAMPLE_RATE)
            except:
                is_speech = rms > self.noise_floor
        else:
            is_speech = rms > self.noise_floor
        
        # RMS filter - reject obvious noise
        if rms < self.noise_floor * 0.3 or rms > MAX_RMS_THRESHOLD:
            self.noise_rejected += 1
            is_speech = False
            self.update_noise_floor(rms, False)
            # Still add to preroll for context
            if not self.in_speech:
                self.preroll_buffer.append(frame_bytes)
            return b''
        
        # Update noise floor during silence
        if not is_speech:
            self.update_noise_floor(rms, False)
        
        if is_speech:
            if not self.in_speech:
                # Speech start - include pre-roll
                self.in_speech = True
                self.speech_frame_count = 0
                
                # Add pre-roll frames
                for preroll_frame in self.preroll_buffer:
                    self.speech_buffer.extend(preroll_frame)
                self.preroll_buffer.clear()
            
            # Add current frame
            self.speech_buffer.extend(frame_bytes)
            self.speech_frame_count += 1
            self.hangover_counter = HANGOVER_FRAMES
            
            # Check max duration - force flush if too long
            max_frames = int(self.MAX_SPEECH_SECONDS * 1000 / FRAME_DURATION_MS)
            if self.speech_frame_count >= max_frames:
                return self._flush_speech_buffer()
            
        else:
            # Silence/noise
            if self.in_speech:
                # In hangover period - keep adding
                if self.hangover_counter > 0:
                    self.speech_buffer.extend(frame_bytes)
                    self.hangover_counter -= 1
                else:
                    # Speech ended - flush if long enough
                    return self._flush_speech_buffer()
            else:
                # Add to pre-roll buffer
                self.preroll_buffer.append(frame_bytes)
        
        return b''
    
    def _flush_speech_buffer(self) -> bytes:
        """Flush speech buffer and return data if valid."""
        self.in_speech = False
        
        if self.speech_frame_count >= MIN_SPEECH_FRAMES:
            result = bytes(self.speech_buffer)
            self.frames_sent += self.speech_frame_count
            self.speech_buffer = bytearray()
            self.speech_frame_count = 0
            return result
        
        self.speech_buffer = bytearray()
        self.speech_frame_count = 0
        return b''
    
    def should_send_batch(self, is_video_playing: bool = False) -> bool:
        """Check if it's time to send accumulated data."""
        send_interval = SEND_INTERVAL_VIDEO if is_video_playing else SEND_INTERVAL_NORMAL
        return (time.time() - self.last_send_time) >= send_interval
    
    def mark_batch_sent(self):
        """Mark that a batch was sent."""
        self.last_send_time = time.time()
    
    def flush(self) -> bytes:
        """Flush any remaining speech buffer (called on stop)."""
        if len(self.speech_buffer) > 0 and self.speech_frame_count >= MIN_SPEECH_FRAMES:
            result = bytes(self.speech_buffer)
            self.frames_sent += self.speech_frame_count
            self.speech_buffer = bytearray()
            self.speech_frame_count = 0
            self.in_speech = False
            return result
        
        self.speech_buffer = bytearray()
        self.speech_frame_count = 0
        self.in_speech = False
        return b''
    
    def get_stats(self) -> dict:
        return {
            'processed': self.frames_processed,
            'sent': self.frames_sent,
            'rejected': self.noise_rejected,
            'noise_floor': f"{self.noise_floor:.0f}",
            'reduction': f"{100*(1-self.frames_sent/(self.frames_processed or 1)):.1f}%"
        }


async def stream_audio_to_server(ws):
    """Stream VAD-filtered audio to WebSocket server."""
    global stop_streaming, current_state
    
    streamer = VADAudioStreamer()
    frame_bytes = FRAME_SIZE * 2  # 16-bit samples
    
    print(f"🎤 Starting VAD audio stream (frame={FRAME_DURATION_MS}ms)")
    
    # Start arecord
    process = subprocess.Popen([
        'arecord', '-D', AUDIO_DEVICE,
        '-f', 'S16_LE', '-r', str(SAMPLE_RATE),
        '-c', str(CHANNELS), '-t', 'raw', '-'
    ], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=frame_bytes * 4)
    
    pending_queue = queue.Queue(maxsize=MAX_PENDING_BATCHES)
    
    try:
        while not stop_streaming:
            # Read one frame
            frame = process.stdout.read(frame_bytes)
            if not frame or len(frame) < frame_bytes:
                break
            
            # Process through VAD - returns speech data when segment completes
            speech_data = streamer.process_frame(frame)
            
            # Check if we have data to send
            is_video = (current_state == State.PLAYING)
            
            if speech_data and len(speech_data) > 0:
                # Queue for sending (with limit to prevent overflow)
                if pending_queue.full():
                    try:
                        pending_queue.get_nowait()  # Drop oldest
                    except:
                        pass
                pending_queue.put(speech_data)
                streamer.mark_batch_sent()
            
            # Send from queue when interval reached
            if streamer.should_send_batch(is_video):
                try:
                    while not pending_queue.empty():
                        data = pending_queue.get_nowait()
                        await ws.send(data)
                except:
                    pass
            
            await asyncio.sleep(0.001)
    
    finally:
        process.terminate()
        process.wait()
        
        # Send flush command
        try:
            await ws.send(json.dumps({'type': 'flush'}))
        except:
            pass
        
        stats = streamer.get_stats()
        print(f"🎤 Stream ended: {stats}")


async def receive_results(ws):
    """Receive results from server."""
    global current_state, stop_streaming
    
    try:
        async for message in ws:
            data = json.loads(message)
            msg_type = data.get('type', '')
            
            if msg_type == 'connected':
                print(f"✅ Connected: {data.get('message', '')}")
                show_message(["Đã kết nối!", "", "Đang nghe..."], (100, 255, 100))
            
            elif msg_type == 'buffering':
                pass  # Throttled on server, ignore
            
            elif msg_type == 'filtered':
                pass  # Silently ignore filtered
            
            elif msg_type == 'result':
                transcript = data.get('transcript', '')
                words = data.get('words', [])
                print(f"📝 Result: {transcript}")
                if words:
                    play_video_sequence(words, transcript)
            
            elif msg_type == 'error':
                print(f"❌ Error: {data.get('error', '')}")
            
            elif msg_type == 'pong':
                pass
    
    except Exception as e:
        print(f"Receive error: {e}")


async def send_heartbeat(ws):
    """Periodic heartbeat."""
    try:
        while not stop_streaming:
            await asyncio.sleep(15)
            if websocket_connected:
                await ws.send(json.dumps({'type': 'ping'}))
    except:
        pass


async def websocket_session():
    """Main WebSocket session."""
    global current_state, stop_streaming, websocket_connected, reconnect_count
    
    ws_url = f"{API_URL}{WS_ENDPOINT}"
    print(f"🔌 Connecting: {ws_url}")
    
    try:
        async with websockets.connect(ws_url, ping_interval=30, ping_timeout=60) as ws:
            websocket_connected = True
            current_state = State.RECORDING
            reconnect_count = 0
            
            show_message(["🔴 GHI ÂM", "", "Nói vào micro...", "Nhấn nút để dừng"], (255, 100, 100), (50, 0, 0))
            
            await asyncio.gather(
                stream_audio_to_server(ws),
                receive_results(ws),
                send_heartbeat(ws)
            )
    
    except websockets.exceptions.ConnectionClosed:
        print("🔌 Connection closed")
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


# ============ BUTTON HANDLER ============
def handle_button():
    global current_state, is_recording, stop_streaming, stop_video, ws_thread
    
    print(f"🔘 Button! State: {current_state}")
    
    if current_state == State.PLAYING:
        stop_video = True
        return
    
    if not is_recording:
        # Start recording
        is_recording = True
        stop_streaming = False
        current_state = State.CONNECTING
        
        show_message(["🔴 GHI ÂM", "", "Đang kết nối...", "Nhấn nút để dừng"], (255, 100, 100), (50, 0, 0))
        
        ws_thread = threading.Thread(target=start_websocket_thread, daemon=True)
        ws_thread.start()
    
    else:
        # Stop recording
        is_recording = False
        stop_streaming = True
        current_state = State.IDLE
        show_message(["Đã dừng", "", "Nhấn nút để", "ghi lại"], (100, 255, 100))


# ============ MAIN ============
def main():
    global current_state
    
    print("=" * 50)
    print("🎤 REAL-TIME VSL - Raspberry Pi (OPTIMIZED)")
    print("=" * 50)
    print(f"📡 Server: {API_URL}")
    print(f"📹 Videos: {len(video_mapper.video_cache)}")
    print(f"🎙️ VAD: {'ENABLED' if VAD_AVAILABLE else 'DISABLED (RMS only)'}")
    print(f"🔧 Frame: {FRAME_DURATION_MS}ms, Pre-roll: {PREROLL_FRAMES*FRAME_DURATION_MS}ms, Hangover: {HANGOVER_FRAMES*FRAME_DURATION_MS}ms")
    print("=" * 50)
    
    init_lcd()
    print("✅ LCD OK!")
    
    show_message(["Real-Time VSL", "(Optimized)", "", "Nhấn nút để", "bắt đầu"], (100, 255, 100))
    
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
