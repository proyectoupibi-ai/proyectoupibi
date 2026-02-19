from BackendV2 import CamaraUV
from FrontendV2 import GUIdeploy
import threading
import tkinter as tk

if __name__ == "__main__":

    camara = CamaraUV()

    # === HILOS ===
    threading.Thread(target=camara.thread_DS18B20, daemon=True).start()
    threading.Thread(target=camara.thread_DHT_UV, daemon=True).start()
    threading.Thread(target=camara.thread_guardado, daemon=True).start()
    threading.Thread(target=camara.thread_lamps, daemon=True).start()
    threading.Thread(target=camara.thread_CNTRLtemp, daemon=True).start()
    threading.Thread(target=camara.thread_time, daemon=True).start()

    # === GUI ===
    root = tk.Tk()
    app = GUIdeploy(root, camara)
    root.mainloop()