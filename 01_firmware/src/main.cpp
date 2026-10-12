/*******************************************************************************
 * @file main.cpp
 * @brief Firmware perimetral ESP32 - Cava de Crianza en Barricas
 * @author María Cristina Maza
 * @date 2026-10-11
 * @stack ESP32 DevKit V1, Arduino Core, DHT22, Streaming SSE (Cero Polling)
 * @description Ingesta perimetral de temperatura y humedad (PATCH 5s) y recepción
 *              reactiva de comandos de climatización con confirmación (ACK) en GPIO 2.
 ******************************************************************************/

#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <WiFiClientSecure.h>
#include <DHT.h>
#include <ArduinoJson.h>

// --- Credenciales de Red ---
const char *ssid = "Wokwi-GUEST";
const char *password = "";

// --- Endpoints de Firebase (Ruta del Trabajo Final) ---
const String RTDB_URL = "https://iot-ies9010-telemetria-6c692-default-rtdb.firebaseio.com/bodega/zona_crianza";
const String TELEMETRIA_PATH = RTDB_URL + "/ambiente.json";
// Firebase RTDB soporta streaming SSE añadiendo .json?print=silent o mediante streams dedicados
const String STREAM_CONTROL_PATH = RTDB_URL + "/control/forzar_climatizacion.json";
const String ACK_PATH = RTDB_URL + "/extractor_confirmado.json";

// --- Asignación de Hardware ---
#define DHTPIN 4
#define DHTTYPE DHT22
#define RELAY_PIN 2 // LED onboard simulando el climatizador/extractor

DHT dht(DHTPIN, DHTTYPE);

// --- Temporizadores No Bloqueantes (millis) solo para Telemetría ---
unsigned long lastTelemetryTime = 0;
const unsigned long telemetryInterval = 5000; // Enviar telemetría cada 5 segundos

bool lastKnownState = false;

// Cliente HTTP seguro global para mantener la conexión de streaming abierta
WiFiClientSecure secureClient;
HTTPClient httpStream;

// Tarea 1: Envío de Telemetría Periódica (Edge ➔ Cloud)
void enviarTelemetria()
{
  float h = dht.readHumidity();
  float t = dht.readTemperature();
  if (isnan(h) || isnan(t))
  {
    Serial.println("[ERROR] Falla en la lectura del sensor DHT22 (isnan detectado).");
    return;
  }

  WiFiClientSecure client;
  client.setInsecure();
  HTTPClient https;

  if (https.begin(client, TELEMETRIA_PATH))
  {
    https.addHeader("Content-Type", "application/json");

    String payload = "{\"temperatura\":" + String(t, 1) +
                     ",\"humedad\":" + String(h, 1) +
                     ",\"dispositivo_id\":\"esp32_cava_crianza\"}";

    int httpCode = https.PATCH(payload);
    if (httpCode > 0)
    {
      Serial.printf("[TELEMETRÍA] Enviada: %.1f °C | %.1f %%\n", t, h);
    }
    else
    {
      Serial.printf("[HTTP ERROR] Falló PATCH telemetría: %s\n", https.errorToString(httpCode).c_str());
    }
    https.end();
  }
}

// Función auxiliar para enviar el Acknowledge físico (Lazo Cerrado)
void enviarAcknowledge(bool estadoFisico)
{
  WiFiClientSecure client;
  client.setInsecure();
  HTTPClient httpsAck;

  if (httpsAck.begin(client, ACK_PATH))
  {
    httpsAck.addHeader("Content-Type", "application/json");
    int ackCode = httpsAck.PUT(estadoFisico ? "true" : "false");
    if (ackCode > 0)
    {
      Serial.println("[ACK] Confirmación de hardware sincronizada con éxito en Firebase.");
    }
    httpsAck.end();
  }
}

// Inicialización de la conexión de Streaming HTTP (Server-Sent Events)
void iniciarStreamingControl()
{
  secureClient.setInsecure();
  Serial.println("[STREAMING] Abriendo canal persistente SSE con Firebase...");
  
  if (httpStream.begin(secureClient, STREAM_CONTROL_PATH))
  {
    // Cabecera obligatoria para solicitar Server-Sent Events (Streaming en tiempo real)
    httpStream.addHeader("Accept", "text/event-stream");
    int httpCode = httpStream.GET();
    
    if (httpCode == HTTP_CODE_OK)
    {
      Serial.println("[STREAMING] Canal de eventos abierto correctamente (Cero Polling activo).");
    }
    else
    {
      Serial.printf("[STREAMING ERROR] Código de apertura fallido: %d\n", httpCode);
    }
  }
}

// Tarea 2: Procesamiento del Stream de Eventos (Recepción Reactiva Cloud ➔ Edge)
void escucharEventosStreaming()
{
  // Verificamos si hay datos disponibles en el flujo continuo de la conexión abierta
  if (httpStream.connected() && secureClient.available())
  {
    String line = httpStream.getStreamPtr()->readStringUntil('\n');
    
    // Firebase Realtime Database envía eventos SSE con el prefijo "data: "
    if (line.startsWith("data:"))
    {
      String jsonData = line.substring(5);
      jsonData.trim();

      // Si el valor recibido no es nulo, evaluamos la orden
      if (jsonData != "null" && jsonData.length() > 0)
      {
        bool ordenEncendido = (jsonData == "true");

        // Actuamos únicamente si hay un cambio real respecto al estado actual
        if (ordenEncendido != lastKnownState)
        {
          lastKnownState = ordenEncendido;
          digitalWrite(RELAY_PIN, ordenEncendido ? HIGH : LOW);
          Serial.printf("[EVENTO PUSH] Actuador GPIO 2 conmutado a: %s\n", ordenEncendido ? "HIGH (ENCENDIDO)" : "LOW (APAGADO)");

          // Despachar inmediatamente el Acknowledge exigido por la rúbrica
          enviarAcknowledge(ordenEncendido);
        }
      }
    }
  }
  else
  {
    // Si la conexión de streaming se interrumpe por timeout de la red, la reiniciamos de forma transparente
    Serial.println("[STREAMING] Reconectando canal de eventos...");
    httpStream.end();
    iniciarStreamingControl();
    delay(1000);
  }
}

void setup()
{
  Serial.begin(115200);

  // Configuración del pin del actuador (LED onboard / Relé)
  pinMode(RELAY_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, LOW);

  dht.begin();

  Serial.print("\n[RED] Conectando a Wi-Fi Wokwi-GUEST");
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED)
  {
    delay(200);
    Serial.print(".");
  }
  Serial.println("\n[RED] Conexión establecida con éxito.");
  Serial.print("[RED] Dirección IP asignada: ");
  Serial.println(WiFi.localIP());

  // Iniciar el canal de streaming persistente de eventos
  iniciarStreamingControl();
}

void loop()
{
  unsigned long currentMillis = millis();

  // Ciclo 1: Ingesta periódica de telemetría cada 5 segundos (PATCH)
  if (currentMillis - lastTelemetryTime >= telemetryInterval)
  {
    lastTelemetryTime = currentMillis;
    enviarTelemetria();
  }

  // Ciclo 2: Escucha permanente del stream de eventos (Cero polling, reactivo por eventos)
  escucharEventosStreaming();
}