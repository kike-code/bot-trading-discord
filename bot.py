import ccxt
import pandas as pd
import time
import requests
import matplotlib.pyplot as plt
import os
from datetime import datetime
import pytz

# --- INICIO DE LA CONFIGURACIÓN ---
DISCORD_WEBHOOK_URL = 'https://discord.com/api/webhooks/1389770196461420674/rhjPM_p8MHQzrbqIFcc_q2MKoGLqKxX0ZuYe7yID6A1Hecevxzridiu24KQ_9DuzqrSd'
# ¡NUEVO! Pega aquí tu clave de CryptoPanic
CRYPTO_PANIC_API_KEY = '46b4a29bc895049eafe9dde2eeae5d00bac52f84'

# 1. GESTIÓN DE CAPITAL Y RIESGO
CAPITAL_INICIAL_USDT = 20.0
RIESGO_POR_OPERACION_PORCENTAJE = 5 

# 2. LISTA DE CRIPTOMONEDAS
LISTA_DE_SIMBOLOS = [
    'BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'DOGEUSDT', 'BNBUSDT', 
    'ADAUSDT', 'LINKUSDT', 'AVAXUSDT', 'MATICUSDT', 'LTCUSDT', 'SUIUSDT'
]

# 3. CONFIGURACIÓN DE ESTRATEGIA
TEMPORALIDAD = '30m'
INTERVALO_REVISION_SEGUNDOS = 300 
ESTRATEGIA_ACTIVA = 'MA_CROSS'
MA_CROSS_RAPIDA = 20
MA_CROSS_LENTA = 50
RATIO_RIESGO_BENEFICIO = 1.5
VELAS_PARA_SL = 10
# --- FIN DE LA CONFIGURACIÓN ---


# ¡NUEVA FUNCIÓN PARA LEER NOTICIAS!
def obtener_sentimiento_noticias(simbolo):
    """Consulta la API de CryptoPanic para obtener el sentimiento de las noticias."""
    if CRYPTO_PANIC_API_KEY.startswith('PON_AQUI'):
        print("Advertencia: API Key de CryptoPanic no configurada. Se ignorará el filtro de noticias.")
        return 0 # Devuelve un sentimiento neutral si no hay clave

    # Extraemos la moneda del par (ej. de 'BTCUSDT' a 'BTC')
    moneda = simbolo.replace('USDT', '')
    
    url = f"https://cryptopanic.com/api/v1/posts/?auth_token={CRYPTO_PANIC_API_KEY}&currencies={moneda}&public=true"
    
    try:
        respuesta = requests.get(url, timeout=10).json()
        
        sentimiento = 0
        if respuesta and 'results' in respuesta and len(respuesta['results']) > 0:
            # Calculamos un puntaje simple basado en las últimas 5 noticias
            for i, post in enumerate(respuesta['results']):
                if i >= 5: break # Solo consideramos las 5 más recientes
                if post['votes']['bullish'] > post['votes']['bearish']:
                    sentimiento += 1
                elif post['votes']['bearish'] > post['votes']['bullish']:
                    sentimiento -= 1
            
            if sentimiento > 0: print(f"Noticias para {moneda}: Positivas (Puntaje: {sentimiento})")
            elif sentimiento < 0: print(f"Noticias para {moneda}: Negativas (Puntaje: {sentimiento})")
            else: print(f"Noticias para {moneda}: Neutrales (Puntaje: {sentimiento})")
            return sentimiento
        else:
            print(f"No se encontraron noticias recientes para {moneda}.")
            return 0 # Neutral si no hay noticias
    except Exception as e:
        print(f"Error al consultar CryptoPanic: {e}")
        return 0 # Neutral si hay un error en la API

def chequear_estrategia_ma_cross(df, simbolo):
    global estados_bot
    df['MA_Rapida'] = df['close'].rolling(window=MA_CROSS_RAPIDA).mean()
    df['MA_Lenta'] = df['close'].rolling(window=MA_CROSS_LENTA).mean()
    ultima = df.iloc[-1]
    penultima = df.iloc[-2]
    estado_simbolo = estados_bot.setdefault(simbolo, {})

    tipo_señal = None
    if penultima['MA_Rapida'] <= penultima['MA_Lenta'] and ultima['MA_Rapida'] > ultima['MA_Lenta']:
        if estado_simbolo.get('ultima_señal') != 'COMPRA': tipo_señal = 'COMPRA'
    elif penultima['MA_Rapida'] >= penultima['MA_Lenta'] and ultima['MA_Rapida'] < ultima['MA_Lenta']:
        if estado_simbolo.get('ultima_señal') != 'VENTA': tipo_señal = 'VENTA'

    if tipo_señal:
        # --- ¡NUEVO FILTRO DE NOTICIAS! ---
        sentimiento_noticias = obtener_sentimiento_noticias(simbolo)
        
        if tipo_señal == 'COMPRA' and sentimiento_noticias < 0:
            print(f"Señal de COMPRA para {simbolo} ignorada por sentimiento de noticias negativo.")
            return # Cancela el envío de la alerta
        
        if tipo_señal == 'VENTA' and sentimiento_noticias > 0:
            print(f"Señal de VENTA para {simbolo} ignorada por sentimiento de noticias positivo.")
            return # Cancela el envío de la alerta
        
        # Si pasamos el filtro, actualizamos el estado y enviamos la alerta
        estado_simbolo['ultima_señal'] = tipo_señal
        enviar_mensaje_completo(df, simbolo, tipo_señal, "MA_CROSS")

# El resto de funciones (generar_y_guardar_grafico, enviar_alerta_discord, enviar_mensaje_completo) y el BUCLE PRINCIPAL no cambian...
# (Se omiten por brevedad, pero debes usar el código completo de la versión anterior para estas funciones)
# ... (Pega aquí el resto de tu código: generar_y_guardar_grafico, enviar_alerta_discord, enviar_mensaje_completo y el Bucle Principal) ...
