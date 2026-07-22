import os
import base64
import cv2
import numpy as np

from .config import RECOGNITION_SIMILARITY_THRESHOLD

_deepface = None


def _get_deepface():
    global _deepface
    if _deepface is None:
        from deepface import DeepFace
        _deepface = DeepFace
    return _deepface


def cosine_similarity(a, b):
    a = np.array(a, dtype=np.float32)
    b = np.array(b, dtype=np.float32)
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def generate_embedding(image_bgr):
    """Extract face, align it, convert back to BGR uint8, and generate a Facenet512 embedding."""
    try:
        DeepFace = _get_deepface()
        from .config import FACE_DETECTOR_BACKEND
        
        faces = DeepFace.extract_faces(
            img_path=image_bgr,
            detector_backend=FACE_DETECTOR_BACKEND,
            enforce_detection=True,
            align=True,
        )
        if not faces:
            return None
            
        face_img = faces[0]["face"]
        face_rgb_255 = (face_img * 255).astype(np.uint8)
        face_bgr_255 = cv2.cvtColor(face_rgb_255, cv2.COLOR_RGB2BGR)
        
        result = DeepFace.represent(
            img_path=face_bgr_255,
            model_name="Facenet512",
            enforce_detection=False,
        )
        if not result:
            return None
        return result[0]["embedding"]
    except Exception as e:
        print(f"Face embedding failed: {e}")
        return None


def match_embedding(embedding, residents, visitors, threshold=None):
    """
    Match against resident and visitor embedding lists.
    residents/visitors: list of dicts with id, name, embedding, type
  Returns: (person_type, match_dict, confidence)
    """
    threshold = threshold or RECOGNITION_SIMILARITY_THRESHOLD
    best = None
    best_score = 0.0

    for entry in residents + visitors:
        if not entry.get("embedding"):
            continue
        score = cosine_similarity(embedding, entry["embedding"])
        if score > best_score:
            best_score = score
            best = entry

    if best and best_score >= threshold:
        return best["type"], best, best_score
    return "UNKNOWN", None, best_score


def fetch_embeddings_from_api(base_url, api_token):
    """Load embeddings from Django recognition API for engine-side matching."""
    import requests

    url = base_url.rstrip("/") + "/recognition/api/embeddings/"
    headers = {"X-Engine-Token": api_token} if api_token else {}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"Failed to fetch embeddings: {e}")
    return {"residents": [], "visitors": []}


def encode_snapshot_b64(image_bgr):
    _, buf = cv2.imencode(".jpg", image_bgr)
    return base64.b64encode(buf.tobytes()).decode("ascii")
