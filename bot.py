import ccxt
import pandas as pd
import pandas_ta as ta 
import time
import requests
import matplotlib.pyplot as plt
import os
from datetime import datetime
import pytz

# --- INICIO DE LA CONFIGURACIÓN ---
DISCORD_WEBHOOK_URL = 'https://discord.com/api/webhooks/1389794534476611684/_hKced3HWO7E3OFljwnEpmS1rmrm4_P8OCZP7uF5EW924xWiI48_y_uQJsE8FeY1pNml'

# 1. SELECCIÓN DE ESTRATEGIA ('MA_CROSS' o 'RSI')
ESTRATEGIA_ACTIVA = 'RSI' 

# 2. GESTIÓN DE CAPITAL Y RIESGO
CAPITAL_INICIAL_USDT = 20.0
RIESGO_POR_OPERACION_PORCENTAJE = 5 

# 3. LISTA DE CRIPTOMONEDAS (Con tu corrección)
LISTA_DE_SIMBOLOS = [
    'BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'DOGEUSDT', 'BNBUSDT', 
    'ADAUSDT', 'LINKUSDT', 'AVAXUSDT', 'MATUSDT', 'LTCUSDT', 'SUIUSDT',
    'DOTUSDT', 'TRXUSDT', 'SHIBUSDT', 'ETCUSDT', 'BCHUSDT', 'NEARUSDT',
    'FILUSDT', 'APTUSDT', 'OPUSDT', 'ARBUSDT'
]

# 4. CONFIGURACIÓN TÉCNICA (Con tus ajustes)
TEMPORALIDAD = '5m' # <-- AJUSTADO A 5 MINUTOS
INTERVALO_REVISION_SEGUNDOS = 60 # <-- AJUSTADO A 1 MINUTO
RATIO_RIESGO_BENEFICIO = 1.5
VELAS_PARA_SL = 10
# Parámetros para MA_CROSS
MA_CROSS_RAPIDA = 20
MA_CROSS_LENTA = 50
# Parámetros para RSI
RSI_PERIODO = 14
RSI_SOBRECOMPRA = 70
RSI_SOBREVENTA = 30
# --- FIN DE LA CONFIGURACIÓN ---


def generar_y_guardar_grafico(df, simbolo, tipo_señal, precio_señal, sl, tp):
    plt.style.use('dark_background')
    fig, (ax1, ax2) = plt.subplots(2, 1, gridspec_kw={'height_ratios': [3, 1]}, figsize=(10, 8))
    df_reciente = df.tail(100)
    ax1.plot(df_reciente.index, df_reciente['close'], label='Precio', color='cyan')
    if ESTRATEGIA_ACTIVA == 'MA_CROSS' and 'MA_Rapida' in df.columns:
        ax1.plot(df_reciente.index, df_reciente['MA_Rapida'], label=f'MA Rápida', color='orange', linestyle='--')
        ax1.plot(df_reciente.index, df_reciente['MA_Lenta'], label=f'MA Lenta', color='purple', linestyle='--')
    ax1.axhline(y=tp, color='lime', linestyle='--', label=f'Take Profit ({tp:.4f})')
    ax1.axhline(y=precio_señal, color='white', linestyle=':', label=f'Entrada ({precio_señal:.4f})', alpha=0.5)
    ax1.axhline(y=sl, color='red', linestyle='--', label=f'Stop Loss ({sl:.4f})')
    ax1.set_title(f'Análisis de {simbolo} - {TEMPORALIDAD}', fontsize=16); ax1.set_ylabel('Precio (USDT)'); ax1.legend()
    if 'RSI' in df.columns:
        ax2.plot(df_reciente.index, df_reciente['RSI'], label=f'RSI ({RSI_PERIODO})', color='yellow')
        ax2.axhline(y=RSI_SOBRECOMPRA, color='red', linestyle='--', alpha=0.5); ax2.axhline(y=RSI_SOBREVENTA, color='lime', linestyle='--', alpha=0.5)
        ax2.fill_between(df_reciente.index, RSI_SOBRECOMPRA, RSI_SOBREVENTA, color='#808080', alpha=0.1)
        ax2.set_ylabel('RSI'); ax2.legend()
    fig.tight_layout()
    ruta_grafico = f"grafico_{simbolo.replace('/', '_')}.png"; fig.savefig(ruta_grafico); plt.close(fig)
    return ruta_grafico

def enviar_alerta_discord(mensaje, ruta_grafico):
    if DISCORD_WEBHOOK_URL.startswith('PON_AQUI'): return
    try:
        with open(ruta_grafico, 'rb') as f:
            files = {'file': (ruta_grafico, f, 'image/png')}; payload = {'content': mensaje}
            requests.post(DISCORD_WEBHOOK_URL, data=payload, files=files)
    except Exception as e: print(f"Error al enviar alerta a Discord: {e}")
    os.remove(ruta_grafico)

