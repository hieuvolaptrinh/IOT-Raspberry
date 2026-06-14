#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import dbus
import dbus.exceptions
import dbus.mainloop.glib
import dbus.service
import gc
import json
import os
import subprocess
import sys
import threading
import time
import cv2
import numpy as np
import spidev
import RPi.GPIO as GPIO
from collections import deque
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from dataclasses import dataclass
from typing import List

from gi.repository import GLib

# Import constants from constraint.py
from constraint import *

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
_resize_buffer = np.empty((240, 240, 3), dtype=np.uint8)
_overlay_cache = {}  # Cache overlay text → np.ndarray, tránh tạo lại mỗi frame
_OVERLAY_CACHE_MAX = 20  # Giới hạn số overlay cache

def _create_text_overlay(text: str) -> np.ndarray:
    # Cache overlay để tránh tạo PIL Image mỗi frame
    text = text.lower()  # Chữ thường
    if text in _overlay_cache:
        return _overlay_cache[text]

    overlay_h = 60  # Cao hơn để chứa 2-3 dòng
    pil_img = Image.new('RGB', (240, overlay_h), (0, 0, 0))
    draw = ImageDraw.Draw(pil_img)
    font = FONT_SMALL  # Font nhỏ hơn để không bị tràn

    # Word-wrap: tách text thành nhiều dòng nếu quá dài
    max_width = 230  # Trừ padding 2 bên
    words = text.split()
    lines = []
    current_line = ""
    for word in words:
        test_line = f"{current_line} {word}".strip() if current_line else word
        try:
            bbox = draw.textbbox((0, 0), test_line, font=font)
            w = bbox[2] - bbox[0]
        except:
            w = len(test_line) * 8
        if w <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)
    
    # Giới hạn tối đa 3 dòng
    lines = lines[:3]

    # Vẽ các dòng căn giữa
    line_height = 18
    total_h = len(lines) * line_height
    start_y = (overlay_h - total_h) // 2
    for i, line in enumerate(lines):
        try:
            bbox = draw.textbbox((0, 0), line, font=font)
            tw = bbox[2] - bbox[0]
        except:
            tw = len(line) * 8
        x = max(5, (240 - tw) // 2)
        y = start_y + i * line_height
        draw.text((x, y), line, font=font, fill=(255, 255, 255))

    result = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

    # Xóa cache cũ nếu quá nhiều
    if len(_overlay_cache) >= _OVERLAY_CACHE_MAX:
        _overlay_cache.clear()
    _overlay_cache[text] = result
    return result

def show_frame(frame, overlay_text=None):
    global _display_buffer, _rgb565_buffer, _resize_buffer

    cv2.resize(frame, (240, 240), dst=_resize_buffer, interpolation=cv2.INTER_NEAREST)
    frame = _resize_buffer

    if overlay_text:
        overlay = _create_text_overlay(overlay_text)
        frame[180:240, :] = overlay  # 60px cao hơn, bắt đầu từ dòng 180

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
        if not word: return None
        key = self.normalize_word(word)
        if not key: return None

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
                if video: result.append((norm, video))
                else: return []
            elif char.isdigit():
                video = self.find_video(char)
                if video: result.append((char, video))
                else: return []
        return result

video_mapper = VideoMapper(VIDEO_DIR)

# ============ VIDEO JOB & QUEUE ============
@dataclass
class VideoJob:
    words: List[str]
    transcript: str

pending_video_queue = deque(maxlen=5)
video_queue_lock = threading.Condition()
video_thread_running = True
stop_video = False
_shell_cwd = '/home/pi/IOT-Raspberry'  # CWD hiện tại cho shell
_shell_output_char = None  # Tham chiếu ShellOutputCharacteristic
_ble_connected = False  # Trạng thái kết nối BLE

def enqueue_video_job(job: VideoJob):
    with video_queue_lock:
        pending_video_queue.append(job)
        video_queue_lock.notify()
        print(f"📥 Đã đưa vào hàng chờ: {job.words} | Số hàng chờ: {len(pending_video_queue)}")

def play_single_video(video_path: str, overlay_word: str = "", max_duration: float = 10.0, speed_multiplier: float = 1.0):
    global stop_video
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened(): return

    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps if fps > 0 else 0

    if duration > max_duration or duration <= 0:
        cap.release()
        return

    effective_fps = fps * speed_multiplier  
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
            if not ret: break
            
            frame_count += 1
            if frame_count % frame_skip == 0:
                show_frame(frame, overlay_word)
                elapsed = time.time() - last_display_time
                if elapsed < display_interval:
                    time.sleep(display_interval - elapsed)
                last_display_time = time.time()
            
            if time.time() - start_time >= max_duration:
                break
    finally:
        cap.release()

def video_playback_worker():
    global video_thread_running, stop_video
    
    while video_thread_running:
        job = None
        with video_queue_lock:
            while len(pending_video_queue) == 0 and video_thread_running:
                video_queue_lock.wait(timeout=0.5)
            if not video_thread_running: break
            if len(pending_video_queue) > 0:
                job = pending_video_queue.popleft()
        
        if job is None: continue
        
        try:
            stop_video = False
            print(f"🎬 Đang phát: {job.words}")
            
            for word in job.words:
                if stop_video: break
                video_path = video_mapper.find_video(word)
                if video_path:
                    play_single_video(str(video_path), overlay_word=job.transcript, speed_multiplier=VIDEO_SPEED)
                else:
                    letters = video_mapper.get_fingerspell_videos(word)
                    if letters:
                        for letter, letter_video in letters:
                            if stop_video: break
                            play_single_video(str(letter_video), overlay_word=job.transcript, speed_multiplier=FINGERSPELL_SPEED)
            
            # Giữ nguyên frame cuối cùng, không hiển thị thông báo chờ
        except Exception as e:
            print(f"❌ Lỗi phát video: {e}")
        finally:
            # Dọn bộ nhớ sau mỗi job, tránh phân mảnh RAM chạy lâu
            gc.collect()

# ============ BLE HELPER FUNCTIONS ============
def get_device_ips():
    ips = {}
    try:
        result = subprocess.run(['hostname', '-I'], capture_output=True, text=True, timeout=5)
        all_ips = result.stdout.strip().split()
        for ip in all_ips:
            if ip.startswith('100.'):
                ips['tailscale'] = ip
            elif ip.startswith('192.168.') or ip.startswith('10.') or ip.startswith('172.'):
                ips['wifi'] = ip
    except: pass
    try:
        result = subprocess.run(['hostname'], capture_output=True, text=True, timeout=5)
        ips['hostname'] = result.stdout.strip()
    except: pass
    return ips

def connect_wifi(ssid, password):
    print(f"📶 Đang kết nối WiFi: {ssid}...")
    try:
        result = subprocess.run(
            ['sudo', 'nmcli', 'dev', 'wifi', 'connect', ssid, 'password', password],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            print(f"✅ Kết nối WiFi '{ssid}' thành công!")
        else:
            print(f"❌ Kết nối WiFi thất bại: {result.stderr.strip()}")
    except Exception as e:
        print(f"❌ Lỗi kết nối WiFi: {e}")

def update_env_file(api_url):
    print(f"📝 Đang cập nhật .env: API_URL={api_url}")
    try:
        env_lines = []
        found = False
        if os.path.exists(ENV_FILE_PATH):
            with open(ENV_FILE_PATH, 'r') as f:
                for line in f:
                    if line.strip().startswith('API_URL='):
                        env_lines.append(f'API_URL={api_url}\n')
                        found = True
                    else:
                        env_lines.append(line)
        if not found:
            env_lines.append(f'API_URL={api_url}\n')
        with open(ENV_FILE_PATH, 'w') as f:
            f.writelines(env_lines)
        print(f"✅ Đã cập nhật .env thành công!")
    except Exception as e:
        print(f"❌ Lỗi cập nhật .env: {e}")

def find_adapter(bus):
    remote_om = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, '/'), DBUS_OM_IFACE)
    objects = remote_om.GetManagedObjects()
    for path, interfaces in objects.items():
        if GATT_MANAGER_IFACE in interfaces:
            return path
    return None

