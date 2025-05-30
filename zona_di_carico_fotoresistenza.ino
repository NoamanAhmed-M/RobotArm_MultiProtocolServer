#include <WiFi.h>
#include <WiFiClient.h>
#include <ArduinoJson.h>

String clientNameIs = "Stazione di prelievo";

const int fotoR = 34;
const int soglia = 400;
int stato;

// WiFi credentials
const char *ssid = "TP-Link_CE88";
const char *password = "123456789";

// TCP server settings
const char *server_ip = "192.168.1.100";
const uint16_t server_port = 5555;
const char *client_id = "ESP32_Sensor";

WiFiClient client;

unsigned long lastSendTime = 0;
unsigned long lastReconnectAttempt = 0;
const unsigned long sendInterval = 2000;      // send every 2 seconds
const unsigned long reconnectInterval = 5000; // Reconnect attempt every 5 seconds

int reconnectCount = 0;
int messagesSent = 0;
bool isConnectedToServer = false;

void connectToWiFi()
{
  Serial.print("[WiFi] Connecting to ");
  Serial.print(ssid);

  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED)
  {
    delay(500);
    Serial.print(".");
  }
  if (WiFi.status() == WL_CONNECTED)
  {
    Serial.println("\n[WiFi] Connected");
    Serial.print("[WiFi] IP address: ");
    Serial.println(WiFi.localIP());
  }
  else
  {
    Serial.println("\n[WiFi] Failed to connect");
    Serial.println("[WiFi] Restarting " + clientNameIs + "...");
    delay(1000);
    ESP.restart();
  }
}

bool connectToServer()
{
  Serial.print("[TCP] Connecting to server... ");
  if (client.connect(server_ip, server_port))
  {
    Serial.println("Connected");
    client.println(client_id); // send client ID to server
    Serial.println("[TCP] Sent client ID: " + String(client_id));

    // Send initial connection message
    StaticJsonDocument<200> doc;
    doc["type"] = "connection";
    doc["message"] = "ESP32_Sensor connected";
    doc["reconnect_count"] = reconnectCount;
    doc["uptime"] = millis();

    String jsonString;
    serializeJson(doc, jsonString);
    client.println(jsonString);

    isConnectedToServer = true;
    reconnectCount++;
    return true;
  }
  else
  {
    Serial.println("Failed to connect to server.");
    isConnectedToServer = false;
    return false;
  }
}

void sendData()
{
  // Check WiFi connection
  if (WiFi.status() != WL_CONNECTED)
  {
    Serial.println("[WiFi] WiFi disconnected. Reconnecting...");
    connectToWiFi();
    return;
  }

  if (!client.connected())
  {
    Serial.println("[TCP] Disconnected. Reconnecting...");
    client.stop();
    isConnectedToServer = false;
    connectToServer();
    return;
  }

  int carico = analogRead(fotoR);
  Serial.print("[Sensor] Raw reading: ");
  Serial.println(carico);

  if (carico >= soglia)
  {
    stato = 0;
  }
  else
  {
    stato = 1;
  }

  // Create JSON message
  StaticJsonDocument<200> doc;
  doc["type"] = "sensor_data";
  doc["state"] = stato;
  doc["sensor_value"] = carico;
  doc["threshold"] = soglia; // Fixed typo: was "sogila"
  doc["timestamp"] = millis();
  doc["message_id"] = messagesSent + 1;

  // Convert to string and send
  String jsonString;
  serializeJson(doc, jsonString);
  client.println(jsonString);

  messagesSent++;
  Serial.print("[TCP] Data sent: ");
  Serial.println(jsonString);
  Serial.print("[TCP] Sensor state: ");
  Serial.println(stato);
}

void setup()
{
  Serial.begin(115200);
  delay(1000);

  Serial.println("=== ESP32 Sensor Starting ===");
  Serial.println("Client Name: " + clientNameIs);
  Serial.println("Client ID: " + String(client_id));
  Serial.println("Target Server: " + String(server_ip) + ":" + String(server_port));

  connectToWiFi();
  connectToServer();
  pinMode(fotoR, INPUT);

  Serial.println("=== Setup Complete ===");
}

void loop()
{
  unsigned long currentTime = millis();

  // Send data every sendInterval
  if (currentTime - lastSendTime >= sendInterval)
  {
    sendData();
    lastSendTime = currentTime;
  }

  delay(100); // Small delay to prevent overwhelming the loop
}