def procesar_señal(df, simbolo, tipo_señal, nombre_estrategia):
    estados_bot.setdefault(simbolo, {})['ultima_señal'] = f"{tipo_señal}_{nombre_estrategia}"
    precio_entrada = df['close'].iloc[-1]
    if tipo_señal == 'COMPRA':
        stop_loss = df['low'].tail(VELAS_PARA_SL).min() * 0.998; operacion_texto = "🟢 Operación: Long 🟢"
    else: # VENTA
        stop_loss = df['high'].tail(VELAS_PARA_SL).max() * 1.002; operacion_texto = "🔴 Operación: Short 🔴"
    riesgo_por_moneda = abs(precio_entrada - stop_loss)
    take_profit = precio_entrada + (riesgo_por_moneda * RATIO_RIESGO_BENEFICIO) if tipo_señal == 'COMPRA' else precio_entrada - (riesgo_por_moneda * RATIO_RIESGO_BENEFICIO)
    riesgo_maximo_usdt = CAPITAL_INICIAL_USDT * (RIESGO_POR_OPERACION_PORCENTAJE / 100)
    tamaño_posicion = riesgo_maximo_usdt / riesgo_por_moneda if riesgo_por_moneda > 0 else 0
    hora_formateada = datetime.now(pytz.timezone('America/La_Paz')).strftime('%d-%m-%Y a las %H:%M:%S')
    mensaje = (f"💡 **Detalle de posición ({nombre_estrategia})**\n-------------------------------------\n"
               f"🗓️ *Señal generada el {hora_formateada} (Hora Bolivia)*\n-------------------------------------\n"
               f"🪙 **Token:** {simbolo}\n{operacion_texto}\n.\n"
               f"🎯 **Precio de apertura:** {precio_entrada:.4f} USDT\n✋ **Stop Loss (SL):** {stop_loss:.4f} USDT\n"
               f"🤑 **Take Profit (TP):** {take_profit:.4f} USDT\n"
               f"📏 **Tamaño Sugerido:** `{tamaño_posicion:.4f}` monedas (para arriesgar ${riesgo_maximo_usdt:.2f} USDT)")
    ruta_grafico = generar_y_guardar_grafico(df, simbolo, tipo_señal, precio_entrada, stop_loss, take_profit)
    enviar_alerta_discord(mensaje, ruta_grafico)

# --- BUCLE PRINCIPAL ---
exchange = ccxt.mexc(); estados_bot = {}
print(f"Bot multifuncional iniciado. Estrategia activa: {ESTRATEGIA_ACTIVA}")
while True:
    print(f"\n--- Nuevo ciclo de revisión ---")
    for simbolo in LISTA_DE_SIMBOLOS:
        try:
            print(f"Analizando {simbolo}...")
            velas = exchange.fetch_ohlcv(simbolo, TEMPORALIDAD, limit=200)
            df = pd.DataFrame(velas, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df.set_index(pd.to_datetime(df['timestamp'], unit='ms'), inplace=True)
            
            if ESTRATEGIA_ACTIVA == 'MA_CROSS':
                df['MA_Rapida'] = df['close'].rolling(window=MA_CROSS_RAPIDA).mean()
                df['MA_Lenta'] = df['close'].rolling(window=MA_CROSS_LENTA).mean()
                ultima, penultima = df.iloc[-1], df.iloc[-2]
                estado_simbolo = estados_bot.setdefault(simbolo, {})
                if penultima['MA_Rapida'] <= penultima['MA_Lenta'] and ultima['MA_Rapida'] > ultima['MA_Lenta']:
                    if estado_simbolo.get('ultima_señal') != 'COMPRA_MA_CROSS': procesar_señal(df, simbolo, 'COMPRA', 'MA_CROSS')
                elif penultima['MA_Rapida'] >= penultima['MA_Lenta'] and ultima['MA_Rapida'] < ultima['MA_Lenta']:
                    if estado_simbolo.get('ultima_señal') != 'VENTA_MA_CROSS': procesar_señal(df, simbolo, 'VENTA', 'MA_CROSS')
            elif ESTRATEGIA_ACTIVA == 'RSI':
                df['RSI'] = ta.rsi(df['close'], length=RSI_PERIODO)
                ultima, penultima = df.iloc[-1], df.iloc[-2]
                estado_simbolo = estados_bot.setdefault(simbolo, {})
                if penultima['RSI'] < RSI_SOBREVENTA and ultima['RSI'] >= RSI_SOBREVENTA:
                    if estado_simbolo.get('ultima_señal') != 'COMPRA_RSI': procesar_señal(df, simbolo, 'COMPRA', 'RSI')
                elif penultima['RSI'] > RSI_SOBRECOMPRA and ultima['RSI'] <= RSI_SOBRECOMPRA:
                    if estado_simbolo.get('ultima_señal') != 'VENTA_RSI': procesar_señal(df, simbolo, 'VENTA', 'RSI')
        except Exception as e:
            print(f"Error analizando {simbolo}: {e}")
    time.sleep(INTERVALO_REVISION_SEGUNDOS)
