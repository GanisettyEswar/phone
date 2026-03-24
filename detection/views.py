from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import PhoneDetection
from face_capture.models import Person
import os
from django.conf import settings
from datetime import datetime

# Models loaded lazily to avoid memory crash on startup
yolo_model = None
face_recognizer = None
label_map = None


def load_models():
    global yolo_model, face_recognizer, label_map
    import cv2
    import pickle

    if yolo_model is None:
        from ultralytics import YOLO
        yolo_model = YOLO('yolov8n.pt')

    if face_recognizer is None:
        model_path = os.path.join(settings.MEDIA_ROOT, 'trained_models', 'face_recognizer.yml')
        label_path = os.path.join(settings.MEDIA_ROOT, 'trained_models', 'label_map.pkl')

        if os.path.exists(model_path) and os.path.exists(label_path):
            # Use same parameters as training
            face_recognizer = cv2.face.LBPHFaceRecognizer_create(
                radius=2,
                neighbors=8,
                grid_x=8,
                grid_y=8,
                threshold=80.0
            )
            face_recognizer.read(model_path)

            with open(label_path, 'rb') as f:
                label_map = pickle.load(f)


def detection_page(request):
    return render(request, 'detection/detection.html')


def process_and_annotate(frame, face_cascade, last_save_time):
    import cv2
    # Detect mobile phones using YOLO
    results = yolo_model(frame, verbose=False)
    phone_detected = False

    for result in results:
        boxes = result.boxes
        for box in boxes:
            class_id = int(box.cls[0])
            # Class 67 is cell phone in COCO dataset
            if class_id == 67:
                phone_detected = True
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
                cv2.putText(frame, 'Phone Detected', (x1, y1 - 10),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)

    # Face recognition and detection saving
    if phone_detected:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        # Apply histogram equalization for better lighting normalization
        gray = cv2.equalizeHist(gray)

        # Improved face detection parameters
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

        for (x, y, w, h) in faces:
            face_roi = gray[y:y+h, x:x+w]
            # Resize to standard size matching training
            face_roi_resized = cv2.resize(face_roi, (200, 200))
            name = "Unknown"
            confidence_score = 0

            # Try face recognition if models are loaded
            if face_recognizer and label_map:
                try:
                    label, confidence = face_recognizer.predict(face_roi_resized)
                    confidence_score = confidence
                    # Stricter threshold for better accuracy (lower is better match)
                    if confidence < 70:  # More strict threshold
                        name = label_map.get(label, "Unknown")
                    else:
                        name = "Unknown"
                except:
                    name = "Unknown"

            # Save detection for both known and unknown users
            current_time = datetime.now()
            save_key = name  # Use only name, not position

            if save_key not in last_save_time or (current_time - last_save_time[save_key]).total_seconds() > 10:
                try:
                    detection_dir = os.path.join(settings.MEDIA_ROOT, 'detections')
                    os.makedirs(detection_dir, exist_ok=True)

                    timestamp = current_time.strftime('%Y%m%d_%H%M%S')
                    image_path = os.path.join(detection_dir, f'{name}_{timestamp}.jpg')
                    cv2.imwrite(image_path, frame)

                    relative_path = f'detections/{name}_{timestamp}.jpg'

                    # Try to link to person if known, otherwise save with person=None
                    person = None
                    if name != "Unknown":
                        try:
                            person = Person.objects.get(username=name)
                        except:
                            pass

                    PhoneDetection.objects.create(person=person, image=relative_path)
                    last_save_time[save_key] = current_time
                except Exception as e:
                    print(f"Error saving detection: {e}")

            # Display confidence score for debugging
            display_text = f"{name} ({confidence_score:.1f})" if confidence_score > 0 else name
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            cv2.putText(frame, display_text, (x, y - 10),
                      cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
    
    return frame, phone_detected


@csrf_exempt
def process_frame(request):
    import base64
    import json
    import cv2
    import numpy as np
    
    if request.method == 'POST':
        try:
            load_models()
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            
            data = json.loads(request.body)
            image_data = data.get('image')
            
            if not image_data:
                return JsonResponse({'success': False, 'error': 'No image data'})
            
            # Decode base64 image
            image_data = image_data.split(',')[1]
            image_bytes = base64.b64decode(image_data)
            
            # Convert to numpy array
            nparr = np.frombuffer(image_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            # Use a shared or persistent last_save_time if needed
            dummy_save_time = {} 
            
            # Process frame
            processed_frame, phone_detected = process_and_annotate(frame, face_cascade, dummy_save_time)
            
            # Encode back to base64
            ret, buffer = cv2.imencode('.jpg', processed_frame)
            processed_image_bytes = base64.b64encode(buffer).decode('utf-8')
            
            return JsonResponse({
                'success': True, 
                'image': f'data:image/jpeg;base64,{processed_image_bytes}',
                'phone_detected': phone_detected
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
            
    return JsonResponse({'success': False, 'error': 'Invalid request'})
