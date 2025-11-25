import cv2
import face_recognition
import os
import psutil
import tkinter as tk
from PIL import Image, ImageTk
from tkinter import messagebox
import ctypes
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import requests
from flask import Flask, request
from pyngrok import ngrok
import threading
import numpy as np
import pyautogui
import time
import pickle
from datetime import datetime
from insightface.app import FaceAnalysis
from scipy.spatial.distance import cosine

# Paths and global variables
AUTH_PASSWORD = "enter password"
sender_email = "enter sender mail"
sender_password = " enter password"
alert_sent = False
recording = False
ngrok_url = None
video_file_path = "unauthorized_attempt_1min_clip.mp4"
shutdown_triggered = False
usb_blocked = False
usb_timer_thread = None

# Flask and Ngrok setup
app = Flask(__name__)
ngrok_tunnel = None

# ---------------------- Logging ----------------------

def write_log(message):
    if not os.path.exists("logs"):
        os.makedirs("logs")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open("logs/security_log.txt", "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")

# ---------------------- Location ----------------------

def save_location():
    try:
        ip_info = requests.get("http://ip-api.com/json/").json()
        location_data = {
            "ip": ip_info.get("query"),
            "city": ip_info.get("city"),
            "region": ip_info.get("regionName"),
            "country": ip_info.get("country"),
            "lat": ip_info.get("lat"),
            "lon": ip_info.get("lon"),
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        if not os.path.exists("logs"):
            os.makedirs("logs")
        with open("logs/location_log.txt", "a") as loc_file:
            loc_file.write(f"{location_data}\n")
        write_log("📍 Location info saved locally.")
    except Exception as e:
        write_log(f"❌ Failed to get location: {e}")

# ---------------------- USB Control -------------------------------------------------------------------------------------------------------------------

def block_usb_ports():
    global usb_blocked
    try:
        os.system("reg add HKLM\\SYSTEM\\CurrentControlSet\\Services\\USBSTOR /v Start /t REG_DWORD /d 4 /f")
        usb_blocked = True
        print("USB ports blocked.")
        write_log("🔐 USB ports have been blocked.")
    except Exception as e:
        print(f"Failed to block USB ports: {e}")

def unblock_usb_ports():
    global usb_blocked
    try:
        os.system("reg add HKLM\\SYSTEM\\CurrentControlSet\\Services\\USBSTOR /v Start /t REG_DWORD /d 3 /f")
        usb_blocked = False
        print("USB ports unblocked.")
        write_log("🔓 USB ports have been unblocked.")
    except Exception as e:
        print(f"Failed to unblock USB ports: {e}")

# ---------------------- Webcam Face Capture -------------------------------------------------------------------------------------------------------------

def capture_face_with_preview():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Cannot open webcam")
        return None

    captured_frame = [None]  # Use list for mutable closure

    def show_frame():
        ret, frame = cap.read()
        if ret:
            cv2image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(cv2image)
            imgtk = ImageTk.PhotoImage(image=img)
            lmain.imgtk = imgtk
            lmain.configure(image=imgtk)
        lmain.after(10, show_frame)

    def capture():
        ret, frame = cap.read()
        if ret:
            captured_frame[0] = frame
            root.destroy()  # Close window

    root = tk.Tk()
    root.title("Face Registration - Look at the Camera")

    lmain = tk.Label(root)
    lmain.pack()

    btn_capture = tk.Button(root, text="Capture", command=capture)
    btn_capture.pack()

    show_frame()
    root.mainloop()
    cap.release()

    return captured_frame[0]

# ---------------------- Registration ---------------------------------------------------------------------------------------------------------------------


def prompt_for_email():
    def submit():
        nonlocal user_email
        user_email = email_entry.get()
        root.destroy()

    user_email = ""
    root = tk.Tk()
    root.title("Enter Email")
    root.geometry("400x150")
    tk.Label(root, text="Enter your email for intruder alerts:", font=("Arial", 12)).pack(padx=20, pady=20)
    email_entry = tk.Entry(root, width=40, font=("Arial", 12))
    email_entry.pack(pady=5)
    email_entry.focus_set()
    tk.Button(root, text="Submit", command=submit, font=("Arial", 12)).pack(pady=10)
    root.mainloop()
    return user_email

def register_user():
    try:
        print("Starting user registration...")
        model = FaceAnalysis(name="buffalo_l")
        model.prepare(ctx_id=0)

        face_img = capture_face_with_preview()
        if face_img is None:
            print("Face capture failed.")
            return False

        if not os.path.exists("registered"):
            os.makedirs("registered")

        image_path = "registered/user_face.jpg"
        cv2.imwrite(image_path, face_img)
        print("Face image saved successfully.")

        face_data = model.get(face_img)
        if not face_data:
            print("Failed to generate face embedding.")
            return False

        face_embedding = face_data[0].embedding

        user_email = prompt_for_email()
        if not user_email:
            print("No email entered. Registration aborted.")
            return False

        with open("user_email.txt", "w") as f:
            f.write(user_email)

        with open("user_data.pkl", "wb") as f:
            pickle.dump({'email': user_email, 'embedding': face_embedding}, f)

        print("User registration completed successfully.")
        return True

    except Exception as e:
        print(f"Error during registration: {e}")
        return False
# ---------------------- Internet & Email ----------------------------------------------------------------------------------------------------------------

def check_internet():
    try:
        response = requests.get('https://www.google.com', timeout=5)
        return response.status_code == 200
    except requests.RequestException:
        return False

def send_email_with_attachment(subject, body, recipient_email, attachment_path=None):
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    if attachment_path:
        try:
            with open(attachment_path, 'rb') as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', f'attachment; filename={os.path.basename(attachment_path)}')
                msg.attach(part)
        except Exception as e:
            print(f"Failed to attach file: {e}")

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, recipient_email, msg.as_string())
        server.quit()
        print("Email sent successfully!")
        write_log("📧 Intruder alert email sent with image and/or recording.")
    except Exception as e:
        print(f"Failed to send email: {e}")

