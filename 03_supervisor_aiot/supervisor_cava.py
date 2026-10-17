"""
===============================================================================
 @file supervisor_cava.py
 @brief Supervisor Centinela AIoT - Cava de Crianza en Barricas
 @author María Cristina Maza
 @date 2026-10-11
 @stack Python 3, Firebase Admin SDK, Google GenAI (Gemini SDK)
 @description Monitoreo continuo del microclima e invoca a Gemini para la mitigación
              autónoma de contingencias microclimáticas en barricas.
===============================================================================
"""

import os
import json
import asyncio
import firebase_admin
from firebase_admin import credentials, db
from google import genai
from dotenv import load_dotenv

# Carga de variables de entorno
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("¡Error de configuración! No se encontró GEMINI_API_KEY en el entorno.")

ai_client = genai.Client(api_key=GEMINI_API_KEY)

PATH_CRED = os.path.join(os.path.dirname(__file__), "secrets", "serviceAccountKey.json")
cred = credentials.Certificate(PATH_CRED)
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://iot-ies9010-telemetria-6c692-default-rtdb.firebaseio.com/'
})

# ---------------------------------------------------------------------------
# CAPA COGNITIVA CON GEMINI 3.8 FLASH
# ---------------------------------------------------------------------------
async def evaluar_microclima_cava(temperatura: float, humedad: float):
    print(f"\n[SUPERVISIÓN COGNITIVA] Evaluando microclima: {temperatura} °C | {humedad} % HR...")

    prompt = f"""
    Eres el Sommelier Cognitivo y Agente de Control Microclimático para la Cava de Crianza en Barricas.
    
    Condiciones óptimas de crianza:
    - Temperatura: 12.0 °C a 18.0 °C
    - Humedad Relativa: 65.0 % a 80.0 %

    Telemetría perimetral actual:
    - Temperatura: {temperatura} °C
    - Humedad: {humedad} %

    Devuelve EXCLUSIVAMENTE un objeto JSON estricto con las siguientes tres claves (sin formato Markdown adicional):
    {{
      "alerta_calidad": true,
      "forzar_climatizacion": true,
      "impacto_enologico": "Explicación técnica en una sola frase del riesgo para el vino y las duelas de madera de las barricas."
    }}
    
    Nota: 'alerta_calidad' y 'forzar_climatizacion' DEBEN ser valores booleanos (true o false).
    """

    max_intentos = 3
    for intento in range(1, max_intentos + 1):
        try:
            print(f"[IA COGNITIVA] Consultando gemini-3.8-flash (Intento {intento}/{max_intentos})...")
            
            response = ai_client.models.generate_content(
                model="gemini-3.8-flash",
                contents=prompt
            )

            raw_text = response.text.replace("```json", "").replace("```", "").strip()
            dict_respuesta = json.loads(raw_text)

            print("=" * 60)
            print("[RESPUESTA ESTRUCTURADA GEMINI - CAVA DE CRIANZA]:")
            print(json.dumps(dict_respuesta, indent=2, ensure_ascii=False))
            print("=" * 60)

            necesita_climatizacion = dict_respuesta.get("forzar_climatizacion", False)
            
            # 1. Inyecta la orden en el actuador
            ref_actuador = db.reference("bodega/zona_crianza/actuadores/extractor_estado")
            ref_actuador.set(necesita_climatizacion)
            
            # 2. Registra el diagnóstico en auditoria_ia
            ref_auditoria = db.reference("bodega/zona_crianza/auditoria_ia")
            ref_auditoria.set(dict_respuesta)

            print(f"[ACCIÓN AUTÓNOMA] Sincronizado en Firebase: extractor_estado = {necesita_climatizacion}")
            break

        except Exception as e:
            print(f"[ERROR IA] Intento {intento} falló: {e}")
            if intento < max_intentos:
                await asyncio.sleep(2)

# ---------------------------------------------------------------------------
# LISTENER Y MITIGACIÓN EN TIEMPO REAL
# ---------------------------------------------------------------------------
def listener_cava(event):
    data = event.data
    if data and isinstance(data, dict):
        temp = data.get("temperatura", 15.0)
        hum = data.get("humedad", 70.0)

        print(f"[TELEMETRÍA CAVA] Temp: {temp} °C | Humedad: {hum} %")

        # Disparador de Contingencia Enológica: T > 22.0 °C o HR < 60.0 %
        if temp > 22.0 or hum < 60.0:
            print("[ALERTA OPERATIVA] Salida de ventana operativa detectada.")
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(evaluar_microclima_cava(temp, hum))
            except RuntimeError:
                asyncio.run(evaluar_microclima_cava(temp, hum))

        # Restablecimiento al retornar a rango seguro (12 a 18 °C y 65 a 80 % HR)
        elif 12.0 <= temp <= 18.0 and 65.0 <= hum <= 80.0:
            print("[ESTADO ÓPTIMO] Retorno a rango seguro. Retirando orden de climatización...")
            db.reference("bodega/zona_crianza/actuadores/extractor_estado").set(False)
            
            informe_normal = {
                "alerta_calidad": False,
                "forzar_climatizacion": False,
                "impacto_enologico": "Las barricas se encuentran en la ventana óptima de crianza. Evolución armónica."
            }
            db.reference("bodega/zona_crianza/auditoria_ia").set(informe_normal)

if __name__ == "__main__":
    print("------------------------------------------------------------------")
    print("Iniciando Supervisor Cava AIoT (supervisor_cava.py)")
    print("Escuchando ruta: /bodega/zona_crianza/ambiente")
    print("------------------------------------------------------------------")
    
    ref = db.reference("bodega/zona_crianza/ambiente")
    ref.listen(listener_cava)