# ============ BLE CLASSES ============
class Advertisement(dbus.service.Object):
    PATH_BASE = '/org/bluez/example/advertisement'
    def __init__(self, bus, index):
        self.path = self.PATH_BASE + str(index)
        self.bus = bus
        self.ad_type = 'peripheral'
        self.local_name = 'Pi-Setup'
        self.service_uuids = [WIFI_SERVICE_UUID]
        self.include_tx_power = True
        dbus.service.Object.__init__(self, bus, self.path)
    def get_properties(self):
        return {
            LE_ADVERTISEMENT_IFACE: {
                'Type': self.ad_type,
                'LocalName': dbus.String(self.local_name),
                'ServiceUUIDs': dbus.Array(self.service_uuids, signature='s'),
                'IncludeTxPower': dbus.Boolean(self.include_tx_power),
            }
        }
    def get_path(self): return dbus.ObjectPath(self.path)
    @dbus.service.method(DBUS_PROP_IFACE, in_signature='s', out_signature='a{sv}')
    def GetAll(self, interface): return self.get_properties()[LE_ADVERTISEMENT_IFACE]
    @dbus.service.method(LE_ADVERTISEMENT_IFACE, in_signature='', out_signature='')
    def Release(self): pass

class WifiService(dbus.service.Object):
    PATH_BASE = '/org/bluez/example/service'
    def __init__(self, bus, index):
        self.path = self.PATH_BASE + str(index)
        self.bus = bus
        self.uuid = WIFI_SERVICE_UUID
        self.primary = True
        self.characteristics = []
        dbus.service.Object.__init__(self, bus, self.path)
    def get_properties(self):
        return {
            GATT_SERVICE_IFACE: {
                'UUID': self.uuid,
                'Primary': self.primary,
                'Characteristics': dbus.Array([c.get_path() for c in self.characteristics], signature='o')
            }
        }
    def get_path(self): return dbus.ObjectPath(self.path)
    @dbus.service.method(DBUS_PROP_IFACE, in_signature='s', out_signature='a{sv}')
    def GetAll(self, interface): return self.get_properties()[GATT_SERVICE_IFACE]

