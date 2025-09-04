"""
----------------------------------------------------------------------------------------------------
### app/ai/emotion_detector.py - Stable Emotion Detection System ###
This module provides stable emotion detection using OpenCV Haar cascades and TensorFlow,
with thread safety, Windows compatibility, and automatic fallback mechanisms.
----------------------------------------------------------------------------------------------------
"""

import os
import cv2
import numpy as np
import threading
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List
from flask import current_app

# Thread safety lock for OpenCV operations
_infer_lock = threading.Lock()

# Global variables for model and cascade
_model = None
_cascade = None
_model_loaded = False
_cascade_loaded = False

# Emotion labels (adjust based on your model)
EMOTION_LABELS = ['angry', 'disgust', 'fear', 'happy', 'sad', 'surprise', 'neutral']

def initialize_opencv():
    """Initialize OpenCV with thread safety settings."""
    try:
        # Limit OpenCV threads for stability on Windows
        cv2.setNumThreads(1)
        logging.info("[EmotionDetector] OpenCV initialized with single thread mode")
    except Exception as e:
        logging.warning(f"[EmotionDetector] Could not set OpenCV thread count: {e}")

def load_haar_cascade() -> Optional[cv2.CascadeClassifier]:
    """
    Load Haar cascade with automatic fallback to OpenCV built-in cascade.
    
    Returns:
        CascadeClassifier object or None if loading fails
    """
    global _cascade, _cascade_loaded
    
    if _cascade_loaded and _cascade is not None:
        return _cascade
    
    cascade_path = None
    
    try:
        # Try to get custom path from Flask config
        if current_app and 'HAAR_CASCADE_PATH' in current_app.config:
            custom_path = current_app.config['HAAR_CASCADE_PATH']
            if custom_path and os.path.exists(custom_path):
                cascade_path = custom_path
                logging.info(f"[EmotionDetector] Using custom Haar cascade: {cascade_path}")
    except Exception as e:
        logging.debug(f"[EmotionDetector] Could not access Flask config: {e}")
    
    # Fallback to OpenCV built-in cascade
    if not cascade_path:
        try:
            opencv_data_path = Path(cv2.data.haarcascades)
            fallback_path = opencv_data_path / 'haarcascade_frontalface_default.xml'
            if fallback_path.exists():
                cascade_path = str(fallback_path)
                logging.info(f"[EmotionDetector] Using OpenCV built-in Haar cascade: {cascade_path}")
            else:
                logging.error(f"[EmotionDetector] OpenCV data path not found: {opencv_data_path}")
                return None
        except Exception as e:
            logging.error(f"[EmotionDetector] Error accessing OpenCV data: {e}")
            return None
    
    try:
        # Load cascade in temporary variable first
        temp_cascade = cv2.CascadeClassifier(cascade_path)
        
        # Verify cascade is not empty before assigning to global
        if temp_cascade.empty():
            logging.error(f"[EmotionDetector] Loaded Haar cascade is empty: {cascade_path}")
            return None
        
        # Only assign to global if cascade is valid
        _cascade = temp_cascade
        _cascade_loaded = True
        logging.info("[EmotionDetector] Haar Cascade caricata con successo")
        return _cascade
        
    except Exception as e:
        logging.error(f"[EmotionDetector] Error loading Haar cascade from {cascade_path}: {e}")
        return None

def load_emotion_model() -> bool:
    """
    Load the emotion recognition model.
    
    Returns:
        True if model loaded successfully, False otherwise
    """
    global _model, _model_loaded
    
    if _model_loaded and _model is not None:
        return True
    
    try:
        # Try to get model path from Flask config or environment
        model_path = None
        
        try:
            if current_app and 'EMOTION_MODEL_PATH' in current_app.config:
                model_path = current_app.config['EMOTION_MODEL_PATH']
        except Exception:
            pass
        
        if not model_path:
            model_path = os.getenv('EMOTION_MODEL_PATH', 'models/emotion_model.keras')
        
        if not os.path.exists(model_path):
            logging.error(f"[EmotionDetector] Emotion model not found: {model_path}")
            return False
        
        # Import TensorFlow here to avoid loading it at module level
        import tensorflow as tf
        
        # Load the model
        _model = tf.keras.models.load_model(model_path)
        _model_loaded = True
        logging.info(f"[EmotionDetector] Emotion model loaded successfully: {model_path}")
        return True
        
    except ImportError:
        logging.error("[EmotionDetector] TensorFlow not available - install with: pip install tensorflow")
        return False
    except Exception as e:
        logging.error(f"[EmotionDetector] Error loading emotion model: {e}")
        return False

