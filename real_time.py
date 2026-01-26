
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
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont

# ============ LOAD .ENV ============
load_dotenv()
_api_url = os.getenv("API_URL", "ws://172.20.10.3:8000")

# Auto-convert http:// to ws:// and https:// to wss://
if _api_url.startswith("http://"):
    API_URL = _api_url.replace("http://", "ws://", 1)
elif _api_url.startswith("https://"):
    API_URL = _api_url.replace("https://", "wss://", 1)
else:
    API_URL = _api_url

WS_ENDPOINT = "/api/realtime/ws/vsl"

# ============ CONNECTION SETTINGS ============
RECONNECT_DELAY = 3  # Seconds between reconnect attempts
MAX_RECONNECT_ATTEMPTS = 5
SILENCE_THRESHOLD = 500  # RMS threshold for silence detection
SILENCE_DURATION = 1.5  # Seconds of silence before flushing

# ============ DISPLAY SETTINGS ============
MIRROR_MODE = True  # Set True for VR glasses (flip horizontal)
SKIP_FRAMES = 1  # Skip every N frames for faster playback (1 = no skip)

# Video playback speed control
# 1.0 = Normal speed (play full video)
# 0.5 = Slower (2x longer, easier to see)
# 2.0 = Faster (2x shorter, quicker but harder to see)
# Recommended: 0.8-1.5 for best experience
VIDEO_SPEED = 1.0  # General video playback speed
FINGERSPELL_SPEED = 1.5



# ============ GPIO PINS ============
BUTTON_PIN = 17  # Pin 11
DC_PIN = 24
RST_PIN = 25
BL_PIN = 18

# ============ PATHS ============
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
VIDEO_DIR = os.path.join(SCRIPT_DIR, "video")
FONT_PATH = os.path.join(SCRIPT_DIR, "SVN-Arial Regular.ttf")

# ============ AUDIO SETTINGS ============
SAMPLE_RATE = 16000  # Whisper expects 16kHz
CHANNELS = 1
CHUNK_SIZE = 8000  # 0.5 seconds of audio at 16kHz

# Client-side filtering (reduce bandwidth, save server resources)
ENABLE_CLIENT_FILTER = True  # Set False to disable client-side filtering
CLIENT_MIN_RMS = 200  # Lower than server threshold (send borderline audio to server)


def calculate_chunk_rms(audio_bytes: bytes) -> float:
    """
    Calculate RMS (Root Mean Square) of audio chunk for noise detection.
    Quick check before sending to server to reduce bandwidth.
    """
    import struct
    
    if len(audio_bytes) < 2:
        return 0.0
    
    # Unpack 16-bit signed integers
    num_samples = len(audio_bytes) // 2
    samples = struct.unpack(f'<{num_samples}h', audio_bytes)
    
    # Calculate RMS
    sum_squares = sum(s * s for s in samples)
    rms = (sum_squares / num_samples) ** 0.5 if num_samples > 0 else 0
    
    return rms


# ============ STATE ============
class State:
    IDLE = 0
    CONNECTING = 1
    RECORDING = 2  # Actively recording and sending audio
    PROCESSING = 3
    PLAYING = 4

current_state = State.IDLE
is_recording = False  # Toggle for recording mode
stop_streaming = False
stop_video = False
websocket_connected = False
reconnect_count = 0
last_audio_time = 0  # For silence detection
ws_thread = None  # WebSocket thread reference


# ============ AUDIO DEVICE ============
def get_usb_audio_device():
    """Auto-detect USB audio device."""
    try:
        result = subprocess.run(['arecord', '-l'], capture_output=True, text=True)
        lines = result.stdout.split('\n')
        
        for line in lines:
            if 'card' in line.lower() and ('usb' in line.lower() or 'pnp' in line.lower()):
                match = re.search(r'card (\d+):', line)
                if match:
                    card_num = match.group(1)
                    device = f"plughw:{card_num},0"
                    print(f"🎤 Found USB Audio: {line.strip()}")
                    print(f"   → Using: {device}")
                    return device
        
        print("⚠️ USB Audio not found, using default: plughw:0,0")
        return "plughw:0,0"
    except Exception as e:
        print(f"⚠️ Error finding audio device: {e}")
        return "plughw:0,0"


AUDIO_DEVICE = get_usb_audio_device()


