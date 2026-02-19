#aqui estarán sensores y actuadores
import adafruit_dht
from w1thermsensor import W1ThermSensor, Sensor
import board
from DFRobot_LTR390UV import *
import threading
from datetime import datetime
import time
import csv
import smbus
import numpy as np
import RPi.GPIO as GPIO

I2C_BUS = 1
TCA_ADDRESS = 0x70       # Dirección por defecto del TCA9548A
UV_ADDRESS = 0x1C        # Dirección del LTR390-UV

bus = smbus.SMBus(I2C_BUS)

uv_sensors = {}
CHANNELS = [0, 1, 4, 6]   # Canales usados del TCA9548A

# === CONTROL TEMPERATURA GPIOS ===
A_RES = 23    # resistencias
A_PLTR = 24   # peltier
F_PLTR = 25   # ventiladores celda peltier

GPIO.setmode(GPIO.BCM)

GPIO.setup(A_RES, GPIO.OUT)
GPIO.setup(A_PLTR, GPIO.OUT)
GPIO.setup(F_PLTR, GPIO.OUT)

LUV_S = 17   # lámparas uv superiores
LUV_I = 18   # lámparas uv inferiores

# === GPIOS LÁMPARAS ===
GPIO.setup(LUV_S, GPIO.OUT)
GPIO.setup(LUV_I, GPIO.OUT)

# === Inicialización sensores ===
dht1 = adafruit_dht.DHT22(board.D27)    # Sensor DHT22 - 1
dht2 = adafruit_dht.DHT22(board.D22)    # Sensor DHT22 - 2
sensor1 = W1ThermSensor(sensor_type=Sensor.DS18B20, sensor_id="3387008797ca")
sensor2 = W1ThermSensor(sensor_type=Sensor.DS18B20, sensor_id="678e008778c2")
sensor3 = W1ThermSensor(sensor_type=Sensor.DS18B20, sensor_id="32cf0087e27c")
sensor4 = W1ThermSensor(sensor_type=Sensor.DS18B20, sensor_id="447500876c5e")

def tca_select(channel):
    if channel < 0 or channel > 7:
        raise ValueError("Canal fuera de rango (0-7)")
    bus.write_byte(TCA_ADDRESS, 1 << channel)
    time.sleep(0.01)

def init_uv_sensor(channel):
    tca_select(channel)
    sensor = DFRobot_LTR390UV_I2C(I2C_BUS, UV_ADDRESS)

    while not sensor.begin():
        print(f"Canal {channel} no responde. Reintentando...")
        time.sleep(1)

    sensor.set_ALS_or_UVS_meas_rate(e18bit, e100ms)
    sensor.set_ALS_or_UVS_gain(eGain1)
    sensor.set_mode(UVSMode)

    print(f"Sensor UV inicializado en canal {channel}")
    return sensor

for ch in CHANNELS:
    uv_sensors[ch] = init_uv_sensor(ch)

# Config base de datos
SAVE_INTERVAL = 60.0

# === Datos base del experimento ===
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

# === FUNCIONES LECTURA DE SENSORES  ===
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

# Función de lectura de sensores UV4
def leer_Uvs():
    uv_values = {}
    for ch, sensor in uv_sensors.items():
        try:
            tca_select(ch)
            sensor.set_ALS_or_UVS_meas_rate(e18bit, e100ms)
            sensor.set_ALS_or_UVS_gain(eGain1)
            sensor.set_mode(UVSMode)

            time.sleep(1)  # Esperar configuración

            sensor.read_original_data()
            time.sleep(0.3) # Ignorar primer lectura

            uv_values[ch] = sensor.read_original_data()

        except Exception as e:
            print(f"[ERROR] Lectura canal {ch}: {e}")
        time.sleep(5)

    return uv_values

