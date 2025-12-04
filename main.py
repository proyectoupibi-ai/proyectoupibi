from backend import *
from front import *


if __name__ == "__main__":
    #root = tk.Tk()
    #app = GUIdeploy(root, data_lock=data_lock, latest_data=latest_data)
    #root.mainloop()

    threading.Thread(target=thread_DS18B20, daemon=True).start()
    threading.Thread(target=thread_DHT_UV, daemon=True).start()
    threading.Thread(target=thread_guardado, daemon=True).start()

    root = tk.Tk()
    app = GUIdeploy(root)
    app.conectar_backend(latest_data, data_lock, guardar_event, paro_eme)
    
    root.mainloop()