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
from urllib.parse import unquote

# Configure the API
API_KEY = os.environ.get('GOOGLE_API_KEY')
ai.configure(api_key=API_KEY)

# Initialize the client
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

from urllib.parse import unquote
from django.core.files.storage import FileSystemStorage
from django.http import JsonResponse, HttpResponseBadRequest
import os
import threading
from django.conf import settings

def start_detection(request):
    if request.method == "POST":
        # Handle video file upload
        if 'video_file' in request.FILES:
            video_file = request.FILES['video_file']
            fs = FileSystemStorage(location='media/videos/')
            filename = fs.save(video_file.name, video_file)
            video_path = fs.url(filename)
            full_video_path = os.path.join(settings.MEDIA_ROOT, 'videos', filename)

            if not os.path.exists(full_video_path):
                return HttpResponseBadRequest(f"Error: File does not exist at {full_video_path}")

            # Start fall detection with uploaded video
            system_status["active"] = True
            threading.Thread(target=start_fall_detection, args=(system_status, full_video_path)).start()
            return JsonResponse({"status": "Fall detection started successfully with uploaded video"})

        else:
            return HttpResponseBadRequest("No video file provided in the request")

    elif request.method == "GET":
        # Handle video URL provided as a query parameter
        video_url = request.GET.get('video_url', None)

        if not video_url:
            return HttpResponseBadRequest("No video URL provided in the request")

        # Decode the video URL
        decoded_video_url = unquote(video_url)

        # Validate decoded URL
        if not decoded_video_url.startswith('/media/'):
            return HttpResponseBadRequest("Invalid video URL provided")

        full_video_path = os.path.join(settings.MEDIA_ROOT, decoded_video_url.lstrip('/'))

        # Debug logs
        print(f"Decoded video URL: {decoded_video_url}")
        print(f"Full video path: {full_video_path}")

        if not os.path.exists(full_video_path):
            return HttpResponseBadRequest(f"Error: File does not exist at {full_video_path}")

        # Start fall detection with video URL
        system_status["active"] = True
        threading.Thread(target=start_fall_detection, args=(system_status, full_video_path)).start()
        return JsonResponse({"status": f"Fall detection started successfully with video URL: {decoded_video_url}"})

    else:
        pass

    return HttpResponseBadRequest("Invalid request method")

def video_feed(request):
    # Check if the environment is Render, if so, use a fallback video or stream source
    if 'RENDER' in os.environ:
        # Fallback video for Render
        fallback_video_name = "fall.mp4"
        fallback_video_path = os.path.join(settings.MEDIA_ROOT, "videos", fallback_video_name)

        if not os.path.exists(fallback_video_path):
            return HttpResponseBadRequest(f"Error: Fallback video does not exist at {fallback_video_path}")

        cap = cv2.VideoCapture(fallback_video_path)  # Open the fallback video file
    else:
        # Local environment: use the camera (index 0)
        cap = cv2.VideoCapture(0)

    def generate():
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            _, jpeg = cv2.imencode(".jpg", frame)
            yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpeg.tobytes() + b"\r\n")

    return StreamingHttpResponse(generate(), content_type="multipart/x-mixed-replace; boundary=frame")


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