# ============ FONT ============
try:
    FONT_VN = ImageFont.truetype(FONT_PATH, 22)  # Bigger font
    FONT_SMALL = ImageFont.truetype(FONT_PATH, 16)
    FONT_LARGE = ImageFont.truetype(FONT_PATH, 28)  # For titles
except:
    FONT_VN = ImageFont.load_default()
    FONT_SMALL = ImageFont.load_default()
    FONT_LARGE = ImageFont.load_default()
    print("⚠️ Font not found, using default")


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
    """Send bulk data to LCD - ULTRA OPTIMIZED with writebytes2."""
    GPIO.output(DC_PIN, GPIO.HIGH)
    # writebytes2 is faster than xfer2 for large data (no return buffer)
    # Use larger chunks for fewer calls
    CHUNK_SIZE = 32768  # 32KB chunks (was 4KB)
    if isinstance(d, bytes):
        for i in range(0, len(d), CHUNK_SIZE):
            spi.writebytes2(d[i:i+CHUNK_SIZE])
    else:
        # Convert to bytes first if it's a list
        d_bytes = bytes(d)
        for i in range(0, len(d_bytes), CHUNK_SIZE):
            spi.writebytes2(d_bytes[i:i+CHUNK_SIZE])


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


# Pre-allocate display buffer for performance
_display_buffer = np.empty((240, 240, 2), dtype=np.uint8)
_rgb565_buffer = np.empty((240, 240), dtype=np.uint16)


