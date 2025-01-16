# AI-Powered Elderly Care System  

## Overview  
This project is an AI-driven solution designed to enhance the safety and well-being of elderly individuals. It features:  
- **Fall Detection**: Real-time monitoring using Yolov8 and OpenCV, with automatic email alerts to caretakers when a fall is detected.  
- **Healthcare Assistant**: Interactive chatbot support for caretakers to access healthcare-related information and resources.  

## Features  
- Real-time camera feed monitoring.  
- AI-based fall detection using Yolov8.  
- Email notifications to caretakers for quick response.  
- Integrated healthcare assistant for caretaker support.  

## Technologies Used  
- **Frontend**: HTML, CSS  
- **Backend**: Python, Django  
- **AI/ML**: Yolov8, OpenCV  
- **Communication**: SMTP (email alerts)  

## Installation  
1. Clone the repository:  
   ```bash
   git clone https://github.com/yourusername/elderly-care-system.git
2. Install dependencies:
   '''bash
   pip install -r requirements.txt
3. Run the server:
   '''bash
   python manage.py runserver
## How It Works
- The camera feed is processed in real-time to detect falls using the Yolov8 model and OpenCV.
- When a fall is detected, an email is sent to the registered caretaker.
- A healthcare assistant provides interactive support and guidance.
