from django.shortcuts import render
from django.http import JsonResponse, StreamingHttpResponse, HttpResponseBadRequest
import threading
from .fall_detection import start_fall_detection
import cv2
from .models import FallLog
from datetime import datetime
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import FileSystemStorage
import os
from django.utils import timezone
from django.conf import settings


import google.generativeai as ai

# Configure the API
API_KEY = os.environ.get('GOOGLE_API_KEY') 'Your_API_Key'
ai.configure(api_key=API_KEY)
model = ai.GenerativeModel("gemini-pro")
chat = model.start_chat()

def chatbot_view(request):
    if request.method == "POST":
        import json

        data = json.loads(request.body)
        user_message = data.get("message", "")

        if user_message.lower() == "bye":
            return JsonResponse({"response": "Goodbye!"})

        response = chat.send_message(user_message)
        return JsonResponse({"response": response.text})
    return JsonResponse({"error": "Invalid request method"}, status=400)


# Define a shared system status dictionary
system_status = {"active": False}

def dashboard(request):
    logs = FallLog.objects.all().order_by('-timestamp')  # Fetch the fall logs
    return render(request, "detection/dashboard.html", {"status": system_status["active"], "logs": logs})

# Make sure 'system_status' is defined somewhere globally or imported properly
system_status = {"active": False}

def start_detection(request):
    if request.method == "POST":
        # Check if a video file is uploaded
        if 'video_file' in request.FILES:
            video_file = request.FILES['video_file']
            # Save the video file in the 'videos' directory under MEDIA_ROOT
            video_path = default_storage.save(f'videos/{video_file.name}', video_file)

            # Construct the full path correctly without duplicating /media/
            full_video_path = os.path.join(settings.MEDIA_ROOT, video_path)

            # Check if the file was saved correctly
            if not os.path.exists(full_video_path):
                return HttpResponseBadRequest(f"Error: File does not exist at {full_video_path}")

            # Update system status to active
            system_status["active"] = True

            # Start fall detection in a separate thread with the uploaded video
            threading.Thread(target=start_fall_detection, args=(system_status, full_video_path)).start()
            return JsonResponse({"status": "Fall detection started successfully with uploaded video"})
        else:
            # Start real-time fall detection
            system_status["active"] = True
            threading.Thread(target=start_fall_detection, args=(system_status,0)).start()
            return JsonResponse({"status": "Fall detection started successfully for real-time processing"})

    elif request.method == "GET":
        video_url = request.GET.get('video_url')
        if not video_url:
            return HttpResponseBadRequest("Missing video_url parameter")

        # Ensure the video_url is a relative path without leading /
        video_path = video_url.lstrip('/')
        
        # If the path already starts with 'media/', remove it to avoid duplication
        if video_path.startswith('media/'):
            video_path = video_path[len('media/'):]

        # Construct the full path
        full_video_path = os.path.join(settings.MEDIA_ROOT,'videos', video_path)

        if not os.path.exists(full_video_path):
            return HttpResponseBadRequest(f"Error: File does not exist at {full_video_path}")

        # Update system status to active
        system_status["active"] = True

        # Start the fall detection process with the video path
        threading.Thread(target=start_fall_detection, args=(system_status, full_video_path)).start()
        return JsonResponse({"status": "Fall detection started successfully with video URL"})

    else:
        return HttpResponseBadRequest("Invalid request method")
    

@csrf_exempt  # Use with caution; implement proper CSRF protection in production
def upload_video(request):
    if request.method == 'POST' and 'video_file' in request.FILES:  # Fixed key to match the frontend
        video_file = request.FILES['video_file']
        fs = FileSystemStorage(location='media/videos/')  # Save to media/videos/
        
        # Ensure the directory exists
        if not os.path.exists('media/videos/'):
            os.makedirs('media/videos/')
        
        filename = fs.save(video_file.name, video_file)
        file_url = fs.url(filename)
        return JsonResponse({"status": "success", "file_url": file_url}, status=201)

    return JsonResponse({"status": "error", "message": "Invalid request"}, status=400)

def video_feed(request):
    cap = cv2.VideoCapture(0)

    def generate():
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            _, jpeg = cv2.imencode(".jpg", frame)
            yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpeg.tobytes() + b"\r\n")

    return StreamingHttpResponse(generate(), content_type="multipart/x-mixed-replace; boundary=frame")

def fetch_logs(request):
    logs = FallLog.objects.all().order_by('-timestamp')  # Fetch logs ordered by timestamp
    logs_data = list(logs.values('snapshot_url', 'timestamp', 'status'))
    return JsonResponse({'logs': logs_data})

def stop_detection(request):
    if request.method == "POST":
        # Update system status to inactive
        system_status["active"] = False
        return JsonResponse({"status": "Fall detection stopped successfully"})
    return JsonResponse({"error": "Invalid request"}, status=400)

def log_fall_event(snapshot_url, status):
    # Get the current timestamp and format it as a datetime object
    timestamp = timezone.now()  # This will automatically use the current time

    # Create the FallLog entry with the formatted timestamp
    fall_log = FallLog.objects.create(
        snapshot_url=snapshot_url,
        timestamp=timestamp,  # Pass the datetime object directly
        status=status
    )
