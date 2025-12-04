#control y GUI
import tkinter as tk
from tkinter import messagebox
import threading
from backend import *
import numpy as np
import matplotlib as plt

# === CONFIGURACION THREADS ===
# Variables compartidas Threading 
paro_eme = threading.Event()
paro_eme.set()  # Por defecto, el hilo sigue corriendo
latest_data = {
    'Temperatura1': None,
    'Temperatura2': None,
    'Temperatura3': None,
    'Temperatura4': None,
    'Temperatura5': None,
    'Temperatura6': None,
    'Humedad1': None,
    'Humedad2': None,
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

Dist, Irrad = config()

# === Función de cálculo ===
#1 J/m2 = W*s/m2
def calcularcm():
    global Dstcl, Tiempo, Dosis, Temperatura

    try:
        Time = slider_tiempo.get()
        Dosis = slider_dosis.get()
        Temperatura = slider_temp.get()

        if Tiempo <= 0:
            messagebox.showerror("Error", "El tiempo debe ser mayor a 0")
            return

        Irradiancia = Dosis / (Time*60)
        Irradiancia = Irradiancia * 1000

        idx = np.argmin(np.abs(Irrad - Irradiancia))
        Dstcl = Dist[idx]
        Irrdcl = Irrad[idx]

        if Irradiancia > Irrad[0]:
            messagebox.showerror("Error", "Irradiancia máxima, aumentar tiempo")
            return
        elif Irradiancia < Irrad[-1]:
            messagebox.showerror("Error", "Irradiancia mínima, disminuir tiempo")
            return
        
        if Irrdcl==Irradiancia:
            resultado.set(f"Para irradiancia ≈ {Irradiancia:.2f} mW/m2,\n"
                      f"Distancia ≈ {Dstcl:.3f} cm (valor interpolado ≈ {Irrdcl:.2f})")
            Tiempo= Time
        else: 
            Irrdrl = Irrdcl / 1000
            tiemposec = Dosis / (Irrdrl * 60)
            resultado.set(f"Para irradiancia ≈ {Irradiancia:.2f} mW/m2,\n"
                      f"Distancia ≈ {Dstcl:.3f} cm (valor interpolado ≈ {Irrdcl:.2f})"
                      f"Tiempo solicitado = {Time} Nuevo tiempo={tiemposec:.2f}")
            Tiempo = tiemposec
            slider_temp.set(Tiempo)


        plt.plot(Dist, Irrad, color="purple", label="Interpolación 4to grado")
        plt.scatter(Dstcl, Irrdcl, color="red", label="Punto calculado")
        plt.xlabel("Distancia (cm)")
        plt.ylabel("Irradiancia (mW/m2)")
        plt.title("Punto calculado")
        plt.legend()
        plt.grid(True)
        plt.show()

    except ValueError:
        messagebox.showerror("Error", "Introduce valores válidos")

#modificar a mover motores
def cargar():
    print("colocar o retirar muestras")

def muestras():
    global remaining_time, runing

    try:
        if remaining_time == 0:
            cargar()
        elif runing == 0:
            cargar()
        else:
            messagebox.showerror("Error", "Experimento en curso")
    except ValueError:
        messagebox.showerror("Error", "Experimento en curso")

#hilo para controlar Temperatura
def thread_Control():
    global latest_data, remaining_time
    while True and remaining_time > 0:
        paro_eme.wait()  #paro de emergencia

        with data_lock:
                data = latest_data
        if data:

            valores_temp = [data['Temperatura1'], data['Temperatura2'], data['Temperatura3'], data['Temperatura4']]
            valores_validos = [t for t in valores_temp if t is not None]

            if valores_validos:
                Tmean = sum(valores_validos) / len(valores_validos)
                print(f"Temperatura promedio: {round(Tmean, 2)} °C")
            else:
                print("Temperatura promedio no disponible (todos los sensores fallaron)")

        time.sleep(2.0)

#hilo para contar tiempo restante del experimento 
def thread_time():
    global remaining_time, start_time, total_duration

    while True and remaining_time > 0:
        paro_eme.wait()  #paro de emergencia

        now = time.time()
        elapsed = now - start_time
        remaining_time = max(total_duration - elapsed,0)

        time.sleep(0.01)

def actualizar_tiempo_restante():
    global remaining_time, total_duration

    if remaining_time > 0:
        minutos = int(remaining_time // 60)
        segundos = int(remaining_time % 60)
        label_tiempo.config(text=f"Tiempo restante: {minutos:03d} min {segundos:02d} s")
    elif remaining_time <= 0 and total_duration > 0:
        label_tiempo.config(text="Experimento finalizado.")
    
    # Llama a sí misma cada 1000 ms (1 segundo)
    root.after(1000, actualizar_tiempo_restante)

def INICIO():
    global start_time, remaining_time, total_duration, Tiempo, runing

    try:
        total_duration = Tiempo * 60  # a segundos
        remaining_time = total_duration
        start_time = time.time()

        paro_eme.set()  # Asegura que no está en pausa

        guardar_event.set()
        threading.Thread(target=thread_Control, daemon=True).start()
        threading.Thread(target=thread_time, daemon=True).start()

        runing = 1

        actualizar_tiempo_restante()

        btn_INICIO.config(bg="green", fg="white", text="Experimento en curso")

        print(f"Experimento iniciado: {Tiempo} minutos")

        def check_end():
            if remaining_time <= 0:
                btn_INICIO.config(bg="lightgray", fg="black", text="Iniciar experimento")
            else:
                root.after(1000, check_end)

        check_end()

    except ValueError:
        messagebox.showerror("Error", "Introduce valores válidos")

#Funciones paro de Emergencia
parado = tk.BooleanVar()
parado.set(False)

def toggle_paro():
    global runing
    if parado.get():
        paro_eme.set()
        btn_STOP.config(text="PARO DE EMERGENCIA", bg="yellow", fg="black")
        parado.set(False)
        runing = 1
        print("Experimento reanudado.")
    else:
        paro_eme.clear()
        btn_STOP.config(text="REANUDAR", bg="red", fg="white")
        parado.set(True)
        runing = 0
        print("Experimento pausado.")

# -----------------------------
# VENTANAS GUI
# -----------------------------
root = tk.Tk()
root.title("Cámara de Irradiación")
root.geometry("700x500")

# === Frame de inicio ===
frame_inicio = tk.Frame(root)
frame_inicio.pack(expand=True)

# --- Etiqueta del temporizador ---
label_tiempo = tk.Label(frame_inicio, text="Tiempo restante: --:--", font=("Arial", 14), fg="darkorange")
label_tiempo.pack(pady=10)

#tk.Label(frame_inicio, text="Bienvenido", font=("Arial", 18)).pack(pady=20)
btn_go_setting = tk.Button(frame_inicio,text="Configuración", command=lambda: mostrar_settings(), width=45, height=3)
btn_go_setting.pack()

btn_ver_sensores = tk.Button(frame_inicio, text="Ver Lecturas de Sensores", command=lambda : mostrar_sensores(), width=45, height=3)
btn_ver_sensores.pack(pady=10)

btn_INICIO = tk.Button(frame_inicio, text="Iniciar experimento", command=lambda : INICIO(),bg="lightgray",
    fg="black", width=45, height=3)
btn_INICIO.pack(pady=10)

btn_STOP = tk.Button(
    frame_inicio,
    text="PARO DE EMERGENCIA",
    command=lambda: toggle_paro(),
    width=45,
    height=3,
    bg="yellow",
    fg="black",
    font=("Arial", 11, "bold")
)
btn_STOP.pack(pady=10)

btn_cargar_retirar = tk.Button(frame_inicio, text="CARGAR / RETIRAR MUESTRAS", command=lambda : muestras(), width=45, height=3)
btn_cargar_retirar.pack(pady=10)

# === Frame de variables ===
frame_calculo = tk.Frame(root)

# Slider para el tiempo en minutos (1 a 600)
tk.Label(frame_calculo, text="Tiempo del experimento (min):").grid(row=0, column=0, padx=10, pady=5, sticky="w")
slider_tiempo = tk.Scale(frame_calculo, from_=1, to=600, orient=tk.HORIZONTAL, length=300)
slider_tiempo.grid(row=0, column=1, padx=10, pady=5)
slider_tiempo.set(300)  # Valor por defecto 

# Slider para la dosis en kJ/m2 (0 a 100,000)
tk.Label(frame_calculo, text="Dosis (J/m2):").grid(row=1, column=0, padx=10, pady=5, sticky="w")
slider_dosis = tk.Scale(frame_calculo, from_=0, to=100000, resolution=1000, orient=tk.HORIZONTAL, length=300)
slider_dosis.grid(row=1, column=1, padx=10, pady=5)
slider_dosis.set(50000)  # Valor por defecto 

# Slider para temperatura en Celsius (20 a 50)
tk.Label(frame_calculo, text="Temperatura del experimento (°C):").grid(row=2, column=0, padx=10, pady=5, sticky="w")
slider_temp = tk.Scale(frame_calculo, from_=20, to=50, orient=tk.HORIZONTAL, length=300)
slider_temp.grid(row=2, column=1, padx=10, pady=5)
slider_temp.set(25)  # Valor por defecto 

btn_calcular = tk.Button(frame_calculo, text="Set", command=calcularcm)
btn_calcular.grid(row=3, column=0, columnspan=2, pady=10)

resultado = tk.StringVar()
tk.Label(frame_calculo, textvariable=resultado, fg="blue", font=("Arial", 11)).grid(row=4, column=0, columnspan=2, pady=10)

btn_volver = tk.Button(frame_calculo, text="Regresar", command=lambda: mostrar_inicio())
btn_volver.grid(row=5, column=0, columnspan=2, pady=5)

# === Frame para mostrar lecturas de sensores ===
frame_sensores = tk.Frame(root)
labels_sensores = {}

def crear_vista_sensores():
    tk.Label(frame_sensores, text="Lecturas en tiempo real", font=("Arial", 16)).grid(row=0, column=0, columnspan=2, pady=10)

    campos = [
        "Temperatura1 (DS18B20-1)",
        "Temperatura2 (DS18B20-2)",
        "Temperatura3 (DS18B20-3)",
        "Temperatura4 (DS18B20-4)",
        "Humedad1 (DHT22-1)",
        "Humedad2 (DHT22-2)",
        "Temperatura5 (DHT22-1)",
        "Temperatura6 (DHT22-2)",
        "UV"
    ]

    for idx, campo in enumerate(campos):
        tk.Label(frame_sensores, text=campo + ":").grid(row=idx+1, column=0, padx=10, sticky="w")
        lbl = tk.Label(frame_sensores, text="---")
        lbl.grid(row=idx+1, column=1, sticky="w")
        labels_sensores[campo] = lbl

    tk.Button(frame_sensores, text="Volver al inicio", command=mostrar_inicio).grid(row=len(campos)+2, column=0, columnspan=2, pady=10)

# Función para actualizar lecturas de sensores
def actualizar_lecturas():
    with data_lock:
        data = latest_data

    if data:
        labels_sensores["Temperatura1 (DS18B20-1)"].config(text=f"{data['Temperatura1']:.2f} °C")
        labels_sensores["Temperatura2 (DS18B20-2)"].config(text=f"{data['Temperatura2']:.2f} °C")
        labels_sensores["Temperatura3 (DS18B20-3)"].config(text=f"{data['Temperatura3']:.2f} °C")
        labels_sensores["Temperatura4 (DS18B20-4)"].config(text=f"{data['Temperatura4']:.2f} °C")
        labels_sensores["Humedad1 (DHT22-1)"].config(text=f"{data['Humedad1']:.2f} %")
        labels_sensores["Humedad2 (DHT22-2)"].config(text=f"{data['Humedad2']:.2f} %")
        labels_sensores["Temperatura3 (DHT22-1)"].config(text=f"{data['Temperatura5']:.2f} °C")
        labels_sensores["Temperatura4 (DHT22-2)"].config(text=f"{data['Temperatura6']:.2f} °C")
        labels_sensores["UV"].config(text=f"{data['UV1']}")
    else:
        for lbl in labels_sensores.values():
            lbl.config(text="---")

    # Actualiza cada 2000 ms (2 segundos)
    frame_sensores.after(1000, actualizar_lecturas)

# === Funciones para cambiar entre frames ===
def mostrar_settings():
    frame_inicio.pack_forget()
    frame_calculo.pack(expand=True)

def mostrar_inicio():
    frame_sensores.pack_forget()
    frame_calculo.pack_forget()
    frame_inicio.pack(expand=True)

def mostrar_sensores():
    frame_inicio.pack_forget()
    frame_sensores.pack(expand=True)
    actualizar_lecturas()

crear_vista_sensores()

# === Ejecutar ventana ===
root.mainloop()


class GUIdeploy:
    def _init_(self,master):
        self.master = master
        master.title("Cámara de Irradiación")
        master.geometry("700x700")
        master.resizable(False, False)

        