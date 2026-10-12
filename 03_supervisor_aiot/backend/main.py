"""
===============================================================================
 @file main.py
 @brief Supervisor Centinela AIoT - Cava de Crianza en Barricas
 @author María Cristina Maza
 @date 2026-10-11
 @stack Python, Firebase Admin SDK, Google GenAI (Gemini SDK)
 @description Listener reactivo de Firebase RTDB para auditoría continua del microclima
              y generación de informes estructurados en JSON con IA para mitigación autónoma.
===============================================================================
"""

import os
import json
import asyncio
import firebase_admin
from firebase_admin import credentials, db
from google import genai
from dotenv import load_dotenv

# 0. Carga de variables de entorno locales (lee el archivo .env oculto)
load_dotenv()

# ---------------------------------------------------------------------------
# 1. CONFIGURACIÓN DE CREDENCIALES Y SERVICIOS
# ---------------------------------------------------------------------------
# La clave no está hardcodeada; se inyecta de forma segura desde el entorno
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("¡Error de configuración! No se encontró la GEMINI_API_KEY en el entorno local.")

ai_client = genai.Client(api_key=GEMINI_API_KEY)

PATH_CRED = os.path.join(os.path.dirname(__file__), "secrets", "serviceAccountKey.json")

cred = credentials.Certificate(PATH_CRED)
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://iot-ies9010-telemetria-6c692-default-rtdb.firebaseio.com/'
})

# ---------------------------------------------------------------------------
# 2. CAPA COGNITIVA: ASISTENTE ENOLÓGICO CON SALIDA JSON ESTRUCTURADA
# ---------------------------------------------------------------------------
async def evaluar_microclima_cava(temperatura: float, humedad: float):
    print(f"\n[SUPERVISIÓN COGNITIVA] Evaluando microclima de Cava: {temperatura} °C | {humedad} % HR...")

    prompt = f"""
    Eres el Sommelier Cognitivo y Agente de Control Microclimático para la Cava de Crianza en Barricas.
    
    Condiciones óptimas de crianza:
    - Temperatura: 12.0 °C a 18.0 °C
    - Humedad Relativa: 65.0 % a 80.0 %

    Telemetría perimetral actual:
    - Temperatura: {temperatura} °C
    - Humedad: {humedad} %

    Devuelve EXCLUSIVAMENTE un objeto JSON con la siguiente estructura (sin formato Markdown adicional):
    {{
      "alerta_calidad": "DESCRIPCIÓN_BREVE_DEL_RIESGO",
      "forzar_climatizacion": true_o_false,
      "impacto_enologico": "EXPLICACIÓN_TÉCNICA_DEL_IMPACTO_EN_LAS_BARRICAS"
    }}
    """

    max_intentos = 3
    for intento in range(1, max_intentos + 1):
        try:
            print(f"[IA COGNITIVA] Consultando Gemini 3.8 Flash (Intento {intento}/{max_intentos})...")
            
            response = ai_client.models.generate_content(
                model="gemini-3.8-flash",
                contents=prompt
            )

            # Limpieza del texto recibido para garantizar parsing JSON
            raw_text = response.text.replace("```json", "").replace("```", "").strip()
            dict_respuesta = json.loads(raw_text)

            print("=" * 60)
            print("[RESPUESTA ESTRUCTURADA GEMINI - CAVA DE CRIANZA]:")
            print(json.dumps(dict_respuesta, indent=2, ensure_ascii=False))
            print("=" * 60)

            # Inyectar mitigación autónoma en Firebase
            necesita_climatizacion = dict_respuesta.get("forzar_climatizacion", False)
            
            ref_control = db.reference("bodega/zona_crianza/control/forzar_climatizacion")
            ref_control.set(necesita_climatizacion)
            
            ref_informe = db.reference("bodega/zona_crianza/informe_enologico")
            ref_informe.set(dict_respuesta)

            print(f"[ACCION AUTÓNOMA] Mitigación actualizada en Firebase: forzar_climatizacion = {necesita_climatizacion}")
            break

        except Exception as e:
            print(f"[ERROR IA] Intento {intento} falló: {e}")
            if intento < max_intentos:
                await asyncio.sleep(2)

# ---------------------------------------------------------------------------
# 3. LISTENER DE TELEMETRÍA DE LA BODEGA
# ---------------------------------------------------------------------------
def listener_cava(event):
    data = event.data
    if data and isinstance(data, dict):
        temp = data.get("temperatura", 15.0)
        hum = data.get("humedad", 70.0)

        print(f"[TELEMETRÍA CAVA] Temp: {temp} °C | Humedad: {hum} %")

        # Disparo de contingencia fuera de ventana operativa:
        if temp > 22.0 or hum < 60.0:
            print("[ALERTA OPERATIVA] Telemetría fuera de la ventana óptima de crianza.")
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(evaluar_microclima_cava(temp, hum))
            except RuntimeError:
                asyncio.run(evaluar_microclima_cava(temp, hum))
        elif temp <= 18.0 and hum >= 65.0:
            # Normalización automática
            print("[ESTADO ÓPTIMO] Cava dentro de rango. Desactivando climatización de contingencia...")
            db.reference("bodega/zona_crianza/control/forzar_climatizacion").set(False)
            
            informe_normal = {
                "alerta_calidad": "Sin desvíos (Microclima estable)",
                "forzar_climatizacion": False,
                "impacto_enologico": "Las barricas se encuentran en la ventana óptima de crianza. Evolución armónica."
            }
            db.reference("bodega/zona_crianza/informe_enologico").set(informe_normal)

# ---------------------------------------------------------------------------
# 4. PUNTO DE ENTRADA
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("------------------------------------------------------------------")
    print("Iniciando Centinela Supervisor AIoT - Cava de Crianza en Barricas")
    print("Escuchando ruta: /bodega/zona_crianza/ambiente")
    print("------------------------------------------------------------------")
    
    ref = db.reference("bodega/zona_crianza/ambiente")
    ref.listen(listener_cava)