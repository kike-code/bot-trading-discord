import ccxt
import pandas as pd
# Quitamos la importación de pandas_ta
import time
import requests
import matplotlib.pyplot as plt
import os
from datetime import datetime
import pytz

# --- INICIO DE LA CONFIGURACIÓN ---
# He puesto un placeholder para proteger tu URL. Vuelve a pegar la tuya aquí.
DISCORD_WEBHOOK_URL = 'https://discord.com/api/webhooks/1387958881057116180/wJB5n11JPY2FrUCaYq5_ceanWrFDxF2JYIjXHG4cFo_0bigLl8NRwEnTFgZrJo-5qneo'

# ¡LISTA DE MONEDAS AMPLIADA Y CORREGIDA!
LISTA_DE_SIMBOLOS = [
    'BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'DOGEUSDT', 'BNBUSDT', 
    'ADAUSDT', 'LINKUSDT', 'AVAXUSDT', 'MATICUSDT', 'LTCUSDT', 'SUIUSDT',
    'DOTUSDT', 'TRXUSDT', 'SHIBUSDT', 'ETCUSDT', 'BCHUSDT', 'NEARUSDT',
    'FILUSDT', 'APTUSDT', 'OPUSDT', 'ARB_USDT'
]

# ¡TEMPORALIDAD ACTUALIZADA!
TEMPORALIDAD = '30m' # <--- CAMBIADO A 30 MINUTOS
INTERVALO_REVISION_SEGUNDOS = 240 # Revisamos cada 4 minutos

# Parámetros MA_CROSS
MA_CROSS_RAPIDA = 20
MA_CROSS_LENTA = 50

# Parámetros de Riesgo
RATIO_RIESGO_BENEFICIO = 1.5
VELAS_PARA_SL = 10
# --- FIN DE LA CONFIGURACIÓN ---


def generar_y_guardar_grafico(df, simbolo, tipo_señal, precio_señal, sl, tp):
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(10, 6))
    df_reciente = df.tail(100)
    ax.plot(df_reciente.index, df_reciente['close'], label='Precio', color='cyan')
    ax.plot(df_reciente.index, df_reciente['MA_Rapida'], label=f'MA Rápida ({MA_CROSS_RAPIDA})', color='orange', linestyle='--')
    ax.plot(df_reciente.index, df_reciente['MA_Lenta'], label=f'MA Lenta ({MA_CROSS_LENTA})', color='purple', linestyle='--')
    
    ax.axhline(y=tp, color='lime', linestyle='--', label=f'Take Profit ({tp:.4f})')
    ax.axhline(y=precio_señal, color='white', linestyle=':', label=f'Entrada ({precio_señal:.4f})', alpha=0.5)
    ax.axhline(y=sl, color='red', linestyle='--', label=f'Stop Loss ({sl:.4f})')
    
    ax.set_title(f'Análisis de {simbolo} - {TEMPORALIDAD}', fontsize=16)
    ax.set_ylabel('Precio (USDT)')
    ax.legend()
    fig.tight_layout()
    ruta_grafico = f"grafico_{simbolo.replace('/', '_')}.png"
    fig.savefig(ruta_grafico)
    plt.close(fig)
    return ruta_grafico

def enviar_alerta_discord(mensaje, ruta_grafico):
    if DISCORD_WEBHOOK_URL.startswith('PON_AQUI'):
        print("ERROR: Configura tu URL de Webhook de Discord.")
        return
    try:
        with open(ruta_grafico, 'rb') as f:
            files = {'file': (ruta_grafico, f, 'image/png')}
            payload = {'content': mensaje}
            requests.post(DISCORD_WEBHOOK_URL, data=payload, files=files)
    except Exception as e:
        print(f"Error al enviar alerta a Discord: {e}")
    os.remove(ruta_grafico)

def chequear_estrategia_ma_cross(df, simbolo):
    global estados_bot
    
    df['MA_Rapida'] = df['close'].rolling(window=MA_CROSS_RAPIDA).mean()
    df['MA_Lenta'] = df['close'].rolling(window=MA_CROSS_LENTA).mean()
    
    ultima = df.iloc[-1]
    penultima = df.iloc[-2]
    estado_simbolo = estados_bot.setdefault(simbolo, {})

    tipo_señal = None
    if penultima['MA_Rapida'] <= penultima['MA_Lenta'] and ultima['MA_Rapida'] > ultima['MA_Lenta']:
        if estado_simbolo.get('ultima_señal') != 'COMPRA':
            tipo_señal = 'COMPRA'
            estado_simbolo['ultima_señal'] = 'COMPRA'
    elif penultima['MA_Rapida'] >= penultima['MA_Lenta'] and ultima['MA_Rapida'] < ultima['MA_Lenta']:
        if estado_simbolo.get('ultima_señal') != 'VENTA':
            tipo_señal = 'VENTA'
            estado_simbolo['ultima_señal'] = 'VENTA'

    if tipo_señal:
        zona_horaria_bolivia = pytz.timezone('America/La_Paz')
        hora_actual_bolivia = datetime.now(zona_horaria_bolivia)
        hora_formateada = hora_actual_bolivia.strftime('%d-%m-%Y a las %H:%M:%S')

        precio_entrada = ultima['close']
        if tipo_señal == 'COMPRA':
            stop_loss = df['low'].tail(VELAS_PARA_SL).min() * 0.998
            riesgo = precio_entrada - stop_loss
            take_profit = precio_entrada + (riesgo * RATIO_RIESGO_BENEFICIO)
            operacion_texto = "🟢 Operación: Long 🟢"
        else:
            stop_loss = df['high'].tail(VELAS_PARA_SL).max() * 1.002
            riesgo = stop_loss - precio_entrada
            take_profit = precio_entrada - (riesgo * RATIO_RIESGO_BENEFICIO)
            operacion_texto = "🔴 Operación: Short 🔴"
        
        mensaje = (
            f"💡 **Detalle de posición**\n"
            f"-------------------------------------\n"
            f"🗓️ *Señal generada el {hora_formateada} (Hora Bolivia)*\n"
            f"-------------------------------------\n"
            f"🪙 **Token:** {simbolo}\n"
            f"{operacion_texto}\n"
            f".\n"
            f"🎯 **Precio de apertura:** {precio_entrada:.4f} USDT\n"
            f"✋ **Stop Loss (SL):** {stop_loss:.4f} USDT\n"
            f"🤑 **Take Profit (TP):** {take_profit:.4f} USDT"
        )
        
        ruta_grafico = generar_y_guardar_grafico(df, simbolo, tipo_señal, precio_entrada, stop_loss, take_profit)
        enviar_alerta_discord(mensaje, ruta_grafico)

# --- BUCLE PRINCIPAL ---
exchange = ccxt.mexc()
estados_bot = {} 
print("Bot versión simplificada iniciado.")

while True:
    print(f"\n--- Nuevo ciclo ---")
    for simbolo in LISTA_DE_SIMBOLOS:
        try:
            print(f"Analizando {simbolo}...")
            velas = exchange.fetch_ohlcv(simbolo, TEMPORALIDAD, limit=200)
            df = pd.DataFrame(velas, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df.set_index('timestamp', inplace=True)
            
            chequear_estrategia_ma_cross(df, simbolo)
            
        except Exception as e:
            print(f"Error analizando {simbolo}: {e}")
    time.sleep(INTERVALO_REVISION_SEGUNDOS)