class WifiCharacteristic(dbus.service.Object):
    def __init__(self, bus, index, service):
        self.path = service.path + '/char' + str(index)
        self.bus = bus
        self.uuid = WIFI_CHRC_UUID
        self.service = service
        self.flags = ['write']
        self.value = []
        dbus.service.Object.__init__(self, bus, self.path)
    def get_properties(self):
        return {
            GATT_CHRC_IFACE: {
                'Service': self.service.get_path(),
                'UUID': self.uuid,
                'Flags': self.flags,
                'Value': dbus.Array(self.value, signature='y'),
            }
        }
    def get_path(self): return dbus.ObjectPath(self.path)
    @dbus.service.method(DBUS_PROP_IFACE, in_signature='s', out_signature='a{sv}')
    def GetAll(self, interface): return self.get_properties()[GATT_CHRC_IFACE]
    @dbus.service.method(GATT_CHRC_IFACE, in_signature='aya{sv}', out_signature='')
    def WriteValue(self, value, options):
        try:
            raw_bytes = bytes([int(b) for b in value])
            decoded = raw_bytes.decode('utf-8')
            print(f"📥 Nhận được cấu hình WiFi: {decoded}")
            wifi_info = json.loads(decoded)
            ssid = wifi_info.get("ssid", "").strip()
            password = wifi_info.get("password", "").strip()
            api_url = wifi_info.get("api_url", "").strip()

            if ssid and password:
                GLib.timeout_add(100, lambda: connect_wifi(ssid, password) or False)
            if api_url:
                GLib.timeout_add(2000, lambda: update_env_file(api_url) or False)
        except Exception as e:
            print(f"❌ Lỗi xử lý WiFi: {e}")

