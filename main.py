from backend import *
from front import *


if __name__ == "__main__":

    # === ARRANCAR BACKEND ===
    t1 = threading.Thread(target=thread_DS18B20, daemon=True)
    t2 = threading.Thread(target=thread_DHT_UV, daemon=True)
    t3 = threading.Thread(target=thread_guardado, daemon=True)
    t4 = threading.Thread(target=thread_lamps, daemon=True)
    t5 = threading.Thread(target=thread_CNTRLtemp, daemon=True)
    t6 = threading.Thread(target=thread_time, daemon=True)


    t1.start()
    t2.start()
    t3.start()
    t4.start()
    t5.start()
    t6.start()

    print("[MAIN] Backend iniciado")

    # === ARRANCAR GUI ===

    root = tk.Tk()
    app = GUIdeploy(root)
    app.conectar_backend(latest_data, data_lock, guardar_event, paro_eme)
    root.mainloop()