def detect_faces(image: np.ndarray) -> List[Tuple[int, int, int, int]]:
    """
    Detect faces in the image using Haar cascade.
    
    Args:
        image: Input image as numpy array
        
    Returns:
        List of face bounding boxes as (x, y, w, h) tuples
    """
    cascade = load_haar_cascade()
    if cascade is None:
        return []
    
    try:
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        # Detect faces
        faces = cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30)
        )
        
        return [(int(x), int(y), int(w), int(h)) for x, y, w, h in faces]
        
    except Exception as e:
        logging.error(f"[EmotionDetector] Error in face detection: {e}")
        return []

def predict_emotion(face_image: np.ndarray) -> Optional[Dict[str, Any]]:
    """
    Predict emotion from a face image.
    
    Args:
        face_image: Cropped face image as numpy array
        
    Returns:
        Dictionary with emotion prediction and probabilities, or None if prediction fails
    """
    if not load_emotion_model():
        return None
    
    try:
        # Preprocess the face image for the model
        # Adjust these parameters based on your model's requirements
        face_resized = cv2.resize(face_image, (48, 48))  # Common size for emotion models
        
        if len(face_resized.shape) == 3:
            face_gray = cv2.cvtColor(face_resized, cv2.COLOR_BGR2GRAY)
        else:
            face_gray = face_resized
        
        # Normalize pixel values
        face_normalized = face_gray.astype('float32') / 255.0
        
        # Reshape for model input (add batch and channel dimensions)
        face_input = face_normalized.reshape(1, 48, 48, 1)
        
        # Make prediction
        predictions = _model.predict(face_input, verbose=0)
        
        # Get the predicted emotion
        emotion_idx = np.argmax(predictions[0])
        emotion_label = EMOTION_LABELS[emotion_idx] if emotion_idx < len(EMOTION_LABELS) else 'unknown'
        confidence = float(predictions[0][emotion_idx])
        
        # Get all probabilities
        probs = {EMOTION_LABELS[i]: float(predictions[0][i]) for i in range(len(EMOTION_LABELS))}
        
        return {
            'emotion': emotion_label,
            'confidence': confidence,
            'probs': probs
        }
        
    except Exception as e:
        logging.error(f"[EmotionDetector] Error in emotion prediction: {e}")
        return None

def analyze_frame(frame: np.ndarray) -> Dict[str, Any]:
    """
    Analyze a video frame for faces and emotions with thread safety.
    
    Args:
        frame: Input video frame as numpy array
        
    Returns:
        Dictionary containing analysis results
    """
    with _infer_lock:  # Serialize face detection and emotion prediction
        try:
            # Detect faces
            faces = detect_faces(frame)
            
            if not faces:
                return {
                    'success': True,
                    'faces_detected': 0,
                    'bbox': None,
                    'emotion': None,
                    'confidence': None,
                    'probs': None
                }
            
            # Process the first (largest) face
            x, y, w, h = faces[0]
            face_roi = frame[y:y+h, x:x+w]
            
            # Predict emotion
            emotion_result = predict_emotion(face_roi)
            
            result = {
                'success': True,
                'faces_detected': len(faces),
                'bbox': {'x': x, 'y': y, 'w': w, 'h': h}
            }
            
            if emotion_result:
                result.update({
                    'emotion': emotion_result['emotion'],
                    'confidence': emotion_result['confidence'],
                    'probs': emotion_result['probs']
                })
            else:
                result.update({
                    'emotion': None,
                    'confidence': None,
                    'probs': None
                })
            
            return result
            
        except Exception as e:
            logging.error(f"[EmotionDetector] Error analyzing frame: {e}")
            return {
                'success': False,
                'error': str(e),
                'faces_detected': 0,
                'bbox': None,
                'emotion': None,
                'confidence': None,
                'probs': None
            }

def initialize_emotion_detector() -> bool:
    """
    Initialize the emotion detection system.
    
    Returns:
        True if initialization successful, False otherwise
    """
    try:
        initialize_opencv()
        
        # Test loading components
        cascade_ok = load_haar_cascade() is not None
        model_ok = load_emotion_model()
        
        if cascade_ok and model_ok:
            logging.info("[EmotionDetector] Emotion detection system initialized successfully")
            return True
        else:
            logging.warning("[EmotionDetector] Emotion detection system partially initialized")
            if not cascade_ok:
                logging.warning("[EmotionDetector] Haar cascade not available")
            if not model_ok:
                logging.warning("[EmotionDetector] Emotion model not available")
            return False
            
    except Exception as e:
        logging.error(f"[EmotionDetector] Error initializing emotion detection system: {e}")
        return False