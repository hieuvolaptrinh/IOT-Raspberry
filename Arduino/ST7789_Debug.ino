/*
 * ST7789 1.54" TFT Display - Text Demo (NO LIBRARY NEEDED)
 * Hiển thị text mà KHÔNG cần cài thư viện ngoài
 * Bao gồm font 5x7 tích hợp sẵn
 * 
 * Wiring:
 * ST7789    Arduino Nano
 * VCC   ->  3.3V
 * GND   ->  GND
 * SCL   ->  D13 (SCK)
 * SDA   ->  D11 (MOSI)
 * RES   ->  D9
 * DC    ->  D8
 * CS    ->  D10
 * BLK   ->  3.3V
 */

#include <SPI.h>

// Pin definitions
#define TFT_CS    10
#define TFT_DC    8
#define TFT_RST   9

// Display dimensions
#define TFT_WIDTH  240
#define TFT_HEIGHT 240

// Colors (RGB565)
#define BLACK     0x0000
#define WHITE     0xFFFF
#define RED       0xF800
#define GREEN     0x07E0
#define BLUE      0x001F
#define YELLOW    0xFFE0
#define CYAN      0x07FF
#define MAGENTA   0xF81F
#define ORANGE    0xFD20

// ST7789 Commands
#define ST7789_SWRESET   0x01
#define ST7789_SLPOUT    0x11
#define ST7789_NORON     0x13
#define ST7789_INVON     0x21
#define ST7789_INVOFF    0x20
#define ST7789_DISPON    0x29
#define ST7789_CASET     0x2A
#define ST7789_RASET     0x2B
#define ST7789_RAMWR     0x2C
#define ST7789_COLMOD    0x3A
#define ST7789_MADCTL    0x36