class CamaraUV:
    def __init__(self):

        # ===== ESTADO =====
        self.estado = "IDLE"

        # ===== PARAMETROS EXPERIMENTO =====
        self.total_duration = 0
        self.start_time = 0
        self.remaining_time = 0

        self.setpoint_temp = 25
        self.dosis = 0

        # ===== DATOS SENSORES =====
        self.latest_data = {
            'Temperatura1': None,
            'Temperatura2': None,
            'Temperatura3': None,
            'Temperatura4': None,
            'Humedad1': None,
            'Humedad2': None,
            'Temperatura5': None,
            'Temperatura6': None,
            'UV1': None,
            'UV2': None,
            'UV3': None,
            'UV4': None,
            'timestamp': None
        }

        self.data_lock = threading.Lock()

        # ===== EVENTOS =====
        self.paro_eme = threading.Event()
        self.paro_eme.set()

        self.guardar_event = threading.Event()
        self.guardar_event.clear()

        # === CONTROL EXPERIMENTO ===
    def iniciar_experimento(self, tiempo_min, temp, dosis):
        self.total_duration = tiempo_min * 60
        self.remaining_time = self.total_duration
        self.setpoint_temp = temp
        self.dosis = dosis

        self.cambiar_estado("RUNNING")

    def cambiar_estado(self, nuevo_estado):
        if self.estado == nuevo_estado:
            return  # No hacer nada si ya está en ese estado

        print(f"[BCKND] {self.estado} a {nuevo_estado}")

        self.estado = nuevo_estado

        # ===== Acciones automáticas según estado =====

        if nuevo_estado == "IDLE":
            self.remaining_time = 0
            self.temp_all_off()
            self.lamps_off()
            self.guardar_event.clear()

        elif nuevo_estado == "RUNNING":
            self.start_time = time.time()
            self.guardar_event.set()
            print("[BCKND] Experimento iniciado")

        elif nuevo_estado == "PAUSED":
            self.temp_all_off()
            self.lamps_off()

        elif nuevo_estado == "FINISHED":
            self.remaining_time = 0
            self.temp_all_off()
            self.lamps_off()
            self.guardar_event.clear()
            print("[BCKND] Experimento finalizado")

        elif nuevo_estado == "ERROR":
            self.temp_all_off()
            self.lamps_off()
            self.guardar_event.clear()
            print("[BCKND] ERROR detectado")

    # === HILOS ===
    # Hilo para contar tiempo restante del experimento 
    def thread_time(self):
        while True:
            if self.estado == "RUNNING":
                elapsed = time.time() - self.start_time
                self.remaining_time = max(self.total_duration - elapsed, 0)

                if self.remaining_time <= 0:
                    self.cambiar_estado("FINISHED")

            time.sleep(1)
    # Hilo para prender/apagar lámparas UV
    def thread_lamps(self):
        self.lamps_off()
        while True:
            if self.estado == "RUNNING":
                self.lamps_on()
            else:
                self.lamps_off()

            time.sleep(0.5)
    # Hilo para controlar temperatura
    def thread_CNTRLtemp(self):
        HISTERESIS = 1.0        # ±°C
        TEMP_MAX = 80.0         # límite superior
        TEMP_MIN = 20.0         # límite inferior
        self.temp_all_off()          
        while True:
            if self.estado != "RUNNING":
                self.temp_all_off()
                time.sleep(1)
                continue
            if not self.paro_eme.is_set():
                self.temp_all_off()
                time.sleep(0.5)
                continue
            with self.data_lock: # Leer temperaturas
                temps = [
                    self.latest_data.get('Temperatura1'),
                    self.latest_data.get('Temperatura2'),
                    self.latest_data.get('Temperatura3'),
                    self.latest_data.get('Temperatura4'),
                ]

            temps_validas = [t for t in temps if t is not None]

            if not temps_validas:
                print("Sin lecturas válidas")
                self.temp_all_off()
                time.sleep(1)
                continue

            Tmean = sum(temps_validas) / len(temps_validas)
            print(f"Temperatura promedio: {round(Tmean,2)} °C")

            if Tmean >= TEMP_MAX or Tmean <= TEMP_MIN:
                print("LIMITE ALCANZADO")
                self.temp_all_off()
                self.cambiar_estado("PAUSED")
                time.sleep(2)
                continue

            # Control ON/OFF con histéresis
            if Tmean < (self.setpoint_temp - HISTERESIS):
                self.heat_on()

            elif Tmean > (self.setpoint_temp + HISTERESIS):
                self.cool_on()

            else:
                self.temp_all_off()

            time.sleep(5)  # periodo de control
    # Hilo de guardado de lecturas en .CSV
    def thread_guardado(self):
        csvfile = None
        writer = None
        filename_actual = None

        while True:
            # Esperar hasta que el experimento inicie
            self.guardar_event.wait()

            # Si cambia el experimento, genera un nuevo archivo
            Tiempoh = self.total_duration / 3600
            filename = f"exp_Time_{round(Tiempoh,2)}h_Temp_{self.setpoint_temp}C_Dosis_{int(self.dosis)}J.csv"

            if filename != filename_actual:
                filename_actual = filename
                csvfile = open(filename, 'a', newline='')
                writer = csv.writer(csvfile)
                if csvfile.tell() == 0:
                    writer.writerow(['Timestamp', 'DS18B20_01', 'DS18B20_02', 'DS18B20_03', 'DS18B20_04', 'Humedad_01',
                                    'Humedad_02', 'TemperaturaDHT_01', 'TemperaturaDHT_02', 'UV_01', 'UV_2', 'UV_03', 'UV_04'])
                print(f"[CSV] Guardando en: {filename}")

            # Guardado mientras quede tiempo
            while self.estado == "RUNNING":
                self.paro_eme.wait()  #paro de emergencia

                with self.data_lock:
                    data = self.latest_data.copy()

                timestamp = data['timestamp']
                if timestamp:
                    ts = timestamp.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    ts = "N/A"

                fila = [
                    ts,
                    data['Temperatura1'],
                    data['Temperatura2'],
                    data['Temperatura3'],
                    data['Temperatura4'],
                    data['Humedad1'],
                    data['Humedad2'],
                    data['Temperatura5'],
                    data['Temperatura6'],
                    data['UV1'],
                    data['UV2'],
                    data['UV3'],
                    data['UV4']
                ]

                writer.writerow(fila)
                csvfile.flush()

                print("[CSV] Guardado:", fila)

                time.sleep(SAVE_INTERVAL)

            # Si terminó el experimento detener guardado
            self.guardar_event.clear()
            print("[CSV] Guardado detenido (experimento terminado)")

            time.sleep(1)
    # Hilo de lectura de sensores DS18B20 (temperatura)
    def thread_DS18B20(self):
        while True:
            try:
                temp1 = sensor1.get_temperature()
                temp2 = sensor2.get_temperature()
                temp3 = sensor3.get_temperature()
                temp4 = sensor4.get_temperature()
                with self.data_lock:
                    self.latest_data['Temperatura1'] = temp1
                    self.latest_data['Temperatura2'] = temp2
                    self.latest_data['Temperatura3'] = temp3
                    self.latest_data['Temperatura4'] = temp4
                    self.latest_data['timestamp'] = datetime.now()
            except Exception as e:
                print(f"Error lectura DS18B20: {e}")
            time.sleep(1.0)
    # Hilo de lectura de sensores UV Y DHT
    def thread_DHT_UV(self):
        while True:
            try:
                temp5, hum1 = leer_DHT(dht1)
                time.sleep(2)
                temp6, hum2 = leer_DHT(dht2)
                uvs = leer_Uvs()

                with self.data_lock:
                    self.latest_data['Temperatura5'] = temp5
                    self.latest_data['Temperatura6'] = temp6
                    self.latest_data['Humedad1'] = hum1
                    self.latest_data['Humedad2'] = hum2
                    self.latest_data['UV1'] = uvs.get(0)
                    self.latest_data['UV2'] = uvs.get(1)
                    self.latest_data['UV3'] = uvs.get(4)
                    self.latest_data['UV4'] = uvs.get(6)
                    self.latest_data['timestamp'] = datetime.now()
            except Exception as e:
                print(f"Error lectura DS18B20: {e}")
            time.sleep(20.0)

    # === CONTROL HARDWARE ===
    # CONTROL RELEVADOR ACTUADORES TEMP
    def heat_on(self):
        GPIO.output(A_RES, GPIO.HIGH)
        GPIO.output(A_PLTR, GPIO.LOW)
        GPIO.output(F_PLTR, GPIO.LOW)
        print("Calentando...")
    def cool_on(self):
        GPIO.output(A_RES, GPIO.LOW)
        GPIO.output(A_PLTR, GPIO.HIGH)
        GPIO.output(F_PLTR, GPIO.HIGH)
        print("Enfriando...")
    def temp_all_off(self):
        GPIO.output(A_RES, GPIO.LOW)
        GPIO.output(A_PLTR, GPIO.LOW)
        GPIO.output(F_PLTR, GPIO.LOW)
        print("TEMP APAGADO")
    # CONTROL RELEVADOR LAMPARAS UV
    def lamps_on(self):
        GPIO.output(LUV_S, GPIO.HIGH)
        GPIO.output(LUV_I, GPIO.HIGH)
        print("Lámparas ENCENDIDAS")
    def lamps_off(self):
        GPIO.output(LUV_S, GPIO.LOW)
        GPIO.output(LUV_I, GPIO.LOW)
        print("Lámparas APAGADAS")
    


#if __name__ == "__main__":
