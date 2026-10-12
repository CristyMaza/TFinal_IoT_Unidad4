## Cava de Crianza en Barricas — Sistema AIoT Autónomo

Sistema inteligente de supervisión y control microclimático para bodegas, desarrollado bajo una arquitectura orientada a eventos, integración con Inteligencia Artificial generativa y la filosofía de "cero polling".

---

## Arquitectura del Sistema y Stack Tecnológico

El proyecto implementa un flujo de datos distribuido en tiempo real que conecta el borde físico con la nube y servicios cognitivos:

1. **Capa Periférica (Edge):** 
   * **ESP32 DevKit V1** programado en C++ (Arduino Core) con PlatformIO.
   * Sensor **DHT22** para adquisición de temperatura y humedad ambiental.
   * Actuador simulado en **GPIO 2** (LED indicador de climatizador/extractor).
   * **Temporización no bloqueante (`millis()`)** e ingesta periódica de telemetría cada 5 segundos mediante peticiones `HTTPS PATCH`.
   * **Recepción Reactiva por Streaming (SSE / HTTP Streaming):** Canal persistente con cabecera `Accept: text/event-stream` para conmutar el actuador por evento push sin consultas cíclicas.
   * **Lazo Cerrado con Acknowledge:** Despacho inmediato de confirmación física (`HTTPS PUT`) para garantizar que la interfaz web solo refleje el estado real tras la conmutación del hardware.

2. **Capa Middleware (Cloud):**
   * **Google Firebase Realtime Database:** Base de datos NoSQL organizada bajo la ruta `/bodega/zona_crianza/`.

3. **Capa de Supervisión Cognitiva (Backend):**
   * Script en **Python** actúando como centinela en segundo plano (listener asíncrono).
   * Integración con **Google Gemini API** (modelo Gemini Flash) para razonamiento contextualizado como sommelier experto, generando dictámenes en formato JSON estructurado (`alerta_calidad`, `forzar_climatizacion`, `impacto_enologico`).

4. **Capa de Presentación (Frontend):**
   * **Dashboard Web (HTML5 + CSS3 + JS Modular):** Interfaz visual nocturna con enlace a Firebase mediante WebSockets (`onValue`) para visualización en tiempo real y control manual bajo el principio de *Acknowledge*.

---

## Estructura del Repositorio

El proyecto se encuentra modularizado de la siguiente manera:

```text
cava-de-crianza-aiot/
│
├── 01_firmware/
│   ├── src/
│   │   └── main.cpp          # Código fuente del ESP32 con streaming SSE
│   ├── platformio.ini        # Configuración de entorno, placa esp32dev y librerías
│   └── wokwi.toml            # Configuración del simulador Wokwi
│
├── 02_frontend/
│   └── panel.html            # Dashboard web interactivo (Firebase SDK Modular)
│
├── 03_supervisor_aiot/
│   ├── secrets/
│   │   └── serviceAccountKey.json  # Credenciales de Firebase (privado/excluido)
│   ├── main.py               # Centinela de Python con integración a Gemini IA
│   └── requirements.txt      # Dependencias de Python (firebase-admin, google-genai)
│
├── diagram.json              # Esquema de conexiones para Wokwi (ESP32 + DHT22 + LED)
└── README.md                 # Documentación técnica del proyecto


## Autoría
María Cristina Maza
Institución: IES 9-010 • Actualización Académica en Desarrollo de Software para IA y Blockchain