import cv2
import cvzone
import math
from ultralytics import YOLO
import os
import smtplib
from email.message import EmailMessage
from datetime import datetime
import time
import threading
from django.utils import timezone  # Import timezone for timezone-aware datetime
from django.conf import settings
from .models import FallLog

def start_fall_detection(system_status, video_path=None):
    """
    Start the fall detection process.
    
    Parameters:
    - system_status (dict): A dictionary to control the active state of the system.
    - video_path (str): Optional. Path to a video file. If None, real-time camera is used.
    """
    from .views import log_fall_event  # Avoid circular import
    
    # Check if video_path is provided; if not, use the camera as the source
    if video_path is None:
        cap = cv2.VideoCapture(0) 
        if not cap.isOpened():
            print("Error: Unable to access the camera.")
            return
    else:
        # For video file, ensure path is valid and accessible
        if not os.path.exists(video_path):
            print(f"Error: File does not exist at {video_path}")
            return
        cap = cv2.VideoCapture(video_path)

    model = YOLO('yolov8s.pt')

    # Load class names
    classnames = []
    file_path = r'C:\Users\shiva\Downloads\Fall-Detection-main\Fall-Detection-main\classes.txt'
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            classnames = f.read().splitlines()
    else:
        print(f"Class names file not found at {file_path}. Exiting.")
        return

    # Email configuration
    EMAIL_ADDRESS = "Your_email"
    EMAIL_PASSWORD = "Your_email_password"  # Replace with environment variables for security
    RECEIVER_EMAIL = "Caretaker's_email"

    # Create the snapshots folder in the MEDIA_ROOT
    snapshots_folder = os.path.join(settings.MEDIA_ROOT, 'snapshots')
    os.makedirs(snapshots_folder, exist_ok=True)

    fall_detected = False
    snapshot_count = 0
    max_snapshots = 3
    fall_detection_time = None

    # Function to send email asynchronously
    def send_email(image_path):
        try:
            msg = EmailMessage()
            msg['Subject'] = 'Fall Detected Alert'
            msg['From'] = EMAIL_ADDRESS
            msg['To'] = RECEIVER_EMAIL
            msg.set_content("A fall has been detected. Please find the snapshot attached.")
            with open(image_path, 'rb') as img:
                msg.add_attachment(img.read(), maintype='image', subtype='jpeg', filename=os.path.basename(image_path))

            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
                smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
                smtp.send_message(msg)

            print("Email sent successfully!")
        except Exception as e:
            print(f"Failed to send email: {e}")

    fps = cap.get(cv2.CAP_PROP_FPS) if video_path else None
    frame_delay = int(1000 / fps) if fps else 1

    while system_status["active"]:
        ret, frame = cap.read()
        if not ret:
            print("Video ended or cannot read the frame.")
            break

        frame = cv2.resize(frame, (980, 740))
        results = model(frame)

        for info in results:
            parameters = info.boxes
            for box in parameters:
                x1, y1, x2, y2 = box.xyxy[0]
                x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                confidence = box.conf[0]
                class_detect = box.cls[0]
                class_detect = int(class_detect)
                class_detect = classnames[class_detect]
                conf = math.ceil(confidence * 100)

                height = y2 - y1
                width = x2 - x1
                threshold = height - width

                if conf > 80 and class_detect == 'person':
                    cvzone.cornerRect(frame, [x1, y1, width, height], l=30, rt=6)
                    cvzone.putTextRect(frame, f'{class_detect}', [x1 + 8, y1 - 12], thickness=2, scale=2)

                    if threshold < 0 and not fall_detected:
                        cvzone.putTextRect(frame, 'Fall Detected', [height, width], thickness=2, scale=2)
                        fall_detected = True
                        fall_detection_time = time.time()
                        snapshot_count = 0

        if fall_detected and snapshot_count < max_snapshots:
            if time.time() - fall_detection_time >= (snapshot_count + 1) * 5:
                timestamp = timezone.now()  # Use timezone-aware datetime
                snapshot_path = os.path.join(snapshots_folder, f"fall_snapshot_{timestamp.strftime('%Y-%m-%d_%H-%M-%S')}_{snapshot_count + 1}.jpg")
                cv2.imwrite(snapshot_path, frame)

                # Create a FallLog entry with timezone-aware timestamp
                FallLog.objects.create(
                    snapshot_url=snapshot_path,
                    timestamp=timestamp,
                    status="Fall Detected"
                )
                print(f"Snapshot {snapshot_count + 1} saved at {snapshot_path}")

                # Start email sending in a separate thread
                threading.Thread(target=send_email, args=(snapshot_path,)).start()
                log_fall_event(snapshot_url=snapshot_path, status="Fall Detected")
                snapshot_count += 1

        cv2.imshow('frame', frame)

        if cv2.waitKey(frame_delay) & 0xFF == ord('q'):  # Press 'q' to quit
            break

    cap.release()
    cv2.destroyAllWindows()
    system_status["active"] = False
