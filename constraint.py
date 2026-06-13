#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os

# ============ PATHS ============
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
VIDEO_DIR = os.path.join(SCRIPT_DIR, "video")
FONT_PATH = os.path.join(SCRIPT_DIR, "SVN-Arial Regular.ttf")
ENV_FILE_PATH = os.path.join(SCRIPT_DIR, ".env")

# ============ BLUEZ D-BUS INTERFACES ============
BLUEZ_SERVICE_NAME = 'org.bluez'
GATT_MANAGER_IFACE = 'org.bluez.GattManager1'
LE_ADVERTISING_MANAGER_IFACE = 'org.bluez.LEAdvertisingManager1'
DBUS_OM_IFACE = 'org.freedesktop.DBus.ObjectManager'
DBUS_PROP_IFACE = 'org.freedesktop.DBus.Properties'
GATT_SERVICE_IFACE = 'org.bluez.GattService1'
GATT_CHRC_IFACE = 'org.bluez.GattCharacteristic1'
LE_ADVERTISEMENT_IFACE = 'org.bluez.LEAdvertisement1'

# ============ UUIDs ============
WIFI_SERVICE_UUID = '00001234-0000-1000-8000-00805f9b34fb'
WIFI_CHRC_UUID = '0000abcd-0000-1000-8000-00805f9b34fb'   # Write: WiFi + ENV config
IP_CHRC_UUID = '0000abce-0000-1000-8000-00805f9b34fb'     # Read:  IP info
VSL_CHRC_UUID = '0000abcf-0000-1000-8000-00805f9b34fb'    # Write: VSL Result data

# ============ DISPLAY SETTINGS ============
MIRROR_MODE = True
TARGET_LCD_FPS = 18  
LCD_FRAME_TIME = 1.0 / TARGET_LCD_FPS  
VIDEO_SPEED = 2.0
FINGERSPELL_SPEED = 3.5

# ============ GPIO PINS ============
DC_PIN = 24
RST_PIN = 25
BL_PIN = 18
