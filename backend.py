#aqui estarán sensores y motores
import adafruit_dht
from w1thermsensor import W1ThermSensor, Sensor
import board
from DFRobot_LTR390UV import *
import threading
from datetime import datetime
import time
import csv
import numpy as np

# Config Sensor UV
ADDRESS = 0x1c 
I2C_1   = 0x01
LTR390UV = DFRobot_LTR390UV_I2C(I2C_1 ,ADDRESS)

# Setup Sensor UV
def setupUV():
    while not LTR390UV.begin():
        print("Sensor UV no se pudo inicializar. Reintentando...")
        time.sleep(1)
    print("Sensor UV inicializado correctamente.")
    LTR390UV.set_ALS_or_UVS_meas_rate(e18bit, e100ms)
    LTR390UV.set_ALS_or_UVS_gain(eGain1)
    LTR390UV.set_mode(UVSMode)

# Inicialización sensores
dht1 = adafruit_dht.DHT22(board.D27)    # Sensor DHT22 - 1
dht2 = adafruit_dht.DHT22(board.D22)    # Sensor DHT22 - 2
sensor1 = W1ThermSensor(sensor_type=Sensor.DS18B20, sensor_id="3387008797ca")
sensor2 = W1ThermSensor(sensor_type=Sensor.DS18B20, sensor_id="678e008778c2")
sensor3 = W1ThermSensor(sensor_type=Sensor.DS18B20, sensor_id="32cf0087e27c")
sensor4 = W1ThermSensor(sensor_type=Sensor.DS18B20, sensor_id="447500876c5e")
setupUV()

# Variables compartidas Threading 
paro_eme = threading.Event()
paro_eme.set()  # Por defecto, el hilo sigue corriendo
latest_data = {
    'Temperatura1': None,
    'Temperatura2': None,
    'Temperatura3': None,
    'Temperatura4': None,
    'Humedad1': None,
    'Humedad2': None,
    'Temperatura5': None,
    'Temperatura6': None,
    'UV1': None,
    'timestamp': None
}
data_lock = threading.Lock()

# datos globales 
Dstcl = 0
Tiempo = 1
Temperatura = 20
Dosis = 1
runing = 0

# Config base de datos
SAVE_INTERVAL = 60.0

guardar_event = threading.Event()
guardar_event.clear()  # No guardar todavía

# Hilo de lectura de sensores DS18B20 (temperatura)
def thread_DS18B20():
    global latest_data
    while True:
        try:
            temp1 = sensor1.get_temperature()
            temp2 = sensor2.get_temperature()
            temp3 = sensor3.get_temperature()
            temp4 = sensor4.get_temperature()
            with data_lock:
                latest_data['Temperatura1'] = temp1
                latest_data['Temperatura2'] = temp2
                latest_data['Temperatura3'] = temp3
                latest_data['Temperatura4'] = temp4
                latest_data['timestamp'] = datetime.now()
        except Exception as e:
            print(f"Error lectura DS18B20: {e}")
        time.sleep(1.0)

# Función de lectura de sensores UV4

# Función de lectura de sensores DHT
def leer_DHT(dht_sensor, reintentos=6, t=2):
    for i in range(reintentos):
        try:
            temp = dht_sensor.temperature
            hum = dht_sensor.humidity
            if temp is not None and hum is not None:
                return temp, hum
        except Exception as e:
            print(f"Error leyendo DHT: {e}")
        time.sleep(t)

    return None, None

# Hilo de lectura de sensores DHT y UV
def thread_DHT_UV():
    global latest_data
    while True:

        temp5, hum1 = leer_DHT(dht1)
        temp6, hum2 = leer_DHT(dht2)

        try:
            uv_data = LTR390UV.read_original_data()
        except Exception as e:
            print(f"Error lectura UV: {e}")
            uv_data = None

        with data_lock:
            latest_data['Temperatura5'] = temp5
            latest_data['Temperatura6'] = temp6
            latest_data['Humedad1'] = hum1
            latest_data['Humedad2'] = hum2
            latest_data['UV1'] = str(uv_data)
            latest_data['timestamp'] = datetime.now()

        time.sleep(20.0)  

# Hilo para guardar datos en CSV
def thread_guardado():
    global latest_data, Dstcl, Tiempo, Temperatura, Dosis, remaining_time
    
    csvfile = None
    writer = None
    filename_actual = None

    while True:

        # Esperar hasta que el experimento inicie
        guardar_event.wait()

        # Si cambia el experimento, genera un nuevo archivo
        Tiempoh = Tiempo / 60
        filename = f"exp_Time_{round(Tiempoh,2)}h_Temp_{Temperatura}C_Dosis_{int(Dosis)}J.csv"

        if filename != filename_actual:
            filename_actual = filename
            csvfile = open(filename, 'a', newline='')
            writer = csv.writer(csvfile)
            if csvfile.tell() == 0:
                writer.writerow(['Timestamp', 'DS18B20_01', 'DS18B20_02', 'DS18B20_03', 'DS18B20_04', 'Humedad_01',
                                 'Humedad_02', 'TemperaturaDHT_01', 'TemperaturaDHT_02', 'UV_01'])
            print(f"[CSV] Guardando en: {filename}")

        # Guardado mientras quede tiempo
        while remaining_time > 0:
            paro_eme.wait()  #paro de emergencia

            with data_lock:
                data = latest_data.copy()

            fila = [
                data['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
                data['Temperatura1'],
                data['Temperatura2'],
                data['Temperatura3'],
                data['Temperatura4'],
                data['Humedad1'],
                data['Humedad2'],
                data['Temperatura5'],
                data['Temperatura6'],
                data['UV1']
            ]

            writer.writerow(fila)
            csvfile.flush()

            print("[CSV] Guardado:", fila)

            time.sleep(SAVE_INTERVAL)

        # Fin del experimento → detener guardado
        guardar_event.clear()
        print("[CSV] Guardado detenido (experimento terminado)")

        time.sleep(1)

# === Datos base ===
cm = np.array([5.5, 11, 16.5, 22, 27.5])   # valores de distancia (cm)
I = np.array([12860.42, 10472.92, 8147.5, 6287.5, 5150])   # valores de irradiancia (mW/m2)
NEMApaso = 0.5 # paso de las charolas (cm)

# === Interpolación ===
def config():
    coef = np.polyfit(cm, I, 4)
    poly = np.poly1d(coef)
    pase = int((27.5 - 5.5) / NEMApaso)
	
    x_line = np.linspace(min(cm), max(cm), pase)
    y_line = poly(x_line)

    return x_line, y_line

if __name__ == "_main_":
    thread_DHT_UV()
    thread_DS18B20()

