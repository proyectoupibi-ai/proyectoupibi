#control y GUI
import tkinter as tk
from tkinter import messagebox
import threading
from backend import *
import numpy as np
import matplotlib as plt

# === CONFIGURACION THREADS ===
# Variables compartidas Threading 
#paro_eme = threading.Event()
#paro_eme.set()  # Por defecto, el hilo sigue corriendo

# datos globales 
Dstcl = 0
Tiempo = 1
Temperatura = 20
Dosis = 1
runing = 0

Dist, Irrad = config()

# === Función de cálculo ===
#1 J/m2 = W*s/m2


class GUIdeploy:
    def __init__(self,root):
        master = root
        self.master = master
        master.title("Cámara de Irradiación")
        master.geometry("700x700")
        master.resizable(False, False)

        self.remaining_time = 0
        self.total_duration = 0
        self.runing = 0

        # ====== FRAMES ======
        self.frame_inicio = tk.Frame(master)
        self.frame_calculo = tk.Frame(master)
        self.frame_sensores = tk.Frame(master)

        self.labels_sensores = {}
        self.parado = tk.BooleanVar(value=False)

        #Construir Frames
        self.ventana_inicio()
        self.ventana_settings()
        self.ventana_sensores()

        # Mostrar vista inicial
        self.mostrar_inicio()

    def conectar_backend(self, latest_data, data_lock, guardar_event, paro_eme):
        self.latest_data = latest_data
        self.data_lock = data_lock
        self.guardar_event = guardar_event
        self.paro_eme = paro_eme

    def fmt(self, val, suf="", nd=2):
        if val is None:
            return "---"
        try:
            return f"{val:.{nd}f}{suf}"
        except Exception:
            return "---"

    def fmt_raw(self, val):
        return "---" if val is None else str(val)
    

    #-----DEFINICION DE FRAMES-----
        
    def ventana_inicio(self):
        f = self.frame_inicio

        self.label_tiempo = tk.Label(f, text="Tiempo restante: --:--", font=("Arial", 14), fg="darkorange")
        self.label_tiempo.pack(pady=10)

        tk.Button(f, text="Configuración", width=45, height=3,
                command=self.mostrar_settings).pack()

        tk.Button(f, text="Ver Lecturas de Sensores",
                width=45, height=3,
                command=self.mostrar_sensores).pack(pady=10)

        tk.Button(f, text="Iniciar experimento",
                width=45, height=3,
                bg="lightgray",
                command=self.INICIO).pack(pady=10)

        self.btn_STOP = tk.Button(f, text="PARO DE EMERGENCIA",
                bg="yellow",fg="black", width=45,
                height=3, font=("Arial", 11, "bold"),
                command=self.toggle_paro)
        self.btn_STOP.pack(pady=10)

        tk.Button(f, text="CARGAR / RETIRAR MUESTRAS",
                width=45, height=3,
                command=self.muestras).pack(pady=10)
            
    def ventana_settings(self):
        f = self.frame_calculo

        tk.Label(f, text="Tiempo del experimento (min):").grid(row=0, column=0, sticky="w", padx=10)
        self.slider_tiempo = tk.Scale(f, from_=1, to=600, orient="horizontal", length=300)
        self.slider_tiempo.grid(row=0, column=1, pady=5)
        self.slider_tiempo.set(300)

        tk.Label(f, text="Dosis (J/m2):").grid(row=1, column=0, sticky="w", padx=10)
        self.slider_dosis = tk.Scale(f, from_=0, to=100000, resolution=1000, orient="horizontal", length=300)
        self.slider_dosis.grid(row=1, column=1)
        self.slider_dosis.set(50000)

        tk.Label(f, text="Temperatura del experimento (°C):").grid(row=2, column=0, sticky="w", padx=10)
        self.slider_temp = tk.Scale(f, from_=20, to=50, orient="horizontal", length=300)
        self.slider_temp.grid(row=2, column=1)
        self.slider_temp.set(25)

        tk.Button(f, text="Set", command=self.calcularcm).grid(row=3, column=0, columnspan=2, pady=10)

        self.resultado = tk.StringVar()
        tk.Label(f, textvariable=self.resultado, fg="blue").grid(row=4, column=0, columnspan=2, pady=10)

        tk.Button(f, text="Regresar", command=self.mostrar_inicio).grid(row=5, column=0, columnspan=2, pady=10)

    def ventana_sensores(self):
        f = self.frame_sensores

        tk.Label(f, text="Lecturas en tiempo real", font=("Arial", 16)).grid(row=0, column=0, columnspan=2, pady=10)

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

        for i, campo in enumerate(campos):
            tk.Label(f, text=campo + ":").grid(row=i+1, column=0, sticky="w", padx=10)
            lbl = tk.Label(f, text="---")
            lbl.grid(row=i+1, column=1, sticky="w")
            self.labels_sensores[campo] = lbl

        tk.Button(f, text="Volver al inicio", command=self.mostrar_inicio).grid(row=len(campos)+2, column=0, columnspan=2, pady=10)

    def actualizar_lecturas(self):

        with self.data_lock:
            data = self.latest_data.copy()

        # DS18B20
        self.labels_sensores["Temperatura1 (DS18B20-1)"].config(
            text=self.fmt(data.get('Temperatura1'), " °C")
        )
        self.labels_sensores["Temperatura2 (DS18B20-2)"].config(
            text=self.fmt(data.get('Temperatura2'), " °C")
        )
        self.labels_sensores["Temperatura3 (DS18B20-3)"].config(
            text=self.fmt(data.get('Temperatura3'), " °C")
        )
        self.labels_sensores["Temperatura4 (DS18B20-4)"].config(
            text=self.fmt(data.get('Temperatura4'), " °C")
        )

        # DHT22 – Humedad
        self.labels_sensores["Humedad1 (DHT22-1)"].config(
            text=self.fmt(data.get('Humedad1'), " %")
        )
        self.labels_sensores["Humedad2 (DHT22-2)"].config(
            text=self.fmt(data.get('Humedad2'), " %")
        )

        # DHT22 – Temperatura
        self.labels_sensores["Temperatura5 (DHT22-1)"].config(
            text=self.fmt(data.get('Temperatura5'), " °C")
        )
        self.labels_sensores["Temperatura6 (DHT22-2)"].config(
            text=self.fmt(data.get('Temperatura6'), " °C")
        )

        # UV
        self.labels_sensores["UV"].config(
            text=self.fmt_raw(data.get('UV1'))
        )

        # volver a llamar cada segundo
        self.frame_sensores.after(1000, self.actualizar_lecturas)

    #-----CAMBIAR ENTRE FRAMES-----
    def mostrar_inicio(self):
        self.frame_calculo.pack_forget()
        self.frame_sensores.pack_forget()
        self.frame_inicio.pack(expand=True)

    def mostrar_settings(self):
        self.frame_inicio.pack_forget()
        self.frame_sensores.pack_forget()
        self.frame_calculo.pack(expand=True)

    def mostrar_sensores(self):
        self.frame_inicio.pack_forget()
        self.frame_calculo.pack_forget()
        self.frame_sensores.pack(expand=True)
        self.actualizar_lecturas()

    #---FUNCIONES EXTRA----

    def actualizar_tiempo_restante(self):
        if self.remaining_time > 0:
            minutos = int(self.remaining_time // 60)
            segundos = int(self.remaining_time % 60)
            self.label_tiempo.config(text=f"Tiempo restante: {minutos:03d} min {segundos:02d} s")
        else:
            self.label_tiempo.config(text="Experimento finalizado.")

        self.master.after(1000, self.actualizar_tiempo_restante)

    def INICIO(self):
        try:
            Tiempo = self.slider_tiempo.get()
            self.total_duration = Tiempo * 60
            self.remaining_time = self.total_duration
            self.start_time = time.time()

            self.paro_eme.set()     #viene del backend
            self.guardar_event.set()  #viene del backend

            threading.Thread(target=thread_Control, daemon=True).start()
            threading.Thread(target=thread_time, daemon=True).start()

            self.runing = 1
            self.actualizar_tiempo_restante()

            self.btn_INICIO.config(bg="green", fg="white", text="Experimento en curso")

            print(f"Experimento iniciado {Tiempo} minutos")

            def check_end():
                if self.remaining_time <= 0:
                    self.btn_INICIO.config(bg="lightgray", fg="black", text="Iniciar experimento")
                else:
                    self.master.after(1000, check_end)

            check_end()

        except Exception as e:
            messagebox.showerror("Error", f"Ocurrió un error: {e}")

    
    def cargar(self):
        print("colocar o retirar muestras")

    def muestras(self):
        try:
            # Usar variables internas de la clase
            if self.remaining_time == 0:
                self.cargar()
            elif self.runing == 0:
                self.cargar()
            else:
                messagebox.showerror("Error", "Experimento en curso")
        except Exception:
            messagebox.showerror("Error", "Experimento en curso")

    def toggle_paro(self):
        if self.parado.get():
            #REANUDAR
            self.paro_eme.set()
            self.btn_STOP.config(
                text="PARO DE EMERGENCIA",
                bg="yellow",
                fg="black"
            )
            self.parado.set(False)
            self.runing = 1
            print("Experimento reanudado.")

        else:
            #PARO
            self.paro_eme.clear()
            self.btn_STOP.config(
                text="REANUDAR",
                bg="red",
                fg="white"
            )
            self.parado.set(True)
            self.runing = 0
            print("Experimento pausado.")

    def calcularcm(self):
        try:
            Time = self.slider_tiempo.get()
            Dosis = self.slider_dosis.get()
            Temperatura = self.slider_temp.get()

            if Time <= 0:
                messagebox.showerror("Error", "El tiempo debe ser mayor a 0")
                return

            # Calcular irradiancia requerida
            Irradiancia = Dosis / (Time * 60)
            Irradiancia *= 1000   # convertir a mW/m2

            # Buscar valor más cercano en la tabla de irradiancias
            idx = np.argmin(np.abs(Irrad - Irradiancia))
            Dstcl = Dist[idx]
            Irrdcl = Irrad[idx]

            # Validación de límites
            if Irradiancia > Irrad[0]:
                messagebox.showerror("Error", "Irradiancia máxima, aumentar tiempo")
                return
            elif Irradiancia < Irrad[-1]:
                messagebox.showerror("Error", "Irradiancia mínima, disminuir tiempo")
                return

            # Resultados si coincide exactamente
            if Irrdcl == Irradiancia:
                self.resultado.set(
                    f"Para irradiancia ≈ {Irradiancia:.2f} mW/m2,\n"
                    f"Distancia ≈ {Dstcl:.3f} cm (valor interpolado ≈ {Irrdcl:.2f})"
                )

            else:
                # nuevo tiempo requerido
                Irrdrl = Irrdcl / 1000
                tiemposec = Dosis / (Irrdrl * 60)

                self.resultado.set(
                    f"Para irradiancia ≈ {Irradiancia:.2f} mW/m2,\n"
                    f"Distancia ≈ {Dstcl:.3f} cm (valor interpolado ≈ {Irrdcl:.2f})\n"
                    f"Tiempo solicitado = {Time} min\n"
                    f"Nuevo tiempo requerido = {tiemposec:.2f} s"
                )

                # Ajusta el control deslizante con el nuevo tiempo
                self.slider_tiempo.set(tiemposec / 60)

            # Graficar
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