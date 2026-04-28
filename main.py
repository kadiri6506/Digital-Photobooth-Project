import cv2
import os
import time
import numpy as np
import sys
import re
import tkinter as tk
from tkinter import simpledialog

# --- SETTINGS ---
proje_klasoru = os.path.dirname(os.path.abspath(__file__))
cerceve_klasoru = os.path.join(proje_klasoru, "frames")
cikti_klasoru = os.path.join(proje_klasoru, "outputs")

os.makedirs(cerceve_klasoru, exist_ok=True)
os.makedirs(cikti_klasoru, exist_ok=True)
WELCOME_PATH = ""

# Is the file path empty?
if WELCOME_PATH != "" and os.path.exists(WELCOME_PATH):
    welcome_img = cv2.imread(WELCOME_PATH)
    welcome_img = cv2.resize(welcome_img, (1280, 720))
else:
    welcome_img = np.zeros((720, 1280, 3), dtype=np.uint8)

# ADD LOGO
logo_mini = cv2.imread("ADD YOUR LOGO")

if logo_mini is not None:
    desired_width = 500 
    aspect_ratio = desired_width / logo_mini.shape[1]
    desired_height = int(logo_mini.shape[0] * aspect_ratio)
    logo_mini = cv2.resize(logo_mini, (desired_width, desired_height))
    x_offset = (1280 - desired_width) // 2 
    y_offset = 20
    welcome_img[y_offset:y_offset+desired_height, x_offset:x_offset+desired_width] = logo_mini

SABLON_AYARLARI = {
    "Frame1.png": [
        (39, 38, 456, 380),
        (39, 457, 456, 380),
        (39, 876, 456, 380)
    ],
    "Frame2.png": [
        (36, 57, 461, 385),
        (36, 477, 461, 385),
        (36, 897, 461, 385)
    ],
    "Frame3.png": [
        (36, 57, 461, 385),
        (36, 477, 461, 385),
        (36, 897, 461, 385)
    ],
    "default": [(50, 50, 600, 400), (50, 500, 600, 400), (50, 950, 600, 400)]
}