class IPInfoCharacteristic(dbus.service.Object):
    def __init__(self, bus, index, service):
        self.path = service.path + '/char' + str(index)
        self.bus = bus
        self.uuid = IP_CHRC_UUID
        self.service = service
        self.flags = ['read']
        self.value = []
        dbus.service.Object.__init__(self, bus, self.path)
    def get_properties(self):
        return {
            GATT_CHRC_IFACE: {
                'Service': self.service.get_path(),
                'UUID': self.uuid,
                'Flags': self.flags,
                'Value': dbus.Array(self.value, signature='y'),
            }
        }
    def get_path(self): return dbus.ObjectPath(self.path)
    @dbus.service.method(DBUS_PROP_IFACE, in_signature='s', out_signature='a{sv}')
    def GetAll(self, interface): return self.get_properties()[GATT_CHRC_IFACE]
    @dbus.service.method(GATT_CHRC_IFACE, in_signature='a{sv}', out_signature='ay')
    def ReadValue(self, options):
        ips = get_device_ips()
        ip_json = json.dumps(ips, ensure_ascii=False)
        print(f"📤 Client đọc IP: {ip_json}")
        return dbus.Array([dbus.Byte(b) for b in ip_json.encode('utf-8')], signature='y')

class VslCharacteristic(dbus.service.Object):
    _BUFFER_MAX_SIZE = 8192   # Giới hạn buffer tránh rò rỉ RAM
    _BUFFER_TIMEOUT_S = 10    # Xóa buffer nếu không nhận hết chunk trong 10s

    def __init__(self, bus, index, service):
        self.path = service.path + '/char' + str(index)
        self.bus = bus
        self.uuid = VSL_CHRC_UUID
        self.service = service
        self.flags = ['write']
        self.value = []
        self._buffer = ""
        self._buffer_started_at = None
        dbus.service.Object.__init__(self, bus, self.path)
    def get_properties(self):
        return {
            GATT_CHRC_IFACE: {
                'Service': self.service.get_path(),
                'UUID': self.uuid,
                'Flags': self.flags,
                'Value': dbus.Array(self.value, signature='y'),
            }
        }
    def get_path(self): return dbus.ObjectPath(self.path)
    @dbus.service.method(DBUS_PROP_IFACE, in_signature='s', out_signature='a{sv}')
    def GetAll(self, interface): return self.get_properties()[GATT_CHRC_IFACE]
    @dbus.service.method(GATT_CHRC_IFACE, in_signature='aya{sv}', out_signature='')
    def WriteValue(self, value, options):
        try:
            raw_bytes = bytes([int(b) for b in value])
            decoded = raw_bytes.decode('utf-8')
            
            # Xóa buffer cũ nếu quá timeout (client gửi dang dở rồi bỏ)
            if self._buffer and self._buffer_started_at:
                if time.time() - self._buffer_started_at > self._BUFFER_TIMEOUT_S:
                    print("⚠️ VSL buffer timeout, xóa buffer cũ")
                    self._buffer = ""
                    self._buffer_started_at = None

            # Xử lý logic chunking [1/3]...
            if decoded.startswith('['):
                end_idx = decoded.find(']')
                if end_idx != -1:
                    chunk_info = decoded[1:end_idx].split('/')
                    if len(chunk_info) == 2:
                        idx = int(chunk_info[0])
                        total = int(chunk_info[1])
                        if idx == 1:
                            self._buffer = ""  # Reset khi bắt đầu chuỗi chunk mới
                            self._buffer_started_at = time.time()
                        self._buffer += decoded[end_idx+1:]
                        # Bảo vệ: xóa buffer nếu quá lớn
                        if len(self._buffer) > self._BUFFER_MAX_SIZE:
                            print("⚠️ VSL buffer quá lớn, xóa")
                            self._buffer = ""
                            self._buffer_started_at = None
                            return
                        if idx == total:
                            self._process_message(self._buffer)
                            self._buffer = ""
                            self._buffer_started_at = None
                        return
            
            # Gửi luôn trong 1 cục (nếu payload ngắn)
            self._process_message(decoded)
            
        except Exception as e:
            print(f"❌ Lỗi xử lý VSL data: {e}")

    def _process_message(self, message):
        try:
            data = json.loads(message)
            print(f"📥 Nhận JSON qua BLE: {data}")
            msg_type = data.get('type', '')
            
            if msg_type == 'result':
                words = data.get('words', [])
                transcript = data.get('transcript', '')
                if words:
                    job = VideoJob(words=words, transcript=transcript)
                    enqueue_video_job(job)
                    
            elif msg_type == 'command':
                action = data.get('action', '')
                print(f"🛠️ Nhận lệnh điều khiển: {action}")
                
                if action == 'shutdown':
                    show_message(["đang tắt máy..."], (255, 100, 100))
                    time.sleep(2)
                    subprocess.run(['sudo', 'shutdown', '-h', 'now'])
                elif action == 'reboot':
                    show_message(["đang khởi động lại..."], (255, 200, 100))
                    time.sleep(2)
                    subprocess.run(['sudo', 'reboot'])
                elif action == 'set_mode':
                    pass

            elif msg_type == 'shell':
                cmd = data.get('cmd', '').strip()
                if cmd:
                    threading.Thread(
                        target=self._run_shell_command,
                        args=(cmd,),
                        daemon=True
                    ).start()

            elif msg_type == 'cd':
                path = data.get('path', '').strip()
                self._handle_cd(path)
                    
        except json.JSONDecodeError:
            print("❌ Lỗi parse JSON từ BLE")

    def _handle_cd(self, path):
        global _shell_cwd
        if not path:
            _shell_cwd = '/home/pi'
        elif path.startswith('/'):
            _shell_cwd = path
        else:
            _shell_cwd = os.path.normpath(os.path.join(_shell_cwd, path))
        
        # Kiểm tra thư mục tồn tại
        if not os.path.isdir(_shell_cwd):
            self._send_shell_output(f"cd: {_shell_cwd}: No such directory\n")
            _shell_cwd = '/home/pi'
        else:
            self._send_shell_output(f"📂 {_shell_cwd}\n")

    def _run_shell_command(self, cmd):
        global _shell_cwd
        print(f"🖥️ Shell: [{_shell_cwd}] $ {cmd}")
        self._send_shell_output(f"$ {cmd}\n")
        
        try:
            proc = subprocess.Popen(
                cmd,
                shell=True,
                cwd=_shell_cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                env={**os.environ, 'PATH': '/home/pi/lcd_env/bin:' + os.environ.get('PATH', '')}
            )
            
            # Stream output từng dòng
            for line in proc.stdout:
                self._send_shell_output(line)
            
            proc.wait(timeout=30)
            
            if proc.returncode != 0:
                self._send_shell_output(f"[exit code: {proc.returncode}]\n")
        except subprocess.TimeoutExpired:
            proc.kill()
            self._send_shell_output("\n⏰ Timeout (30s)\n")
        except Exception as e:
            self._send_shell_output(f"\n❌ Error: {e}\n")
        
        # Gửi EOT marker
        self._send_shell_output("\x04")

    def _send_shell_output(self, text):
        global _shell_output_char
        if _shell_output_char:
            _shell_output_char.send_output(text)

