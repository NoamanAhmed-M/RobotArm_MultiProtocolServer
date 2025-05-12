import json
import cv2
import numpy as np
import base64
import time

def create_test_frame(text="Test Frame"):
    """Create a test frame with specified text"""
    test_img = np.ones((480, 640, 3), dtype=np.uint8) * 128  # Gray image
    cv2.putText(test_img, text, (220, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
    _, jpeg = cv2.imencode('.jpg', test_img)
    b64_data = base64.b64encode(jpeg.tobytes()).decode('utf-8')
    
    return json.dumps({
        "type": "video_frame",
        "data": b64_data,
        "timestamp": time.time(),
        "test": True
    })

def format_elapsed_time(seconds):
    """Format seconds into human-readable elapsed time"""
    if seconds < 60:
        return f"{seconds:.1f} seconds"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f} minutes"
    else:
        hours = seconds / 3600
        return f"{hours:.1f} hours"

def log_with_timestamp(message, level="INFO"):
    """Log a message with timestamp and log level"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    print(f"[{timestamp}] [{level}] {message}")