# ---------------------- Flask Routes ---------------------------------------------------------------------------------------------------------------------

@app.route("/shutdown", methods=["GET"])
def shutdown():
    user_response = request.args.get('response')
    global shutdown_triggered

    unblock_usb_ports()

    if user_response == "no":
        shutdown_triggered = True
        os.system("shutdown /s /t 1")
        return "System is shutting down..."
    return "Shutdown canceled. USB ports have been unblocked."

def start_flask_server():
    app.run(host="0.0.0.0", port=5000)

def start_ngrok():
    global ngrok_tunnel
    ngrok.set_auth_token(" enter ngrok token")
    ngrok_tunnel = ngrok.connect(5000)
    print(f"Ngrok tunnel \"{ngrok_tunnel.public_url}\" is live")
    return ngrok_tunnel.public_url

# ---------------------- Authentication Lock Screen -------------------------------------------------------------------------------------------------------

def authenticate(overlay):
    def check_password():
        global usb_timer_thread
        if password_entry.get() == AUTH_PASSWORD:
            if usb_timer_thread and usb_timer_thread.is_alive():
                usb_timer_thread.cancel()
            unblock_usb_ports()
            write_log("✅ Freeze screen unlocked by user. USB ports unblocked.")
            overlay.destroy()
        else:
            messagebox.showerror("Authentication Failed", "Incorrect Password!")

    overlay.title("System Locked")
    overlay.geometry("400x200")
    overlay.attributes("-fullscreen", True)
    overlay.attributes("-topmost", True)
    overlay.protocol("WM_DELETE_WINDOW", lambda: None)

    tk.Label(overlay, text="System Locked! Unauthorized Access Detected.", font=("Arial", 14)).pack(pady=20)
    tk.Label(overlay, text="Enter Password:", font=("Arial", 12)).pack()

    password_entry = tk.Entry(overlay, show="*", font=("Arial", 12))
    password_entry.pack(pady=10)
    password_entry.focus_set()

    tk.Button(overlay, text="Unlock", command=check_password, font=("Arial", 12)).pack(pady=20)
    overlay.mainloop()

def freeze_system():
    write_log("🧊 System freeze triggered (offline mode).")
    overlay = tk.Tk()
    authenticate(overlay)

# ---------------------- Screen Recording -----------------------------------------------------------------------------------------------------------------
def record_screen(output_file, email):
    global recording
    original_screen_size = pyautogui.size()
    screen_size = (int(original_screen_size[0] * 0.5), int(original_screen_size[1] * 0.5))  # Compress to 50%
    codec = cv2.VideoWriter_fourcc(*"mp4v")  # Ensure compatibility with .mp4
    fps = 2.0  # Reduce FPS to lower file size
    video_writer = cv2.VideoWriter(output_file, codec, fps, screen_size)

    print("Screen recording started...")
    recording = True
    start_time = time.time()

    while recording:
        screenshot = pyautogui.screenshot()
        frame = np.array(screenshot)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame = cv2.resize(frame, screen_size)  # Compress frame
        video_writer.write(frame)

        if time.time() - start_time > 60:
            video_writer.release()
            print(f"Screen recording saved: {output_file}")
            send_email_with_attachment(
                "Unauthorized Login Screen Recording",
                "See the attached compressed 1-minute video.",
                email,
                output_file
            )
            output_file = f"unauthorized_attempt_{int(time.time())}.mp4"
            video_writer = cv2.VideoWriter(output_file, codec, fps, screen_size)
            start_time = time.time()

    video_writer.release()

