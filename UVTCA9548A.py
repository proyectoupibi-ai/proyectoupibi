import time
import smbus
from DFRobot_LTR390UV import *

I2C_BUS = 1
TCA_ADDRESS = 0x70       # Dirección por defecto del TCA9548A
UV_ADDRESS = 0x1C        # Dirección del LTR390-UV

bus = smbus.SMBus(I2C_BUS)

def tca_select(channel):
    if channel < 0 or channel > 7:
        raise ValueError("Canal TCA fuera de rango (0-7)")
    bus.write_byte(TCA_ADDRESS, 1 << channel)
    time.sleep(0.01)

def init_uv_sensor(channel):
    tca_select(channel)
    sensor = DFRobot_LTR390UV_I2C(I2C_BUS, UV_ADDRESS)

    while not sensor.begin():
        print(f"[ERROR] UV canal {channel} no responde. Reintentando...")
        time.sleep(1)

    sensor.set_ALS_or_UVS_meas_rate(e18bit, e100ms)
    sensor.set_ALS_or_UVS_gain(eGain1)
    sensor.set_mode(UVSMode)

    print(f"[OK] Sensor UV inicializado en canal {channel}")
    return sensor

uv_sensors = {}
CHANNELS = [0, 1, 4, 6]   # Canales usados del TCA9548A

for ch in CHANNELS:
    uv_sensors[ch] = init_uv_sensor(ch)

print("\nLectura de sensores UV iniciada...\n")


while True:
    for ch, sensor in uv_sensors.items():
        try:
            tca_select(ch)
            sensor.set_ALS_or_UVS_meas_rate(e18bit, e100ms)
            sensor.set_ALS_or_UVS_gain(eGain1)
            sensor.set_mode(UVSMode)

            time.sleep(1)  # Esperar conversión

            sensor.read_original_data()
            time.sleep(0.3)

            uv_value = sensor.read_original_data()
            #uv_value = sensor.read_UVS_transform_data()
            print(f"Canal {ch} | UV{ch+1}: {uv_value}")
        except Exception as e:
            print(f"[ERROR] Lectura UV canal {ch}: {e}")

    print("-" * 20)
    time.sleep(5)