class ShellOutputCharacteristic(dbus.service.Object):
    """Characteristic Notify để stream shell output về Flutter."""
    
    CCCD_UUID = '00002902-0000-1000-8000-00805f9b34fb'

    def __init__(self, bus, index, service):
        self.path = service.path + '/char' + str(index)
        self.bus = bus
        self.uuid = SHELL_CHRC_UUID
        self.service = service
        self.flags = ['notify', 'read']
        self.notifying = False
        self.value = []
        dbus.service.Object.__init__(self, bus, self.path)
    
    def get_properties(self):
        return {
            GATT_CHRC_IFACE: {
                'Service': self.service.get_path(),
                'UUID': self.uuid,
                'Flags': self.flags,
                'Value': dbus.Array(self.value, signature='y'),
                'Descriptors': dbus.Array([], signature='o'),
            }
        }
    
    def get_path(self): return dbus.ObjectPath(self.path)
    
    @dbus.service.method(DBUS_PROP_IFACE, in_signature='s', out_signature='a{sv}')
    def GetAll(self, interface): return self.get_properties()[GATT_CHRC_IFACE]
    
    @dbus.service.method(GATT_CHRC_IFACE, in_signature='a{sv}', out_signature='ay')
    def ReadValue(self, options):
        # Trả về CWD hiện tại khi Read
        global _shell_cwd
        prompt = f"{_shell_cwd}"
        return dbus.Array([dbus.Byte(b) for b in prompt.encode('utf-8')], signature='y')

    @dbus.service.method(GATT_CHRC_IFACE, in_signature='', out_signature='')
    def StartNotify(self):
        self.notifying = True
        print("🔔 Shell Notify: ON")
        global _shell_cwd, _ble_connected
        _ble_connected = True
        # Hiển thị trạng thái kết nối trên LCD
        show_message(["đã kết nối", "", "bật mic trên app", "để sử dụng"], (100, 255, 100))
        self.send_output(f"📂 {_shell_cwd}\n")

    @dbus.service.method(GATT_CHRC_IFACE, in_signature='', out_signature='')
    def StopNotify(self):
        self.notifying = False
        print("🔕 Shell Notify: OFF")
        global _ble_connected
        _ble_connected = False
        # Hiển thị lại màn hình chờ kết nối
        show_message(["vui lòng", "kết nối ble"], (100, 200, 255))

    def send_output(self, text):
        if not self.notifying:
            return
        try:
            data = text.encode('utf-8')
            # Chunk output nếu quá dài (BLE MTU ~500 bytes)
            chunk_size = 500
            for i in range(0, len(data), chunk_size):
                chunk = data[i:i + chunk_size]
                value = dbus.Array([dbus.Byte(b) for b in chunk], signature='y')
                self.PropertiesChanged(
                    GATT_CHRC_IFACE,
                    {'Value': value},
                    []
                )
                if len(data) > chunk_size:
                    time.sleep(0.02)  # Delay nhỏ giữa chunks
        except Exception as e:
            print(f"❌ Shell notify error: {e}")

    @dbus.service.signal(DBUS_PROP_IFACE, signature='sa{sv}as')
    def PropertiesChanged(self, interface, changed, invalidated):
        pass