def show_frame(frame, overlay_text=None):
    """Display a frame on LCD - supports Vietnamese font and mirror mode."""
    global _display_buffer, _rgb565_buffer
    
    # Resize with fastest interpolation
    frame = cv2.resize(frame, (240, 240), interpolation=cv2.INTER_NEAREST)
    
    # Add text overlay BEFORE mirroring (so text is mirrored too)
    if overlay_text:
        # Convert to PIL for Vietnamese font support
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(frame_rgb)
        draw = ImageDraw.Draw(pil_img)
        
        # Black bar at bottom
        draw.rectangle([(0, 200), (240, 240)], fill=(0, 0, 0))
        
        # White text, centered
        text = overlay_text[:30]
        try:
            bbox = draw.textbbox((0, 0), text, font=FONT_VN)
            text_width = bbox[2] - bbox[0]
        except:
            text_width = len(text) * 10
        x = max(5, (240 - text_width) // 2)
        draw.text((x, 210), text, font=FONT_VN, fill=(255, 255, 255))
        
        frame = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    
    # Mirror for VR glasses AFTER adding text (so text is mirrored too)
    if MIRROR_MODE:
        frame = cv2.flip(frame, 1)
    
    # OPTIMIZED RGB565 conversion
    np.add(
        np.add(
            np.left_shift(frame[:, :, 2].astype(np.uint16) >> 3, 11),
            np.left_shift(frame[:, :, 1].astype(np.uint16) >> 2, 5)
        ),
        frame[:, :, 0].astype(np.uint16) >> 3,
        out=_rgb565_buffer
    )
    
    # Split into high/low bytes
    _display_buffer[:, :, 0] = (_rgb565_buffer >> 8).astype(np.uint8)
    _display_buffer[:, :, 1] = (_rgb565_buffer & 0xFF).astype(np.uint8)
    
    # Send to LCD
    cmd(0x2A); data([0, 0, 0, 239])
    cmd(0x2B); data([0, 0, 0, 239])
    cmd(0x2C)
    data_bulk(_display_buffer.tobytes())


def show_message(lines, color=(255, 255, 255), bg_color=(0, 0, 0)):
    """Display text message on LCD with white/bright colors."""
    pil_img = Image.new('RGB', (240, 240), bg_color)
    draw = ImageDraw.Draw(pil_img)
    
    if isinstance(lines, str):
        lines = lines.split('\n')
    
    total_height = len(lines) * 35  # Increased line height
    start_y = (240 - total_height) // 2
    
    for i, line in enumerate(lines):
        # Get text width for centering
        bbox = draw.textbbox((0, 0), line, font=FONT_VN)
        text_width = bbox[2] - bbox[0]
        x = max(5, (240 - text_width) // 2)
        y = start_y + i * 35
        draw.text((x, y), line, font=FONT_VN, fill=color)
    
    frame = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    show_frame(frame)
    
    # Free memory
    del pil_img, draw, frame


# ============ VIDEO MAPPER ============
class VideoMapper:
    """Map words to local video files."""
    
    # Windows reserved names
    RESERVED_NAMES = {'con', 'prn', 'aux', 'nul', 'com1', 'com2', 'lpt1'}
    
    # Vietnamese tone marks → base letter
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
        print(f"📹 VideoMapper: {len(self.video_cache)} videos loaded")
    
    def _scan_videos(self):
        """Scan and cache all video files."""
        if not self.video_dir.exists():
            print(f"⚠️ Video dir not found: {self.video_dir}")
            return
        
        for f in self.video_dir.glob("*.mp4"):
            key = f.stem.lower()
            self.video_cache[key] = f
        
        for f in self.video_dir.glob("*.webm"):
            key = f.stem.lower()
            if key not in self.video_cache:
                self.video_cache[key] = f
    
    def normalize_for_pronunciation(self, text: str) -> str:
        """Remove tone marks for fuzzy matching."""
        result = []
        for char in text.lower():
            result.append(self.TONE_MAP.get(char, char))
        return ''.join(result)
    
    def normalize_word(self, word: str) -> str:
        """
        Normalize word for matching: lowercase, remove punctuation.
        
        Examples:
            "Tôi" -> "tôi"
            "học!" -> "học"
            "Xin chào," -> "xin chào"
        """
        import string
        # Remove punctuation
        word = word.translate(str.maketrans('', '', string.punctuation))
        # Lowercase
        word = word.lower().strip()
        return word
    
    def find_video(self, word: str) -> Path:

        if not word:
            return None
        
        # Normalize: lowercase + remove punctuation
        key = self.normalize_word(word)
        
        if not key:  # Empty after normalization
            return None
        
        # Strategy 1: Exact match
        if key in self.video_cache:
            video_path = self.video_cache[key]
            # Verify file still exists
            if video_path.exists():
                return video_path
            else:
                print(f"      ⚠️ Video file missing: {video_path}")
                return None
        
        # Strategy 2: Windows reserved names (con → con_)
        if key in self.RESERVED_NAMES:
            key_reserved = key + '_'
            if key_reserved in self.video_cache:
                video_path = self.video_cache[key_reserved]
                if video_path.exists():
                    return video_path
        
        # Strategy 3: Underscore format
        key_underscore = key.replace(' ', '_')
        if key_underscore in self.video_cache:
            video_path = self.video_cache[key_underscore]
            if video_path.exists():
                return video_path
        
        # Strategy 4: Remove tone marks
        key_no_tone = self.normalize_for_pronunciation(key)
        if key_no_tone in self.video_cache:
            video_path = self.video_cache[key_no_tone]
            if video_path.exists():
                return video_path
        
        return None
    
    def get_fingerspell_videos(self, word: str) -> list:
        """
        Get list of videos for fingerspelling a word.
        Returns empty list if cannot fingerspell (missing letter videos).
        """
        result = []
        missing_chars = []
        
        for char in word.lower():
            if char.isalpha():
                normalized = self.TONE_MAP.get(char, char)
                video = self.find_video(normalized)
                if video:
                    result.append((normalized, video))
                else:
                    missing_chars.append(char)
            elif char.isdigit():
                video = self.find_video(char)
                if video:
                    result.append((char, video))
                else:
                    missing_chars.append(char)
            # Skip spaces and special characters
        
        # If any character is missing, cannot fingerspell properly
        if missing_chars:
            print(f"      Cannot fingerspell '{word}': missing videos for {missing_chars}")
            return []
        
        return result


# Initialize video mapper
video_mapper = VideoMapper(VIDEO_DIR)


# ============ VIDEO PLAYBACK (THREADED) ============
# Queue for video playback tasks
import queue
video_queue = queue.Queue()
video_thread_running = True


def video_playback_worker():
    """Worker thread that plays videos from queue - doesn't block WebSocket."""
    global video_thread_running, current_state, stop_video
    
    while video_thread_running:
        try:
            # Wait for video task with timeout (to check running flag)
            task = video_queue.get(timeout=0.5)
            if task is None:
                continue
            
            words, transcript = task
            current_state = State.PLAYING
            stop_video = False
            
            print(f"Playing sequence: {words}")
            
            played_count = 0
            skipped_count = 0
            skipped_words = []
            
            for word in words:
                if stop_video:
                    break
                
                video_path = video_mapper.find_video(word)
                
                if video_path:
                    # Found direct video - play with VIDEO_SPEED
                    print(f"   ✓ {word} -> {video_path.name}")
                    play_single_video(str(video_path), transcript, speed_multiplier=VIDEO_SPEED)
                    played_count += 1
                else:
                    # Try fingerspelling fallback
                    letters = video_mapper.get_fingerspell_videos(word)
                    
                    if letters and len(letters) > 0:
                        # Can fingerspell - use FINGERSPELL_SPEED
                        print(f"   🔤 Fingerspelling: {word} ({len(letters)} letters) at {FINGERSPELL_SPEED}x speed")
                        for letter, letter_video in letters:
                            if stop_video:
                                break
                            # Play with fingerspell speed multiplier
                            play_single_video(str(letter_video), transcript, speed_multiplier=FINGERSPELL_SPEED)
                        played_count += 1
                    else:
                        # Cannot find video AND cannot fingerspell - SKIP silently
                        print(f"   ⚠️ SKIP: '{word}' (no video, cannot fingerspell)")
                        skipped_count += 1
                        skipped_words.append(word)
                        continue
            
            # Summary (console only, no LCD notification)
            print(f"   [Summary: {played_count} played, {skipped_count} skipped]")
            if skipped_words:
                print(f"   [Skipped words: {', '.join(skipped_words)}]")
            
            # NO LCD notification for skipped words - just continue
            
            current_state = State.RECORDING
            stop_video = False
            video_queue.task_done()
            
        except queue.Empty:
            continue
        except Exception as e:
            print(f"Video worker error: {e}")


def play_video_sequence(words: list, transcript: str = ""):
    """Queue video sequence for playback in background thread."""
    video_queue.put((words, transcript))


# Start video worker thread
video_thread = threading.Thread(target=video_playback_worker, daemon=True)
video_thread.start()
print("Video worker thread started")


def play_single_video(video_path: str, overlay_word: str = "", max_duration: float = 10.0, speed_multiplier: float = 1.0):
    """
    Play a single video file on LCD - FULL PLAYBACK with timeout protection.
    
    Args:
        video_path: Path to video file
        overlay_word: Text to display at bottom
        max_duration: Absolute max duration to prevent hanging (default 10s)
        speed_multiplier: Speed multiplier (1.0 = normal, 0.5 = slower, 2.0 = faster)
    """
    global stop_video
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"   ❌ Cannot open: {video_path}")
        return

    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    
    # Get video info
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    video_duration = total_frames / fps if fps > 0 else 0
    
    # Safety check: skip if video is too long or corrupted
    if video_duration > max_duration or video_duration <= 0:
        print(f"   ⚠️ SKIP: Video too long ({video_duration:.1f}s) or corrupted")
        cap.release()
        return
    
    print(f"   [Video: {total_frames} frames, {fps:.1f}fps, {video_duration:.2f}s, speed={speed_multiplier}x]")
    
    # Adjust playback speed with multiplier
    frame_delay = (1.0 / fps if fps > 0 else 0.04) / speed_multiplier
    
    frame_count = 0
    gc_interval = 20
    start_time = time.time()
    
    try:
        while not stop_video:
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_count += 1
            
            # Display every frame
            show_frame(frame, overlay_word)
            del frame

            # Periodic GC
            if frame_count % gc_interval == 0:
                import gc
                gc.collect()

            # Absolute timeout protection only
            elapsed = time.time() - start_time
            if elapsed >= max_duration:
                print(f"   ⚠️ Timeout reached ({max_duration}s), stopping video")
                break
            
            time.sleep(frame_delay)
        
        print(f"   [Played: {frame_count}/{total_frames} frames in {time.time() - start_time:.2f}s]")
            
    except Exception as e:
        print(f"   ❌ Video playback error: {e}")
    finally:
        cap.release()
        import gc
        gc.collect()


# ============ WEBSOCKET CLIENT ============
async def stream_audio_to_server(ws):
    """Stream audio chunks to WebSocket server with optional client-side filtering."""
    global stop_streaming
    
    print("🎤 Starting audio stream...")
    if ENABLE_CLIENT_FILTER:
        print(f"   Client-side filter: RMS >= {CLIENT_MIN_RMS}")
    
    # Stats for monitoring
    chunks_sent = 0
    chunks_filtered = 0
    
    # Start arecord process with smaller buffer
    process = subprocess.Popen([
        'arecord', '-D', AUDIO_DEVICE,
        '-f', 'S16_LE', '-r', str(SAMPLE_RATE),
        '-c', str(CHANNELS), '-t', 'raw', '-'
    ], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=CHUNK_SIZE * 2)
    
    try:
        while not stop_streaming:
            # Read audio chunk
            audio_data = process.stdout.read(CHUNK_SIZE * 2)  # 16-bit = 2 bytes
            
            if not audio_data:
                break
            
            # === CLIENT-SIDE FILTERING ===
            if ENABLE_CLIENT_FILTER:
                rms = calculate_chunk_rms(audio_data)
                
                if rms < CLIENT_MIN_RMS:
                    # Skip this chunk (silence/noise)
                    chunks_filtered += 1
                    del audio_data
                    await asyncio.sleep(0.005)
                    continue
            
            # Send to server
            await ws.send(audio_data)
            chunks_sent += 1
            
            # Delete audio data immediately after sending to free memory
            del audio_data
            
            await asyncio.sleep(0.005)  # Minimal delay
    finally:
        process.terminate()
        process.wait()
        print(f"🎤 Audio stream stopped: {chunks_sent} sent, {chunks_filtered} filtered")


async def receive_results(ws):
    """Receive and process results from server."""
    global current_state, stop_streaming
    
    # Stats for monitoring
    results_received = 0
    filtered_count = 0
    
    try:
        async for message in ws:
            data = json.loads(message)
            msg_type = data.get('type', '')
            
            if msg_type == 'connected':
                print(f"Connected: {data.get('message')}")
                show_message(["Da ket noi!", "", "Dang lang nghe..."], (100, 255, 100))
            
            elif msg_type == 'buffering':
                progress = data.get('progress', 0)
                # Only log every 25% to reduce spam
                if int(progress * 4) != int((progress - 0.25) * 4):
                    print(f"   Buffering: {progress*100:.0f}%")
            
            elif msg_type == 'filtered':
                # Audio/transcription was filtered (noise/garbage)
                filtered_count += 1
                reason = data.get('reason', 'unknown')
                # Only log occasionally to avoid spam
                if filtered_count % 10 == 1:
                    print(f"   🔇 Filtered ({filtered_count}x): {reason}")
            
            elif msg_type == 'result':
                results_received += 1
                transcript = data.get('transcript', '')
                vsl_text = data.get('vsl_text', '')
                words = data.get('words', [])
                confidence = data.get('confidence', 0)
                
                print(f"✅ Result #{results_received}:")
                print(f"   Transcript: {transcript}")
                print(f"   VSL Text: {vsl_text}")
                print(f"   Confidence: {confidence:.2f}")
                
                if words:
                    play_video_sequence(words, transcript)
            
            elif msg_type == 'error':
                print(f"Error: {data.get('error')}")
                show_message(["Loi!", data.get('error', '')[:20]], (255, 100, 100))
            
            elif msg_type == 'pong':
                # Heartbeat response, ignore
                pass
            
            # Free message memory after processing
            del data, message
    
    except Exception as e:
        print(f"Receive error: {e}")
    finally:
        print(f"📊 Session stats: {results_received} results, {filtered_count} filtered")


async def websocket_session():
    """Main WebSocket session with auto-reconnect."""
    global current_state, stop_streaming, websocket_connected, reconnect_count, is_recording
    
    ws_url = f"{API_URL}{WS_ENDPOINT}"
    print(f"🔌 Connecting to: {ws_url}")
    
    try:
        async with websockets.connect(
            ws_url,
            ping_interval=30,   # Send ping every 30s
            ping_timeout=60,    # Wait 60s for pong (allow long video playback)
            close_timeout=10
        ) as ws:
            websocket_connected = True
            current_state = State.RECORDING
            reconnect_count = 0  # Reset on successful connection
            
            # Show recording status on LCD
            show_message([
                "🔴 ĐANG GHI ÂM",
                "",
                "Nói vào micro...",
                "Nhấn nút để dừng"
            ], (255, 100, 100), (50, 0, 0))
            
            # Run sender and receiver concurrently
            sender = asyncio.create_task(stream_audio_to_server(ws))
            receiver = asyncio.create_task(receive_results(ws))
            heartbeat = asyncio.create_task(send_heartbeat(ws))
            
            # Wait until stop_streaming is set or connection closes
            # Use ALL_COMPLETED so session stays alive while any task runs
            try:
                await asyncio.gather(sender, receiver, heartbeat)
            except Exception as e:
                print(f"Task error: {e}")
    
    except websockets.exceptions.ConnectionClosed:
        print("🔌 Connection closed")
    except Exception as e:
        print(f"❌ Connection error: {e}")
        show_message(["Lỗi kết nối!", str(e)[:20]], (255, 100, 100))
    finally:
        websocket_connected = False
        current_state = State.IDLE


async def send_heartbeat(ws):
    """Send periodic heartbeat to keep connection alive."""
    try:
        while not stop_streaming:
            await asyncio.sleep(15)
            if websocket_connected:
                await ws.send(json.dumps({'type': 'ping'}))
    except:
        pass


async def websocket_session_with_reconnect():
    """Wrapper with auto-reconnect logic."""
    global reconnect_count, stop_streaming
    
    while not stop_streaming and reconnect_count < MAX_RECONNECT_ATTEMPTS:
        await websocket_session()
        
        if stop_streaming:
            break
        
        reconnect_count += 1
        if reconnect_count < MAX_RECONNECT_ATTEMPTS:
            print(f"🔄 Reconnecting in {RECONNECT_DELAY}s... (attempt {reconnect_count}/{MAX_RECONNECT_ATTEMPTS})")
            show_message(["Mất kết nối", f"Thử lại {reconnect_count}/{MAX_RECONNECT_ATTEMPTS}"], (255, 200, 100))
            await asyncio.sleep(RECONNECT_DELAY)
        else:
            print("❌ Max reconnect attempts reached")
            show_message(["Không thể kết nối", "Nhấn nút để thử lại"], (255, 100, 100))


def start_websocket_thread():
    """Start WebSocket session in a separate thread."""
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
    """Handle button press - Toggle recording on/off."""
    global current_state, is_recording, stop_streaming, stop_video, ws_thread
    
    print(f"🔘 Button pressed! State: {current_state}, Recording: {is_recording}")
    
    if current_state == State.PLAYING:
        # Stop video playback first
        print("⏹ Stopping video...")
        stop_video = True
        return
    
    if not is_recording:
        # ===== START RECORDING =====
        print("🔴 Starting recording...")
        is_recording = True
        stop_streaming = False
        current_state = State.CONNECTING
        
        show_message([
            "🔴 GHI ÂM",
            "",
            "Đang kết nối...",
            "Nhấn nút để dừng"
        ], (255, 100, 100), (50, 0, 0))
        
        # Start WebSocket in background thread
        ws_thread = threading.Thread(target=start_websocket_thread)
        ws_thread.daemon = True
        ws_thread.start()
    
    else:
        # ===== STOP RECORDING =====
        print("⏹ Stopping recording...")
        is_recording = False
        stop_streaming = True
        
        # Send flush command to process remaining audio
        # (handled in websocket session)
        
        current_state = State.IDLE
        show_message([
            "Đã dừng ghi âm",
            "",
            "Nhấn nút để",
            "ghi lại"
        ], (100, 255, 100))


# ============ MAIN ============
def main():
    global current_state
    
    print("=" * 50)
    print("🎤 REAL-TIME VSL - Raspberry Pi")
    print("=" * 50)
    print(f"📡 Server: {API_URL}")
    print(f"📹 Videos: {len(video_mapper.video_cache)}")
    print(f"🔘 Button: GPIO {BUTTON_PIN}")
    print("=" * 50)
    
    print("Initializing LCD...")
    init_lcd()
    print("✅ LCD OK!")
    
    show_message([
        "Real-Time VSL",
        "",
        "Nhấn nút để",
        "bắt đầu"
    ], (100, 255, 100))
    
    last_state = GPIO.HIGH
    
    print("\n✅ Ready! Press button to start...")
    print("   Press Ctrl+C to exit\n")
    
    try:
        while True:
            current_btn = GPIO.input(BUTTON_PIN)
            
            if last_state == GPIO.HIGH and current_btn == GPIO.LOW:
                handle_button()
                time.sleep(0.3)  # Debounce
            
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
