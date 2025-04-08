#include <WiFi.h>

const char* ssid = "sussymg";
const char* password = "123456789";

const char* serverIP = "192.168.146.136";  // Replace with your server's IP
const int serverPort = 5555;     // Replace with your server's port

// Define your matrix here (example 3x4 matrix)
const int matrix[3][4] = {
  {1, 0, 1, 0},
  {0, 1, 0, 1},
  {1, 1, 0, 0}
};
const int rows = 3;
const int cols = 4;

WiFiClient client;

void sendMatrix() {
  if (!client.connected()) return;
  
  // Send matrix header
  client.print("MATRIX_START:");
  client.print(rows);
  client.print("x");
  client.print(cols);
  client.println();
  
  // Send matrix data
  for (int i = 0; i < rows; i++) {
    for (int j = 0; j < cols; j++) {
      client.print(matrix[i][j]);
      if (j < cols - 1) client.print(","); // Separate elements with comma
    }
    client.println(); // New line for each row
  }
  
  // Send matrix footer
  client.println("MATRIX_END");
  Serial.println("Matrix sent to server");
}

void setup() {
  Serial.begin(115200);
  
  // Connect to WiFi
  WiFi.begin(ssid, password);
  
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  
  Serial.println("\nConnected to WiFi");
  Serial.print("IP Address: ");
  Serial.println(WiFi.localIP());

  // Connect to TCP server
  Serial.print("Connecting to server...");
  if (client.connect(serverIP, serverPort)) {
    Serial.println("Connected to server!");
    sendMatrix(); // Send the matrix immediately after connection
  } else {
    Serial.println("Connection failed!");
  }
}

void loop() {
  // Check for incoming data
  if (client.available()) {
    String line = client.readStringUntil('\n');
    Serial.print("Received: ");
    Serial.println(line);
  }
  
  // Send matrix periodically (example: every 5 seconds)
  static unsigned long lastSend = 0;
  if (millis() - lastSend > 5000) {
    lastSend = millis();
    if (client.connected()) {
      sendMatrix();
    }
  }
  
  // Check if connection is still alive
  if (!client.connected()) {
    Serial.println("Disconnected from server. Attempting to reconnect...");
    client.stop();
    if (client.connect(serverIP, serverPort)) {
      Serial.println("Reconnected to server!");
      sendMatrix(); // Send matrix after reconnection
    } else {
      Serial.println("Reconnection failed!");
    }
    delay(1000);
  }
}