class WifiSetupApplication(dbus.service.Object):
    def __init__(self, bus):
        self.path = '/org/bluez/example'
        self.services = []
        dbus.service.Object.__init__(self, bus, self.path)

        wifi_service = WifiService(bus, 0)
        wifi_chrc = WifiCharacteristic(bus, 0, wifi_service)
        wifi_service.characteristics.append(wifi_chrc)
        ip_chrc = IPInfoCharacteristic(bus, 1, wifi_service)
        wifi_service.characteristics.append(ip_chrc)
        
        # Thêm characteristic cho VSL
        vsl_chrc = VslCharacteristic(bus, 2, wifi_service)
        wifi_service.characteristics.append(vsl_chrc)

        # Thêm characteristic cho Shell output (Notify)
        global _shell_output_char
        shell_chrc = ShellOutputCharacteristic(bus, 3, wifi_service)
        wifi_service.characteristics.append(shell_chrc)
        _shell_output_char = shell_chrc
        
        self.services.append(wifi_service)

    def get_path(self): return dbus.ObjectPath(self.path)
    @dbus.service.method(DBUS_OM_IFACE, out_signature='a{oa{sa{sv}}}')
    def GetManagedObjects(self):
        response = {}
        for service in self.services:
            response[service.get_path()] = service.get_properties()
            for chrc in service.characteristics:
                response[chrc.get_path()] = chrc.get_properties()
        return response

# ============ BLE AGENT (Auto-accept pairing) ============
AGENT_IFACE = 'org.bluez.Agent1'
AGENT_MANAGER_IFACE = 'org.bluez.AgentManager1'
AGENT_PATH = '/org/bluez/example/agent'