cerceve_dosyalari = [f for f in os.listdir(cerceve_klasoru) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
guncel_index = 0
user_email = ""
app_state = "GIRIS" # ENTRY, SELECTION, SHOOTING

cap = cv2.VideoCapture(1) # 1 for Iriun webcam, 0 for internal webcam
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

cv2.namedWindow('Digifest', cv2.WINDOW_NORMAL)
cv2.setWindowProperty('Digifest', cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

# --- FUNCTİONS ---

def get_email_popup():
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    email = simpledialog.askstring("", "Please Enter Your Mail Adress:", parent=root) #Save the names of the images by email.
    root.destroy()
    return email if email else "anonymous_user"

def dosya_ismi_temizle(email):
    return re.sub(r'[\\/*?:"<>|]', "_", email)

def kutuya_sigdir_oval(img, tw, th, radius=75, feather=15):
    h, w = img.shape[:2]
    scale = max(tw / w, th / h)
    res = cv2.resize(img, (int(w*scale)+1, int(h*scale)+1))
    sx, sy = (res.shape[1]-tw)//2, (res.shape[0]-th)//2
    cropped = cv2.resize(res[sy:sy+th, sx:sx+tw], (tw, th))

    mask = np.zeros((th, tw), dtype=np.uint8)
    r = min(radius, tw // 2, th // 2)
    cv2.rectangle(mask, (r, 0), (tw - r, th), 255, -1)
    cv2.rectangle(mask, (0, r), (tw, th - r), 255, -1)
    for c in [(r, r), (tw - r, r), (r, th - r), (tw - r, th - r)]:
        cv2.circle(mask, c, r, 255, -1)
    
    mask_3d = cv2.cvtColor(cv2.GaussianBlur(mask, (0, 0), feather), cv2.COLOR_GRAY2BGR).astype(float) / 255.0
    return cropped, mask_3d

def tam_ekrana_sigdir(img, ew=1920, eh=1080):
    h, w = img.shape[:2]
    s = min(ew/w, eh/h)
    canvas = np.zeros((eh, ew, 3), dtype=np.uint8)
    if s > 0:
        nw, nh = int(w*s), int(h*s)
        res = cv2.resize(img, (nw, nh))
        canvas[(eh-nh)//2:(eh-nh)//2+nh, (ew-nw)//2:(ew-nw)//2+nw] = res
    return canvas

def akilli_overlay(background, overlay_img):
    bg_h, bg_w = background.shape[:2]
    overlay_res = cv2.resize(overlay_img, (bg_w, bg_h))
    if overlay_res.shape[2] == 4:
        alpha = overlay_res[:, :, 3] / 255.0
        for c in range(3):
            background[:, :, c] = (alpha * overlay_res[:, :, c] + (1 - alpha) * background[:, :, c]).astype(np.uint8)
    else:
        gray = cv2.cvtColor(overlay_res, cv2.COLOR_BGR2GRAY)
        _, mask = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)
        mask_inv = cv2.bitwise_not(mask)
        fg = cv2.bitwise_and(overlay_res, overlay_res, mask=mask)
        bg = cv2.bitwise_and(background, background, mask=mask_inv)
        background[:] = cv2.add(fg, bg)
    return background

# --- MAIN LOOP ---
while cap.isOpened():
    success, frame = cap.read()
    if not success: break
    frame = cv2.flip(frame, 1)
    hf, wf = frame.shape[:2]
    frame_clean = frame[int(hf*0.05):int(hf*0.95), int(wf*0.05):int(wf*0.95)]

    display_img = np.zeros((720, 1280, 3), dtype=np.uint8)

    if app_state == "GIRIS": #Entry
        display_img = welcome_img.copy()
        
        if int(time.time() * 2) % 2 == 0:
             cv2.putText(display_img, "SPACE TO CONTINUE", (400, 600), 
                         cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
    elif app_state == "SECIM": #selection
        dosya_adi = cerceve_dosyalari[guncel_index]
        sablon_img = cv2.imread(os.path.join(cerceve_klasoru, dosya_adi), cv2.IMREAD_UNCHANGED)
        
        # UI Paneli
        cam_mini = cv2.resize(frame_clean, (700, 400))
        display_img[100:500, 50:750] = cam_mini
        if sablon_img is not None:
            sh, sw = sablon_img.shape[:2]
            s_scale = 500 / sh
            s_mini = cv2.resize(sablon_img[:,:,:3], (int(sw*s_scale), 500))
            display_img[80:580, 850:850+s_mini.shape[1]] = s_mini
        
        cv2.putText(display_img, f"Welcome: {user_email}", (50, 50), 1, 1.2, (255, 255, 0), 1)
        cv2.putText(display_img, "[N]: Change Frame | [S]: Start Shooting", (350, 650), 1, 1.8, (0, 255, 0), 2)

    cv2.imshow('YOUR EVENTS NAME', tam_ekrana_sigdir(display_img))
    key = cv2.waitKey(1) & 0xFF

    if key == ord('q'): break

    if app_state == "GIRIS" and key == 32: # SPACE and ENTRY
        user_email = get_email_popup()
        app_state = "SECIM" #selection 

    if app_state == "SECIM": #selection
        if key == ord('n'):
            guncel_index = (guncel_index + 1) % len(cerceve_dosyalari)
        
        if key == ord('s'):
            kutular = SABLON_AYARLARI.get(dosya_adi, SABLON_AYARLARI["default"])
            cekilenler = []
            for i in range(len(kutular)):
                st = time.time()
                while time.time() - st < 3:
                    _, p = cap.read()
                    p = cv2.flip(p, 1)[int(hf*0.05):int(hf*0.95), int(wf*0.05):int(wf*0.95)]
                    g = p.copy()
                    cv2.putText(g, str(3-int(time.time()-st)), (wf//2-50, hf//2), 1, 8, (0,0,255), 12)
                    cv2.imshow('Digifest', tam_ekrana_sigdir(g))
                    cv2.waitKey(1)
                cekilenler.append(p)
                cv2.imshow('Digifest', np.full((1080,1920,3), 255, np.uint8)); cv2.waitKey(100)

            # Combination
            final_kolaj = np.ones((sh, sw, 3), dtype=np.uint8) * 255 
            for idx, foto in enumerate(cekilenler):
                x, y, wk, hk = kutular[idx]
                islenmis, maske = kutuya_sigdir_oval(foto, wk, hk)
                roi = final_kolaj[y:y+hk, x:x+wk].astype(float)
                blended = (islenmis.astype(float) * maske) + (roi * (1.0 - maske))
                final_kolaj[y:y+hk, x:x+wk] = blended.astype(np.uint8)

            final_kolaj = akilli_overlay(final_kolaj, sablon_img)
            dosya_adi_kayit = f"{dosya_ismi_temizle(user_email)}_{int(time.time())}.jpg"
            cv2.imwrite(os.path.join(cikti_klasoru, dosya_adi_kayit), final_kolaj)
            
            cv2.imshow('Digifest', tam_ekrana_sigdir(final_kolaj))
            cv2.waitKey(5000)
            app_state = "GIRIS" # Return start

cap.release()
cv2.destroyAllWindows()