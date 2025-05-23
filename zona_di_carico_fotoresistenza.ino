#include <WiFi.h>
#include <WiFiClient.h>

const int fotoR = 34;
const int soglia = 400;
int stato;

//data del router
const char* ssid = "TP-Link_WE66";
const char* password = "123456789";

// TCP server settings
const char* server_ip = "192.168.100.150"; // questo e' l'IP del nostro server
const uint16_t server_port = 5555;
const char* client_id = "ESP_Carico";

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
  Serial.println(analogRead(fotoR));
  
  //Serial.print("[TCP] Carico letto: ");
  //Serial.println(carico);

  //int stato = (carico >= soglia) ? 1 : 0;

  
if (carico >= soglia) {
  stato = 1;
} else {
  stato = 0;
}

  // invio in formato semplice e leggibile
  client.println(String(stato));
  Serial.print("[TCP] Stato inviato: ");
  Serial.println(stato);
  stato = 0;
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
  delay(1000); // invio ogni secondo
}