class NoInputNoOutputAgent(dbus.service.Object):
    """Agent tự động chấp nhận pairing mà không cần nhập PIN hay xác nhận."""

    @dbus.service.method(AGENT_IFACE, in_signature='', out_signature='')
    def Release(self):
        pass

    @dbus.service.method(AGENT_IFACE, in_signature='os', out_signature='')
    def AuthorizeService(self, device, uuid):
        print(f"✅ Auto-authorize service {uuid} cho {device}")

    @dbus.service.method(AGENT_IFACE, in_signature='o', out_signature='s')
    def RequestPinCode(self, device):
        return "0000"

    @dbus.service.method(AGENT_IFACE, in_signature='o', out_signature='u')
    def RequestPasskey(self, device):
        return dbus.UInt32(0)

    @dbus.service.method(AGENT_IFACE, in_signature='ouq', out_signature='')
    def DisplayPasskey(self, device, passkey, entered):
        pass

    @dbus.service.method(AGENT_IFACE, in_signature='os', out_signature='')
    def DisplayPinCode(self, device, pincode):
        pass

    @dbus.service.method(AGENT_IFACE, in_signature='ou', out_signature='')
    def RequestConfirmation(self, device, passkey):
        print(f"✅ Auto-confirm pairing cho {device}")

    @dbus.service.method(AGENT_IFACE, in_signature='o', out_signature='')
    def RequestAuthorization(self, device):
        print(f"✅ Auto-authorize {device}")

    @dbus.service.method(AGENT_IFACE, in_signature='', out_signature='')
    def Cancel(self):
        pass

# ============ MAIN ============
if __name__ == '__main__':
    print("=" * 50)
    print("📡 SignSound BLE Application v3.0 (Display Node)")
    print("=" * 50)

    # Bật LCD
    init_lcd()
    show_message(["vui lòng", "kết nối ble"], (100, 200, 255))

    # Chạy thread phát video
    video_thread = threading.Thread(target=video_playback_worker, daemon=True)
    video_thread.start()

    # Thiết lập BLE Server
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()

    adapter_path = find_adapter(bus)
    if not adapter_path:
        print("❌ Không tìm thấy Bluetooth adapter!")
        show_message(["lỗi bluetooth", "không tìm thấy adapter"], (255, 100, 100))
        sys.exit(1)

    print(f"🔵 Bluetooth adapter: {adapter_path}")
    adapter_props = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, adapter_path), DBUS_PROP_IFACE)
    try:
        adapter_props.Set('org.bluez.Adapter1', 'Powered', dbus.Boolean(True))
        adapter_props.Set('org.bluez.Adapter1', 'Pairable', dbus.Boolean(True))
        adapter_props.Set('org.bluez.Adapter1', 'Discoverable', dbus.Boolean(True))
        adapter_props.Set('org.bluez.Adapter1', 'PairableTimeout', dbus.UInt32(0))
        adapter_props.Set('org.bluez.Adapter1', 'DiscoverableTimeout', dbus.UInt32(0))
    except Exception as e:
        print(f"⚠️ Không thể set adapter properties: {e}")

    # Đăng ký Agent tự động chấp nhận pairing (NoInputNoOutput)
    agent = NoInputNoOutputAgent(bus, AGENT_PATH)
    agent_manager = dbus.Interface(
        bus.get_object(BLUEZ_SERVICE_NAME, '/org/bluez'),
        AGENT_MANAGER_IFACE
    )
    try:
        agent_manager.RegisterAgent(AGENT_PATH, "NoInputNoOutput")
        agent_manager.RequestDefaultAgent(AGENT_PATH)
        print("✅ BLE Agent registered (NoInputNoOutput - auto accept pairing)")
    except Exception as e:
        print(f"⚠️ Agent registration: {e}")

    app = WifiSetupApplication(bus)
    adv = Advertisement(bus, 0)

    ad_manager = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, adapter_path), LE_ADVERTISING_MANAGER_IFACE)
    ad_manager.RegisterAdvertisement(adv.get_path(), {}, reply_handler=lambda: print("✅ Advertising OK"), error_handler=lambda e: print(f"❌ Adv Error: {e}"))

    gatt_manager = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, adapter_path), GATT_MANAGER_IFACE)
    gatt_manager.RegisterApplication(app.get_path(), {}, reply_handler=lambda: print("✅ GATT App OK"), error_handler=lambda e: print(f"❌ App Error: {e}"))

    show_message(["sẵn sàng"], (100, 255, 100))
    print("BLE Application đang chạy...")

    mainloop = GLib.MainLoop()
    try:
        mainloop.run()
    except KeyboardInterrupt:
        print("\n👋 Đang tắt...")
        video_thread_running = False
        ad_manager.UnregisterAdvertisement(adv.get_path())
        spi.close()
        GPIO.cleanup()
