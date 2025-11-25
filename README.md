🔐 Face Authentication Security System
A Real-Time Intruder Detection, Alerting & Laptop Protection System

This project is a complete laptop security system built using Python that performs:

✔ Face Recognition
✔ Intruder Detection
✔ USB Port Blocking
✔ Email Alerts with Intruder Photo
✔ Location Logging
✔ Screen Recording
✔ Remote Shutdown (via Flask + Ngrok)
✔ Offline Freeze Protection

It protects your laptop from unauthorized access attempts in real time.

🚀 Features
🔵 Face Registration

Captures a live face image using webcam

Extracts embeddings using InsightFace (buffalo_l)

Saves:

registered/user_face.jpg

user_data.pkl

user_email.txt

🔴 Real-Time Intruder Detection

Webcam continuously monitors faces

Compares detected face with registered owner

Uses cosine similarity threshold (0.5)

If mismatch → triggers intruder alert logic

⚠️ Security Actions on Intruder Detection
📵 Offline Mode (No Internet)

Locks system with a full-screen Tkinter window

User must enter AUTH_PASSWORD to unlock

🌐 Online Mode (Internet Available)

Starts Ngrok tunnel

Generates secure links:

Shutdown

Ignore

Sends an email with:
✔ Intruder photo
✔ Location
✔ Shutdown/Ignore links

⛔ USB Port Blocking

Blocks USB storage immediately:

reg add HKLM\SYSTEM\CurrentControlSet\Services\USBSTOR /v Start /t REG_DWORD /d 4 /f


Unblocks after 120 seconds or on password verification.

🎥 Screen Recording

Records the screen using pyautogui

Saves compressed .mp4 files

Sends 1-minute clips via email every 60 seconds

🌍 Location Tracking

Uses ip-api.com
Stores:

IP Address

City

Region

Country

Latitude & Longitude

Timestamp

All written to logs/location_log.txt.

🌐 Flask + Ngrok Remote Actions

Endpoints:

/shutdown?response=no   → Shutdown system  
/shutdown?response=yes  → Ignore & unblock USB  

📁 Project Structure
Face Authentication Security App.py
registered/
    user_face.jpg
    user_data.pkl
intruders/
    intruder_YYYY-MM-DD_HH-MM-SS.jpg
logs/
    security_log.txt
    location_log.txt
user_email.txt
unauthorized_clip.mp4

🛠️ Technologies Used

Python

OpenCV

InsightFace (buffalo_l)

Tkinter

Flask

Ngrok

PyAutoGUI

Requests

NumPy

Pickle

Gmail SMTP

📦 Installation
1️⃣ Clone the Repository
git clone <your-repository-url>

2️⃣ Install Dependencies

If you have a requirements.txt:

pip install -r requirements.txt


Or install manually:

pip install opencv-python insightface numpy flask pyngrok pyautogui pillow requests scipy

🔧 Configuration

Open the Python file and update:

AUTH_PASSWORD = "your unlock password"
sender_email = "yourgmail@gmail.com"
sender_password = "your app password"
ngrok.set_auth_token("your ngrok auth token")


⚠️ Gmail requires App Password, not your normal password.

▶️ How to Run

Run the application:

python "Face Authentication Security App.py"

🖥 How It Works (Workflow)

On first run → prompts for face registration & email

Starts webcam-based face monitoring

If intruder detected:

Saves intruder image

Blocks USB ports

Logs event + geolocation

Starts screen recording

Sends email with:

Intruder PHOTO

System LOCATION

ShutDown / Ignore LINKS

Offline mode → screen lock

Online mode → Ngrok remote control
