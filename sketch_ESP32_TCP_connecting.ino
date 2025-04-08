#include <WiFi.h>

const char* ssid = "sussymg";
const char* password = "123456789";

const char* serverIP = "192.168.146.136";
const int serverPort = 5555;

WiFiClient client;

void connectToWiFi() {
  Serial.print("Connecting to WiFi");
  WiFi.begin(ssid, password);
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWiFi connected");
    Serial.print("IP address: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\nFailed to connect to WiFi");
  }
}

bool connectToServer() {
  Serial.print("Connecting to server...");
  if (client.connect(serverIP, serverPort)) {
    Serial.println("Connected!");
    client.println("ESP32 client connected");
    return true;
  } else {
    Serial.println("Failed!");
    return false;
  }
}

void setup() {
  Serial.begin(115200);
  delay(1000);
  
  connectToWiFi();
  connectToServer();
}

void loop() {
  // Maintain WiFi connection
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi disconnected. Reconnecting...");
    connectToWiFi();
  }
  
  // Maintain server connection
  if (!client.connected()) {
    Serial.println("Server disconnected. Reconnecting...");
    if (!connectToServer()) {
      delay(5000); // Wait before retrying
      return;
    }
  }
  
  // Handle incoming data
  while (client.available()) {
    String response = client.readStringUntil('\n');
    Serial.print("Server: ");
    Serial.println(response);
  }
  
  // Example: Send data every 3 seconds
  static unsigned long lastSend = 0;
  if (millis() - lastSend > 3000) {
    lastSend = millis();
    client.println("ESP32 status: OK");
    Serial.println("Sent status update");
  }
}