// Font 5x7 - 95 printable ASCII characters (space to ~)
// Mỗi ký tự có 5 cột, mỗi cột là 1 byte (7 bit dùng cho 7 hàng)
const uint8_t font5x7[] PROGMEM = {
  0x00, 0x00, 0x00, 0x00, 0x00, // (space)
  0x00, 0x00, 0x5F, 0x00, 0x00, // !
  0x00, 0x07, 0x00, 0x07, 0x00, // "
  0x14, 0x7F, 0x14, 0x7F, 0x14, // #
  0x24, 0x2A, 0x7F, 0x2A, 0x12, // $
  0x23, 0x13, 0x08, 0x64, 0x62, // %
  0x36, 0x49, 0x55, 0x22, 0x50, // &
  0x00, 0x05, 0x03, 0x00, 0x00, // '
  0x00, 0x1C, 0x22, 0x41, 0x00, // (
  0x00, 0x41, 0x22, 0x1C, 0x00, // )
  0x08, 0x2A, 0x1C, 0x2A, 0x08, // *
  0x08, 0x08, 0x3E, 0x08, 0x08, // +
  0x00, 0x50, 0x30, 0x00, 0x00, // ,
  0x08, 0x08, 0x08, 0x08, 0x08, // -
  0x00, 0x60, 0x60, 0x00, 0x00, // .
  0x20, 0x10, 0x08, 0x04, 0x02, // /
  0x3E, 0x51, 0x49, 0x45, 0x3E, // 0
  0x00, 0x42, 0x7F, 0x40, 0x00, // 1
  0x42, 0x61, 0x51, 0x49, 0x46, // 2
  0x21, 0x41, 0x45, 0x4B, 0x31, // 3
  0x18, 0x14, 0x12, 0x7F, 0x10, // 4
  0x27, 0x45, 0x45, 0x45, 0x39, // 5
  0x3C, 0x4A, 0x49, 0x49, 0x30, // 6
  0x01, 0x71, 0x09, 0x05, 0x03, // 7
  0x36, 0x49, 0x49, 0x49, 0x36, // 8
  0x06, 0x49, 0x49, 0x29, 0x1E, // 9
  0x00, 0x36, 0x36, 0x00, 0x00, // :
  0x00, 0x56, 0x36, 0x00, 0x00, // ;
  0x00, 0x08, 0x14, 0x22, 0x41, // <
  0x14, 0x14, 0x14, 0x14, 0x14, // =
  0x41, 0x22, 0x14, 0x08, 0x00, // >
  0x02, 0x01, 0x51, 0x09, 0x06, // ?
  0x32, 0x49, 0x79, 0x41, 0x3E, // @
  0x7E, 0x11, 0x11, 0x11, 0x7E, // A
  0x7F, 0x49, 0x49, 0x49, 0x36, // B
  0x3E, 0x41, 0x41, 0x41, 0x22, // C
  0x7F, 0x41, 0x41, 0x22, 0x1C, // D
  0x7F, 0x49, 0x49, 0x49, 0x41, // E
  0x7F, 0x09, 0x09, 0x01, 0x01, // F
  0x3E, 0x41, 0x41, 0x51, 0x32, // G
  0x7F, 0x08, 0x08, 0x08, 0x7F, // H
  0x00, 0x41, 0x7F, 0x41, 0x00, // I
  0x20, 0x40, 0x41, 0x3F, 0x01, // J
  0x7F, 0x08, 0x14, 0x22, 0x41, // K
  0x7F, 0x40, 0x40, 0x40, 0x40, // L
  0x7F, 0x02, 0x04, 0x02, 0x7F, // M
  0x7F, 0x04, 0x08, 0x10, 0x7F, // N
  0x3E, 0x41, 0x41, 0x41, 0x3E, // O
  0x7F, 0x09, 0x09, 0x09, 0x06, // P
  0x3E, 0x41, 0x51, 0x21, 0x5E, // Q
  0x7F, 0x09, 0x19, 0x29, 0x46, // R
  0x46, 0x49, 0x49, 0x49, 0x31, // S
  0x01, 0x01, 0x7F, 0x01, 0x01, // T
  0x3F, 0x40, 0x40, 0x40, 0x3F, // U
  0x1F, 0x20, 0x40, 0x20, 0x1F, // V
  0x7F, 0x20, 0x18, 0x20, 0x7F, // W
  0x63, 0x14, 0x08, 0x14, 0x63, // X
  0x03, 0x04, 0x78, 0x04, 0x03, // Y
  0x61, 0x51, 0x49, 0x45, 0x43, // Z
  0x00, 0x00, 0x7F, 0x41, 0x41, // [
  0x02, 0x04, 0x08, 0x10, 0x20, // backslash
  0x41, 0x41, 0x7F, 0x00, 0x00, // ]
  0x04, 0x02, 0x01, 0x02, 0x04, // ^
  0x40, 0x40, 0x40, 0x40, 0x40, // _
  0x00, 0x01, 0x02, 0x04, 0x00, // `
  0x20, 0x54, 0x54, 0x54, 0x78, // a
  0x7F, 0x48, 0x44, 0x44, 0x38, // b
  0x38, 0x44, 0x44, 0x44, 0x20, // c
  0x38, 0x44, 0x44, 0x48, 0x7F, // d
  0x38, 0x54, 0x54, 0x54, 0x18, // e
  0x08, 0x7E, 0x09, 0x01, 0x02, // f
  0x08, 0x14, 0x54, 0x54, 0x3C, // g
  0x7F, 0x08, 0x04, 0x04, 0x78, // h
  0x00, 0x44, 0x7D, 0x40, 0x00, // i
  0x20, 0x40, 0x44, 0x3D, 0x00, // j
  0x00, 0x7F, 0x10, 0x28, 0x44, // k
  0x00, 0x41, 0x7F, 0x40, 0x00, // l
  0x7C, 0x04, 0x18, 0x04, 0x78, // m
  0x7C, 0x08, 0x04, 0x04, 0x78, // n
  0x38, 0x44, 0x44, 0x44, 0x38, // o
  0x7C, 0x14, 0x14, 0x14, 0x08, // p
  0x08, 0x14, 0x14, 0x18, 0x7C, // q
  0x7C, 0x08, 0x04, 0x04, 0x08, // r
  0x48, 0x54, 0x54, 0x54, 0x20, // s
  0x04, 0x3F, 0x44, 0x40, 0x20, // t
  0x3C, 0x40, 0x40, 0x20, 0x7C, // u
  0x1C, 0x20, 0x40, 0x20, 0x1C, // v
  0x3C, 0x40, 0x30, 0x40, 0x3C, // w
  0x44, 0x28, 0x10, 0x28, 0x44, // x
  0x0C, 0x50, 0x50, 0x50, 0x3C, // y
  0x44, 0x64, 0x54, 0x4C, 0x44, // z
  0x00, 0x08, 0x36, 0x41, 0x00, // {
  0x00, 0x00, 0x7F, 0x00, 0x00, // |
  0x00, 0x41, 0x36, 0x08, 0x00, // }
  0x08, 0x08, 0x2A, 0x1C, 0x08, // ~
};

