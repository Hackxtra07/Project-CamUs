import cv2
import tkinter as tk
from tkinter import ttk, filedialog
from PIL import Image, ImageTk
import threading
import time
import os

class SafeCameraApp:
    def __init__(self, window):
        self.window = window
        self.window.title("Linux Camera App")
        self.window.geometry("900x650")
        self.window.minsize(600, 400)
        self.window.rowconfigure(0, weight=1)
        self.window.columnconfigure(0, weight=1)

        # Default camera parameters
        self.camera_index = 0
        self.width = 1280
        self.height = 720

        self.cap = None
        self.running = False
        self.is_recording = False
        self.video_writer = None
        self.zoom_level = 1.0
        self.save_dir = os.getcwd()
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.timelapse_var = tk.IntVar()
        self.last_snap = 0
        self.frame = None

        # Video display
        self.video_label = tk.Label(window, bg="black")
        self.video_label.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        # Controls
        controls = tk.Frame(window, bg="#333333")
        controls.grid(row=1, column=0, sticky="ew", padx=10, pady=5)

        btn_style = {"bg": "#4CAF50", "fg": "white", "font": ("Arial", 12, "bold"), "bd": 0, "width": 14, "height":2}

        self.snapshot_btn = tk.Button(controls, text="Take Snapshot", command=self.take_snapshot, **btn_style)
        self.snapshot_btn.grid(row=0, column=0, padx=5, pady=5)

        self.record_btn = tk.Button(controls, text="Start Recording", command=self.toggle_recording, **btn_style)
        self.record_btn.grid(row=0, column=1, padx=5, pady=5)

        self.switch_btn = tk.Button(controls, text="Switch Camera", command=self.switch_camera, **btn_style)
        self.switch_btn.grid(row=0, column=2, padx=5, pady=5)

        self.folder_btn = tk.Button(controls, text="Save Folder", command=self.choose_folder, **btn_style)
        self.folder_btn.grid(row=0, column=3, padx=5, pady=5)

        self.refresh_btn = tk.Button(controls, text="Refresh", command=self.refresh_camera, **btn_style)
        self.refresh_btn.grid(row=0, column=4, padx=5, pady=5)

        # Resolution
        tk.Label(controls, text="Resolution:", bg="#333333", fg="white", font=("Arial", 10, "bold")).grid(row=1, column=0)
        self.resolution_cb = ttk.Combobox(controls, values=["640x480", "1280x720", "1920x1080"])
        self.resolution_cb.current(1)
        self.resolution_cb.grid(row=1, column=1)
        self.resolution_cb.bind("<<ComboboxSelected>>", self.change_resolution)

        # Zoom
        tk.Label(controls, text="Zoom:", bg="#333333", fg="white", font=("Arial", 10, "bold")).grid(row=1, column=2)
        self.zoom_slider = tk.Scale(controls, from_=1.0, to=3.0, resolution=0.1, orient=tk.HORIZONTAL,
                                    command=self.set_zoom, bg="#333333", fg="white", troughcolor="#555555")
        self.zoom_slider.set(1.0)
        self.zoom_slider.grid(row=1, column=3)

        # Countdown
        tk.Label(controls, text="Countdown(sec):", bg="#333333", fg="white", font=("Arial", 10, "bold")).grid(row=2, column=0)
        self.timer_entry = tk.Entry(controls, width=5)
        self.timer_entry.insert(0, "0")
        self.timer_entry.grid(row=2, column=1)

        # Timelapse
        tk.Checkbutton(controls, text="Timelapse", bg="#333333", fg="white",
                       variable=self.timelapse_var, font=("Arial",10,"bold")).grid(row=2, column=2, padx=5, pady=5)
        tk.Label(controls, text="Interval(sec):", bg="#333333", fg="white", font=("Arial",10,"bold")).grid(row=2,column=3)
        self.interval_entry = tk.Entry(controls, width=5)
        self.interval_entry.insert(0,"2")
        self.interval_entry.grid(row=2,column=4)

        # Status bar
        self.status = tk.Label(window, text="Camera Ready", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status.grid(row=3, column=0, sticky="ew")

        # Open camera with initial parameters
        self.open_camera()
        self.update_gui_frame()

    # ------------------ Camera management ------------------ #
    def open_camera(self):
        if self.cap is not None:
            self.cap.release()
            time.sleep(0.2)
        self.cap = cv2.VideoCapture(self.camera_index)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.running = True
        threading.Thread(target=self.video_loop, daemon=True).start()
        self.status.config(text=f"Camera opened at {self.width}x{self.height}")

    def release_camera(self):
        self.running = False
        time.sleep(0.2)
        if self.cap is not None and self.cap.isOpened():
            if self.is_recording:
                self.toggle_recording()
            self.cap.release()
            time.sleep(0.2)

    def refresh_camera(self):
        self.release_camera()
        # Reset all controls
        self.zoom_level = 1.0
        self.zoom_slider.set(1.0)
        self.timer_entry.delete(0, tk.END)
        self.timer_entry.insert(0, "0")
        self.timelapse_var.set(0)
        self.interval_entry.delete(0, tk.END)
        self.interval_entry.insert(0, "2")
        self.open_camera()
        self.status.config(text="Camera refreshed and controls reset")

    def switch_camera(self):
        self.release_camera()
        self.camera_index = 1 - self.camera_index
        self.open_camera()
        self.status.config(text=f"Switched to camera {self.camera_index}")

    def change_resolution(self, event):
        selected_res = self.resolution_cb.get().split("x")
        self.width, self.height = int(selected_res[0]), int(selected_res[1])
        self.release_camera()
        self.open_camera()
        self.status.config(text=f"Resolution changed to {self.width}x{self.height}")

    # ------------------ Video loop ------------------ #
    def video_loop(self):
        while self.running:
            ret, frame = self.cap.read()
            if ret:
                # Face detection
                #gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                #faces = self.face_cascade.detectMultiScale(gray,1.3,5)
                #for (x,y,w,h) in faces:
                    #cv2.rectangle(frame,(x,y),(x+w,y+h),(0,255,0),2)

                # Timelapse
                if self.timelapse_var.get():
                    interval = int(self.interval_entry.get())
                    if time.time() - self.last_snap >= interval:
                        filename = os.path.join(self.save_dir, f"snapshot_{int(time.time())}.png")
                        cv2.imwrite(filename, frame)
                        self.last_snap = time.time()

                if self.is_recording:
                    self.video_writer.write(frame)

                self.frame = frame

    # ------------------ Snapshot and Zoom ------------------ #
    def set_zoom(self, val):
        self.zoom_level = float(val)

    def apply_zoom(self, frame):
        if self.zoom_level != 1.0:
            h, w = frame.shape[:2]
            cx, cy = w//2, h//2
            rx, ry = int(w/(2*self.zoom_level)), int(h/(2*self.zoom_level))
            frame = frame[cy-ry:cy+ry, cx-rx:cx+rx]
            frame = cv2.resize(frame, (w,h))
        return frame

    def take_snapshot(self):
        timer = int(self.timer_entry.get())
        if timer > 0:
            self.status.config(text=f"Taking snapshot in {timer} seconds...")
            self.window.after(timer*1000, self.save_snapshot)
        else:
            self.save_snapshot()

    def save_snapshot(self):
        if self.frame is not None:
            frame = self.apply_zoom(self.frame.copy())
            filename = os.path.join(self.save_dir, f"snapshot_{int(time.time())}.png")
            cv2.imwrite(filename, frame)
            self.status.config(text=f"Snapshot saved as {filename}")

    # ------------------ Video Recording ------------------ #
    def toggle_recording(self):
        if not self.is_recording:
            fourcc = cv2.VideoWriter_fourcc(*'XVID')
            filename = os.path.join(self.save_dir, f"recording_{int(time.time())}.avi")
            self.video_writer = cv2.VideoWriter(filename, fourcc, 20.0, (self.width, self.height))
            self.is_recording = True
            self.record_btn.config(text="Stop Recording", bg="#f44336")
            self.status.config(text=f"Recording started: {filename}")
        else:
            self.is_recording = False
            self.video_writer.release()
            self.record_btn.config(text="Start Recording", bg="#4CAF50")
            self.status.config(text="Recording stopped.")

    # ------------------ Folder ------------------ #
    def choose_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.save_dir = folder
            self.status.config(text=f"Save folder: {folder}")

    # ------------------ GUI Update ------------------ #
    def update_gui_frame(self):
        if self.frame is not None:
            display_frame = self.apply_zoom(self.frame.copy())
            cv2image = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(cv2image)
            imgtk = ImageTk.PhotoImage(image=img)
            self.video_label.imgtk = imgtk
            self.video_label.configure(image=imgtk)
        self.window.after(10, self.update_gui_frame)

    # ------------------ Close ------------------ #
    def close(self):
        self.running = False
        self.release_camera()
        self.window.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = SafeCameraApp(root)
    root.protocol("WM_DELETE_WINDOW", app.close)
    root.mainloop()
