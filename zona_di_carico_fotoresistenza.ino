#include <WiFi.h>
#include <WiFiClient.h>
#include <ArduinoJson.h>

const int fotoR = 34;
const int soglia = 400;
int stato;

// WiFi credentials
const char* ssid = "Andrea's Galaxy A35 5G";
const char* password = "Andrea216";

// TCP server settings - CORRECTED
const char* server_ip = "192.168.99.232"; // Updated server IP
const uint16_t server_port = 5555; // TCP port confirmed as 5555
const char* client_id = "ESP_Matrix"; // CORRECTED to match routing table

WiFiClient client;

void connectToWiFi() {
  Serial.print("[WiFi] Connecting to ");
  Serial.print(ssid);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\n[WiFi] Connected");
  Serial.print("[WiFi] IP address: ");
  Serial.println(WiFi.localIP());
}

void connectToServer() {
  Serial.print("[TCP] Connecting to server... ");
  if (client.connect(server_ip, server_port)) {
    Serial.println("Connected");
    client.println(client_id); // send client ID to server
    Serial.println("[TCP] Sent client ID: " + String(client_id));
  } else {
    Serial.println("Failed to connect to server.");
  }
}

void sendData() {
  if (!client.connected()) {
    Serial.println("[TCP] Disconnected. Reconnecting...");
    client.stop();
    connectToServer();
    return;
  }
  
  int carico = analogRead(fotoR);
  Serial.print("[Sensor] Raw reading: ");
  Serial.println(carico);
  
  if (carico >= soglia) {
    stato = 0;
  } else {
    stato = 1;
  }
  
  // Create simple JSON without matrix
  StaticJsonDocument<100> doc;
  doc["state"] = stato;
  doc["sensor_value"] = carico;
  
  // Convert to string and send
  String jsonString;
  serializeJson(doc, jsonString);
  client.println(jsonString);
  
  Serial.print("[TCP] Data sent: ");
  Serial.println(jsonString);
  Serial.print("[TCP] Sensor state: ");
  Serial.println(stato);
}

void setup() {
  Serial.begin(115200);
  delay(1000);
  connectToWiFi();
  connectToServer();
  pinMode(fotoR, INPUT);
}

void loop() {
  sendData();
  delay(2000); // Send every 2 seconds to avoid flooding
}
