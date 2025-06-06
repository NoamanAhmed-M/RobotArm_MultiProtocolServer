#include <WiFi.h>
#include <WiFiClient.h>
#include <ArduinoJson.h>

String clientNameIs = "Stazione di prelievo";

const int fotoR = 33;
const int soglia = 400;
int stato;

// WiFi credentials
const char *ssid = "ITS Academy Udine Guests";
const char *password = "!MV5rP2xka";

// TCP server settings
const char *server_ip = "10.65.102.103";
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
int wifiRetryCount = 0;
const int maxWifiRetries = 10;

void connectToWiFi()
{
  Serial.print("[WiFi] Connecting to ");
  Serial.print(ssid);

  WiFi.begin(ssid, password);
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) // Max 10 seconds
  {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED)
  {
    Serial.println("\n[WiFi] Connected");
    Serial.print("[WiFi] IP address: ");
    Serial.println(WiFi.localIP());
    wifiRetryCount = 0; // Reset retry count on successful connection
  }
  else
  {
    Serial.println("\n[WiFi] Failed to connect");
    wifiRetryCount++;
    
    if (wifiRetryCount >= maxWifiRetries)
    {
      Serial.println("[WiFi] Max retries reached. Restarting " + clientNameIs + "...");
      delay(1000);
      ESP.restart();
    }
    else
    {
      Serial.println("[WiFi] Will retry in 5 seconds...");
      delay(5000);
    }
  }
}

bool connectToServer()
{
  Serial.print("[TCP] Connecting to server... ");
  
  // Clean up any existing connection
  if (client.connected()) {
    client.stop();
  }
  
  if (client.connect(server_ip, server_port))
  {
    Serial.println("Connected");
    
    // Send client ID as plain text first (as expected by server)
    client.print(client_id);
    client.print("\n");  // Add newline to terminate the client ID
    Serial.println("[TCP] Sent client ID: " + String(client_id));

    // Wait a bit for server to process client ID
    delay(100);

    // Send client identification as JSON message
    StaticJsonDocument<200> idDoc;
    idDoc["type"] = "client_id";
    idDoc["client_id"] = client_id;
    idDoc["client_name"] = clientNameIs;
    idDoc["timestamp"] = millis();

    String idJsonString;
    serializeJson(idDoc, idJsonString);
    client.print(idJsonString);
    client.print("\n");  // Ensure newline termination
    Serial.println("[TCP] Sent client ID JSON: " + idJsonString);

    // Wait for server acknowledgment (optional but recommended)
    unsigned long timeout = millis() + 3000; // 3 second timeout
    while (!client.available() && millis() < timeout) {
      delay(10);
    }
    
    if (client.available()) {
      String response = client.readStringUntil('\n');
      Serial.println("[TCP] Server response: " + response);
    }

    // Send initial connection message
    StaticJsonDocument<200> doc;
    doc["type"] = "connection";
    doc["message"] = "ESP32_Sensor connected";
    doc["reconnect_count"] = reconnectCount;
    doc["uptime"] = millis();
    doc["client_name"] = clientNameIs;

    String jsonString;
    serializeJson(doc, jsonString);
    client.print(jsonString);
    client.print("\n");  // Ensure newline termination
    Serial.println("[TCP] Sent connection message: " + jsonString);

    isConnectedToServer = true;
    reconnectCount++;
    lastReconnectAttempt = millis(); // Update reconnect timing
    return true;
  }
  else
  {
    Serial.println("Failed to connect to server.");
    isConnectedToServer = false;
    lastReconnectAttempt = millis(); // Update reconnect timing
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

  // Check TCP connection with reconnect interval
  if (!client.connected())
  {
    unsigned long currentTime = millis();
    if (currentTime - lastReconnectAttempt >= reconnectInterval)
    {
      Serial.println("[TCP] Disconnected. Reconnecting...");
      client.stop();
      isConnectedToServer = false;
      connectToServer();
    }
    return;
  }

  int carico = analogRead(fotoR);
  Serial.print("[Sensor] Raw reading: ");
  Serial.println(carico);

  // Determine state based on threshold
  if (carico >= soglia)
  {
    stato = 1; // High light level (not covered)
  }
  else
  {
    stato = 0; // Low light level (covered/blocked)
  }

  // Create JSON message
  StaticJsonDocument<300> doc;  // Increased size for safety
  doc["type"] = "sensor_data";
  doc["state"] = stato;
  doc["sensor_value"] = carico;
  doc["threshold"] = soglia;
  doc["timestamp"] = millis();
  doc["message_id"] = messagesSent + 1;
  doc["client_name"] = clientNameIs;
  doc["client_id"] = client_id;  // Add client_id for consistency

  // Convert to string and send
  String jsonString;
  serializeJson(doc, jsonString);
  
  // Send with proper termination
  client.print(jsonString);
  client.print("\n");  // Ensure newline termination
  
  // Check if send was successful
  if (!client.connected()) {
    Serial.println("[TCP] Connection lost during send");
    isConnectedToServer = false;
    return;
  }
  
  messagesSent++;
  Serial.print("[TCP] Data sent: ");
  Serial.println(jsonString);
  Serial.print("[TCP] Sensor state: ");
  Serial.println(stato == 1 ? "CLEAR" : "BLOCKED");
  Serial.print("[TCP] Messages sent: ");
  Serial.println(messagesSent);
}

void setup()
{
  Serial.begin(115200);
  delay(1000);

  Serial.println("=== ESP32 Sensor Starting ===");
  Serial.println("Client Name: " + clientNameIs);
  Serial.println("Client ID: " + String(client_id));
  Serial.println("Target Server: " + String(server_ip) + ":" + String(server_port));
  Serial.println("Sensor Threshold: " + String(soglia));

  // Set WiFi mode
  WiFi.mode(WIFI_STA);
  
  // Configure photoresistor pin
  pinMode(fotoR, INPUT);

  // Connect to WiFi with retry logic
  while (WiFi.status() != WL_CONNECTED && wifiRetryCount < maxWifiRetries)
  {
    connectToWiFi();
  }

  // Connect to server
  if (WiFi.status() == WL_CONNECTED)
  {
    connectToServer();
  }

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

  // Handle any incoming data from server (optional)
  if (client.available())
  {
    String incomingData = client.readStringUntil('\n');
    Serial.println("[TCP] Received: " + incomingData);
  }

  delay(100); // Small delay to prevent overwhelming the loop
}
