import cv2
import numpy as np
import base64
import json
import logging
from typing import Tuple, List, Optional

logger = logging.getLogger("face_service")

# Lazy-loaded Haar Cascade Classifier
_face_cascade = None

def get_face_cascade():
    global _face_cascade
    if _face_cascade is None:
        try:
            cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            _face_cascade = cv2.CascadeClassifier(cascade_path)
        except Exception as e:
            logger.warning(f"Could not load Haar cascade: {e}")
            _face_cascade = False
    return _face_cascade if _face_cascade is not False else None

def decode_base64_image(b64_str: str) -> np.ndarray:
    """Decodes a base64 string or data URL to an OpenCV BGR image."""
    if not b64_str:
        raise ValueError("Empty image data provided")
    
    if "," in b64_str:
        b64_str = b64_str.split(",", 1)[1]
    
    raw = base64.b64decode(b64_str)
    arr = np.frombuffer(raw, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Failed to decode image from provided data")
    return img

def extract_face_descriptor(image_data_b64: str) -> Tuple[List[float], str, bool]:
    """
    Extracts a zero-mean normalized facial descriptor vector (ZNCC) and thumbnail.
    Returns:
        (descriptor_vector, thumbnail_data_url, is_face_detected)
    """
    img = decode_base64_image(image_data_b64)
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    cascade = get_face_cascade()
    is_face_detected = False
    color_crop = img
    gray_crop = gray
    
    if cascade is not None:
        faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(30, 30))
        if len(faces) > 0:
            # Pick largest face
            faces = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)
            fx, fy, fw, fh = faces[0]
            # Add 15% margin
            pad_x = int(fw * 0.15)
            pad_y = int(fh * 0.15)
            x1 = max(0, fx - pad_x)
            y1 = max(0, fy - pad_y)
            x2 = min(w, fx + fw + pad_x)
            y2 = min(h, fy + fh + pad_y)
            
            gray_crop = gray[y1:y2, x1:x2]
            color_crop = img[y1:y2, x1:x2]
            is_face_detected = True

    if not is_face_detected:
        # Fallback to center 75% crop if face detector didn't find clear bounding box
        cy, cx = h // 2, w // 2
        sz = int(min(h, w) * 0.38)
        gray_crop = gray[max(0, cy - sz):min(h, cy + sz), max(0, cx - sz):min(w, cx + sz)]
        color_crop = img[max(0, cy - sz):min(h, cy + sz), max(0, cx - sz):min(w, cx + sz)]

    # Resize to standard 48x48
    resized = cv2.resize(gray_crop, (48, 48)).astype(np.float32)
    
    # Zero-mean Normalized Cross-Correlation (ZNCC) descriptor
    norm = resized - np.mean(resized)
    std = np.std(norm)
    if std > 1e-5:
        norm /= std
    
    flat = norm.flatten()
    length = np.linalg.norm(flat)
    if length > 1e-6:
        flat /= length
    
    descriptor_vector = flat.tolist()

    # Generate 80x80 thumbnail for avatar
    thumb = cv2.resize(color_crop, (80, 80))
    _, enc = cv2.imencode(".jpg", thumb, [cv2.IMWRITE_JPEG_QUALITY, 85])
    thumb_b64 = "data:image/jpeg;base64," + base64.b64encode(enc).decode("ascii")

    return descriptor_vector, thumb_b64, is_face_detected

def compare_face_descriptors(desc1: List[float], desc2: List[float]) -> float:
    """Computes similarity score between two face descriptor vectors (-1.0 to 1.0)."""
    if not desc1 or not desc2 or len(desc1) != len(desc2):
        return -1.0
    v1 = np.array(desc1, dtype=np.float32)
    v2 = np.array(desc2, dtype=np.float32)
    return float(np.dot(v1, v2))

def match_face_against_users(captured_desc: List[float], users: list, threshold: float = 0.65):
    """
    Finds best matching user among candidate users who have enrolled face descriptors.
    Returns: (matching_user, similarity_score) or None
    """
    best_user = None
    best_score = -1.0

    for user in users:
        if not user.face_descriptor:
            continue
        try:
            stored_desc = json.loads(user.face_descriptor)
            score = compare_face_descriptors(captured_desc, stored_desc)
            if score > best_score:
                best_score = score
                best_user = user
        except Exception as e:
            logger.warning(f"Error parsing face descriptor for user {user.id}: {e}")

    if best_user and best_score >= threshold:
        return best_user, best_score
    return None