# ---------------------- Face Monitoring -----------------------------------------------------------------------------------------------------------

def monitor_faces():
    global alert_sent, ngrok_url, recording, shutdown_triggered, usb_timer_thread

    if not os.path.exists("registered/user_face.jpg") or not os.path.exists("user_email.txt"):
        print("User not registered. Exiting...")
        return

    # Load user face image and extract embedding
    model = FaceAnalysis(name="buffalo_l")
    model.prepare(ctx_id=0)

    user_image = cv2.imread("registered/user_face.jpg")
    user_faces = model.get(user_image)
    if not user_faces:
        print("Failed to extract user face embedding.")
        return
    user_embedding = user_faces[0].embedding

    with open("user_email.txt", "r") as f:
        user_email = f.read().strip()

    video_capture = cv2.VideoCapture(0)
    intrusion_handled = False

    unauthorized_mode = False   

    while True:
        ret, frame = video_capture.read()
        if not ret:
            print("Camera error.")
            break

        detected_faces = model.get(frame)
        matched = False     

    
        for face in detected_faces:
            distance = cosine(user_embedding, face.embedding)
            if distance < 0.5:
                matched = True
                break

        if not matched and not unauthorized_mode and not shutdown_triggered:
            unauthorized_mode = True  # Set to True to prevent repeated triggers
            print("Unauthorized user detected!")
            write_log("⚠ Unauthorized user detected. Intruder image saved.")
            save_location()
            intrusion_handled = True

            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            if not os.path.exists("intruders"):
                os.makedirs("intruders")
            intruder_image_path = f"intruders/intruder_{timestamp}.jpg"
            cv2.imwrite(intruder_image_path, frame)

            block_usb_ports()

            if usb_timer_thread and usb_timer_thread.is_alive():
                usb_timer_thread.cancel()

            usb_timer_thread = threading.Timer(120, unblock_usb_ports)
            usb_timer_thread.start()

            if check_internet():
                if not ngrok_url:
                    ngrok_url = start_ngrok()

                shutdown_link = f"{ngrok_url}/shutdown?response=no"
                ignore_link = f"{ngrok_url}/shutdown?response=yes"

                email_body = (
                    "A login attempt was made on your laptop. Confirm if it was you:\n\n"
                    f"{shutdown_link} (Shutdown if not you)\n"
                    f"{ignore_link} (Ignore if you authorized this)"
                )

                send_email_with_attachment(
                    subject="\U0001F6A8 Intruder Alert: Unauthorized Access Detected",
                    body=email_body,
                    recipient_email=user_email,
                    attachment_path=intruder_image_path
                )

                recording_thread = threading.Thread(target=record_screen, args=("unauthorized_clip.mp4", user_email))
                recording_thread.start()
            else:
                print("No internet. Freezing system...")
                freeze_system()

            alert_sent = True

        if shutdown_triggered:
            break

        time.sleep(0.1)

    video_capture.release()
    cv2.destroyAllWindows()


# ---------------------- Main -----------------------------------------------------------------------------------------------------------------------------

def main():
    global ngrok_url, shutdown_triggered

    print("Starting the application...")

    # Step 1: Check if the user face encoding and email exist
    if not (os.path.exists("registered/user_face.jpg") and os.path.exists("user_email.txt") and os.path.exists("user_data.pkl")):
        print("No registered user found. Registering now...")
        # Step 2: Register user and check if registration was successful
        if not register_user():
            print("Registration failed. Exiting.")
            return  # Exit if registration fails

    # Step 3: Check if internet connection is available
    if check_internet():
        print("System is online. Starting Ngrok and Flask server...")
        ngrok_url = start_ngrok()  # Assuming ngrok URL is returned
        # Start Flask server in a separate thread
        flask_thread = threading.Thread(target=start_flask_server)
        flask_thread.start()
    else:
        print("No internet connection detected. Entering offline mode...")

    # Step 4: Start monitoring faces
    monitor_faces()

if __name__ == "__main__":
    main()