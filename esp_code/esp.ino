#include <ESP8266WiFi.h>
#include <ArduinoJson.h>
#include <DHT.h>
#include <Wire.h>
#include <BH1750.h>
#include <ESP8266HTTPClient.h>
#include <WiFiManager.h>
#include <LittleFS.h>

#define DHTPIN D4
#define DHTTYPE DHT11
#define SOIL_PIN A0
#define RELAY_PIN D5
#define SDA_PIN D2
#define SCL_PIN D1

// Global configuration variables
char server_ip[40] = "192.168.1.100";
bool shouldSaveConfig = false;

// Callback notifying us of the need to save config
void saveConfigCallback() {
  Serial.println("Should save config");
  shouldSaveConfig = true;
}

DHT dht(DHTPIN, DHTTYPE);
BH1750 lightMeter;
WiFiClient client;

float moistureThreshold = 50.0;
bool pumpActivated = false;
bool pumpStatus = false;

void setup()
{
    Serial.begin(115200);
    dht.begin();
    Wire.begin();
    lightMeter.begin();
    pinMode(RELAY_PIN, OUTPUT);
    digitalWrite(RELAY_PIN, HIGH);

    // Read configuration from LittleFS
    Serial.println("Mounting FS...");
    if (LittleFS.begin()) {
        Serial.println("Mounted file system");
        if (LittleFS.exists("/config.json")) {
            Serial.println("Reading config file");
            File configFile = LittleFS.open("/config.json", "r");
            if (configFile) {
                size_t size = configFile.size();
                std::unique_ptr<char[]> buf(new char[size]);
                configFile.readBytes(buf.get(), size);
                StaticJsonDocument<200> json;
                DeserializationError error = deserializeJson(json, buf.get());
                if (!error) {
                    Serial.println("Parsed json:");
                    serializeJson(json, Serial);
                    Serial.println();
                    strcpy(server_ip, json["server_ip"] | "192.168.1.100");
                } else {
                    Serial.println("Failed to load json config");
                }
                configFile.close();
            }
        }
    } else {
        Serial.println("Failed to mount FS");
    }

    WiFiManagerParameter custom_server_ip("server", "Server IP", server_ip, 40);

    WiFiManager wifiManager;
    wifiManager.setSaveConfigCallback(saveConfigCallback);
    wifiManager.addParameter(&custom_server_ip);

    // Fetches ssid and pass and tries to connect
    // If it does not connect it starts an access point with the specified name
    Serial.print("Connecting to WiFi...");
    if (!wifiManager.autoConnect("RangerGreen_Setup")) {
        Serial.println("Failed to connect and hit timeout");
        delay(3000);
        ESP.restart();
        delay(5000);
    }

    Serial.println("\n✅ Connected to WiFi!");

    // Read updated parameters
    strcpy(server_ip, custom_server_ip.getValue());

    // Save the custom parameters to FS if they changed
    if (shouldSaveConfig) {
        Serial.println("Saving config");
        StaticJsonDocument<200> json;
        json["server_ip"] = server_ip;

        File configFile = LittleFS.open("/config.json", "w");
        if (!configFile) {
            Serial.println("Failed to open config file for writing");
        } else {
            serializeJson(json, Serial);
            serializeJson(json, configFile);
            configFile.close();
        }
    }
}

void loop()
{
    readAndProcessSensors();
    fetchMoistureThreshold();
    delay(3000);
}

void readAndProcessSensors()
{
    float temperature = dht.readTemperature();
    float humidity = dht.readHumidity();
    float lightIntensity = lightMeter.readLightLevel();
    int rawSoilMoisture = analogRead(SOIL_PIN);

    float soilMoisturePercent = 100.0 - ((rawSoilMoisture / 1023.0) * 100.0);

    // Handle sensor failures
    String tempValue = isnan(temperature) ? "none" : String(temperature, 2);
    String humidityValue = isnan(humidity) ? "none" : String(humidity, 2);
    String lightValue = (lightIntensity < 0) ? "none" : String(lightIntensity, 2);
    String soilValue = (rawSoilMoisture < 0 || rawSoilMoisture > 1023) ? "none" : String(soilMoisturePercent, 2);

    Serial.printf("🌱 Soil Moisture: %s%%\n", soilValue.c_str());
    Serial.printf("🌡 Temperature: %s°C\n", tempValue.c_str());
    Serial.printf("💧 Humidity: %s%%\n", humidityValue.c_str());
    Serial.printf("☀ Light Intensity: %s lux\n", lightValue.c_str());

    float lowerThreshold = moistureThreshold * 0.80;

    if (!pumpActivated)
    {
        if (soilMoisturePercent < moistureThreshold)
        {
            pumpActivated = true;
            Serial.println("✅ Pump control activated after first threshold breach!");
        }
    }
    else
    {
        if (soilMoisturePercent < lowerThreshold)
        {
            digitalWrite(RELAY_PIN, LOW);
            pumpStatus = true;
            Serial.println("🚰 Pump ON! (Soil moisture too low)");
        }
        else if (soilMoisturePercent >= moistureThreshold)
        {
            digitalWrite(RELAY_PIN, HIGH);
            pumpStatus = false;
            Serial.println("❌ Pump OFF! (Moisture threshold reached)");
        }
    }

    sendDataToServer(tempValue, humidityValue, lightValue, soilValue, pumpStatus);
}

void sendDataToServer(String temperature, String humidity, String lightIntensity, String soilMoisture, bool pumpStatus)
{
    if (WiFi.status() == WL_CONNECTED)
    {
        HTTPClient http;
        String serverUrl = String("http://") + server_ip + ":5001/sensor_data";
        http.begin(client, serverUrl);
        http.addHeader("Content-Type", "application/json");

        StaticJsonDocument<200> jsonDoc;
        jsonDoc["temperature"] = temperature;
        jsonDoc["humidity"] = humidity;
        jsonDoc["light_intensity"] = lightIntensity;
        jsonDoc["soil_moisture"] = soilMoisture;
        jsonDoc["pump_status"] = pumpStatus ? "ON" : "OFF";

        String payload;
        serializeJson(jsonDoc, payload);
        int httpResponseCode = http.POST(payload);

        Serial.printf("📡 Sent Data: %s\n", payload.c_str());
        Serial.printf("🌍 Server Response: %d\n", httpResponseCode);
        http.end();
    }
}

void fetchMoistureThreshold()
{
    if (WiFi.status() == WL_CONNECTED)
    {
        HTTPClient http;
        String thresholdUrl = String("http://") + server_ip + ":5001/update_moisture";
        http.begin(client, thresholdUrl);
        int httpResponseCode = http.GET();

        if (httpResponseCode == 200)
        {
            String response = http.getString();
            StaticJsonDocument<200> jsonDoc;
            deserializeJson(jsonDoc, response);
            moistureThreshold = jsonDoc["threshold"];
            Serial.printf("🔄 Updated Moisture Threshold: %.2f%%\n", moistureThreshold);
        }

        http.end();
    }
}