// Text settings
uint8_t textSize = 1;
uint16_t textColor = WHITE;
int16_t cursorX = 0;
int16_t cursorY = 0;

// ==================== SPI Functions ====================

void writeCommand(uint8_t cmd) {
  digitalWrite(TFT_DC, LOW);
  digitalWrite(TFT_CS, LOW);
  SPI.transfer(cmd);
  digitalWrite(TFT_CS, HIGH);
}

void writeData(uint8_t data) {
  digitalWrite(TFT_DC, HIGH);
  digitalWrite(TFT_CS, LOW);
  SPI.transfer(data);
  digitalWrite(TFT_CS, HIGH);
}

// ==================== ST7789 Initialization ====================

void tftInit() {
  // Hardware reset
  digitalWrite(TFT_RST, HIGH);
  delay(50);
  digitalWrite(TFT_RST, LOW);
  delay(50);
  digitalWrite(TFT_RST, HIGH);
  delay(150);
  
  writeCommand(ST7789_SWRESET);
  delay(150);
  
  writeCommand(ST7789_SLPOUT);
  delay(500);
  
  writeCommand(ST7789_COLMOD);
  writeData(0x55);  // 16-bit color
  delay(10);
  
  writeCommand(ST7789_MADCTL);
  writeData(0x00);  // Rotation 0
  delay(10);
  
  writeCommand(ST7789_INVON);  // Inversion on (thử INVOFF nếu màu sai)
  delay(10);
  
  writeCommand(ST7789_NORON);
  delay(10);
  
  writeCommand(ST7789_DISPON);
  delay(100);
}

// ==================== Drawing Functions ====================

void setAddressWindow(uint16_t x0, uint16_t y0, uint16_t x1, uint16_t y1) {
  writeCommand(ST7789_CASET);
  writeData(x0 >> 8);
  writeData(x0 & 0xFF);
  writeData(x1 >> 8);
  writeData(x1 & 0xFF);
  
  writeCommand(ST7789_RASET);
  writeData(y0 >> 8);
  writeData(y0 & 0xFF);
  writeData(y1 >> 8);
  writeData(y1 & 0xFF);
  
  writeCommand(ST7789_RAMWR);
}

void fillScreen(uint16_t color) {
  setAddressWindow(0, 0, TFT_WIDTH - 1, TFT_HEIGHT - 1);
  
  digitalWrite(TFT_DC, HIGH);
  digitalWrite(TFT_CS, LOW);
  
  uint8_t hi = color >> 8;
  uint8_t lo = color & 0xFF;
  
  for (uint32_t i = 0; i < (uint32_t)TFT_WIDTH * TFT_HEIGHT; i++) {
    SPI.transfer(hi);
    SPI.transfer(lo);
  }
  
  digitalWrite(TFT_CS, HIGH);
}

void fillRect(int16_t x, int16_t y, int16_t w, int16_t h, uint16_t color) {
  if (x >= TFT_WIDTH || y >= TFT_HEIGHT || w <= 0 || h <= 0) return;
  if (x + w > TFT_WIDTH) w = TFT_WIDTH - x;
  if (y + h > TFT_HEIGHT) h = TFT_HEIGHT - y;
  
  setAddressWindow(x, y, x + w - 1, y + h - 1);
  
  digitalWrite(TFT_DC, HIGH);
  digitalWrite(TFT_CS, LOW);
  
  uint8_t hi = color >> 8;
  uint8_t lo = color & 0xFF;
  
  for (uint32_t i = 0; i < (uint32_t)w * h; i++) {
    SPI.transfer(hi);
    SPI.transfer(lo);
  }
  
  digitalWrite(TFT_CS, HIGH);
}

void drawPixel(int16_t x, int16_t y, uint16_t color) {
  if (x < 0 || x >= TFT_WIDTH || y < 0 || y >= TFT_HEIGHT) return;
  
  setAddressWindow(x, y, x, y);
  
  digitalWrite(TFT_DC, HIGH);
  digitalWrite(TFT_CS, LOW);
  SPI.transfer(color >> 8);
  SPI.transfer(color & 0xFF);
  digitalWrite(TFT_CS, HIGH);
}

void drawLine(int16_t x0, int16_t y0, int16_t x1, int16_t y1, uint16_t color) {
  int16_t dx = abs(x1 - x0), sx = x0 < x1 ? 1 : -1;
  int16_t dy = -abs(y1 - y0), sy = y0 < y1 ? 1 : -1;
  int16_t err = dx + dy, e2;
  
  while (true) {
    drawPixel(x0, y0, color);
    if (x0 == x1 && y0 == y1) break;
    e2 = 2 * err;
    if (e2 >= dy) { err += dy; x0 += sx; }
    if (e2 <= dx) { err += dx; y0 += sy; }
  }
}

