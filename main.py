from backend import *
from front import *


if __name__ == "__main__":

    # === ARRANCAR BACKEND ===
    t1 = threading.Thread(target=thread_DS18B20, daemon=True)
    t2 = threading.Thread(target=thread_DHT_UV, daemon=True)
    t3 = threading.Thread(target=thread_guardado, daemon=True)

    t1.start()
    t2.start()
    t3.start()

    print("[MAIN] Backend iniciado")

    # === ARRANCAR GUI ===

    root = tk.Tk()
    app = GUIdeploy(root)
    app.conectar_backend(latest_data, data_lock, guardar_event, paro_eme)
    root.mainloop()