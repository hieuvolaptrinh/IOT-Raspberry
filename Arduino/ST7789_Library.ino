/*
 * ST7789 1.54" TFT - Arduino Nano
 * 
 * Wiring (với điện trở chia áp 1K):
 * LCD     Arduino Nano
 * VCC  -> 3.3V
 * GND  -> GND
 * SCL  -> D13 (qua trở 1K)
 * SDA  -> D11 (qua trở 1K)
 * RES  -> D8  (qua trở 1K)
 * DC   -> D9  (qua trở 1K)
 * CS   -> D10 (qua trở 1K)
 * BLK  -> 3.3V (hoặc D7)
 */

#include <Adafruit_GFX.h>
#include <Adafruit_ST7789.h>
#include <SPI.h>

#define TFT_CS   10
#define TFT_DC    9
#define TFT_RST   8
#define TFT_BL    7   // Backlight pin (optional)

Adafruit_ST7789 tft = Adafruit_ST7789(TFT_CS, TFT_DC, TFT_RST);

void setup() {
  Serial.begin(9600);
  
  // Bật backlight
  pinMode(TFT_BL, OUTPUT);
  digitalWrite(TFT_BL, HIGH);
  
  Serial.println("Initializing...");
  
  // Khởi tạo với SPI_MODE3
  tft.init(240, 240, SPI_MODE3);
  
  // BẬT INVERSION - RẤT QUAN TRỌNG cho ST7789!
  tft.invertDisplay(true);
  
  tft.setRotation(0);
  
  // Test các màu để debug
  Serial.println("RED");
  tft.fillScreen(ST77XX_RED);
  delay(500);
  
  Serial.println("GREEN");
  tft.fillScreen(ST77XX_GREEN);
  delay(500);
  
  Serial.println("BLUE");
  tft.fillScreen(ST77XX_BLUE);
  delay(500);
  
  Serial.println("WHITE");
  tft.fillScreen(ST77XX_WHITE);
  delay(500);
  
  // Hiển thị text
  tft.fillScreen(ST77XX_BLACK);
  tft.setTextColor(ST77XX_WHITE);
  tft.setTextSize(2);
  tft.setCursor(30, 100);
  tft.print("Hello Nano!");
  
  tft.setTextColor(ST77XX_YELLOW);
  tft.setCursor(50, 130);
  tft.print("ST7789 OK");
  
  Serial.println("Done!");
}

void loop() {}