// ==================== Text Functions ====================

void setTextSize(uint8_t s) {
  textSize = (s > 0) ? s : 1;
}

void setTextColor(uint16_t c) {
  textColor = c;
}

void setCursor(int16_t x, int16_t y) {
  cursorX = x;
  cursorY = y;
}

void drawChar(int16_t x, int16_t y, char c, uint16_t color, uint8_t size) {
  if (c < 32 || c > 126) c = '?';  // Chỉ hỗ trợ ASCII printable
  
  uint16_t index = (c - 32) * 5;
  
  for (uint8_t col = 0; col < 5; col++) {
    uint8_t line = pgm_read_byte(&font5x7[index + col]);
    
    for (uint8_t row = 0; row < 7; row++) {
      if (line & (1 << row)) {
        if (size == 1) {
          drawPixel(x + col, y + row, color);
        } else {
          fillRect(x + col * size, y + row * size, size, size, color);
        }
      }
    }
  }
}

void printChar(char c) {
  if (c == '\n') {
    cursorX = 0;
    cursorY += 8 * textSize;
    return;
  }
  if (c == '\r') {
    cursorX = 0;
    return;
  }
  
  drawChar(cursorX, cursorY, c, textColor, textSize);
  cursorX += 6 * textSize;  // 5 pixels + 1 space
  
  // Wrap text
  if (cursorX > TFT_WIDTH - 6 * textSize) {
    cursorX = 0;
    cursorY += 8 * textSize;
  }
}

void printText(const char* str) {
  while (*str) {
    printChar(*str++);
  }
}

void printNumber(int num) {
  char buf[12];
  itoa(num, buf, 10);
  printText(buf);
}

void println(const char* str) {
  printText(str);
  printChar('\n');
}

// ==================== Setup ====================

void setup() {
  Serial.begin(9600);
  delay(500);
  
  Serial.println("ST7789 Text Demo - NO LIBRARY VERSION");
  
  // Initialize pins
  pinMode(TFT_CS, OUTPUT);
  pinMode(TFT_DC, OUTPUT);
  pinMode(TFT_RST, OUTPUT);
  
  digitalWrite(TFT_CS, HIGH);
  
  // Start SPI
  SPI.begin();
  SPI.beginTransaction(SPISettings(8000000, MSBFIRST, SPI_MODE0));
  
  // Initialize display
  tftInit();
  
  Serial.println("Display initialized!");
  
  // Demo!
  demoText();
}

void loop() {
  static unsigned long lastUpdate = 0;
  static int counter = 0;
  
  if (millis() - lastUpdate > 2000) {
    lastUpdate = millis();
    counter++;
    
    // Cập nhật số đếm
    fillRect(0, 200, 240, 40, BLACK);
    setCursor(10, 210);
    setTextColor(CYAN);
    setTextSize(2);
    printText("Counter: ");
    printNumber(counter);
    
    Serial.print("Counter: ");
    Serial.println(counter);
  }
}

void demoText() {
  // Xóa màn hình
  fillScreen(BLACK);
  
  // === Tiêu đề lớn ===
  setCursor(20, 10);
  setTextColor(YELLOW);
  setTextSize(3);
  println("Hello!");
  
  // === Text thông thường ===
  setCursor(10, 50);
  setTextColor(WHITE);
  setTextSize(2);
  println("Xin chao!");
  println("Day la man hinh");
  println("TFT ST7789 1.54\"");
  
  // === Text nhiều màu ===
  setCursor(10, 130);
  setTextSize(2);
  setTextColor(RED);
  printText("R");
  setTextColor(GREEN);
  printText("G");
  setTextColor(BLUE);
  printText("B");
  setTextColor(WHITE);
  println(" Colors");
  
  // === Text nhỏ ===
  setCursor(10, 160);
  setTextColor(CYAN);
  setTextSize(1);
  println("Text nho (size 1)");
  println("Arduino + ST7789");
  println("240x240 pixels");
  
  // === Vẽ đường kẻ ===
  drawLine(0, 195, 240, 195, MAGENTA);
  
  // === Counter ===
  setCursor(10, 210);
  setTextColor(CYAN);
  setTextSize(2);
  printText("Counter: 0");
  
  Serial.println("Text demo displayed!");
}
