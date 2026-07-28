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


def match_embedding(
    embedding,
    residents,
    visitors,
    threshold=None,
    resident_threshold=None,
    visitor_threshold=None,
):
    """
    Match against resident and visitor embedding lists.
    residents/visitors: list of dicts with id, name, embedding, type
    Returns: (person_type, match_dict, confidence)
    """
    res_thresh = resident_threshold or threshold or RECOGNITION_SIMILARITY_THRESHOLD
    vis_thresh = visitor_threshold or threshold or RECOGNITION_SIMILARITY_THRESHOLD

    best_res_entry = None
    best_res_score = 0.0
    res_scores_by_id = {}

    for entry in residents:
        emb = entry.get("embedding")
        if not emb:
            continue
        score = cosine_similarity(embedding, emb)
        res_id = entry.get("id")
        if res_id:
            if res_id not in res_scores_by_id or score > res_scores_by_id[res_id][0]:
                res_scores_by_id[res_id] = (score, entry)
        elif score > best_res_score:
            best_res_score = score
            best_res_entry = entry

    if res_scores_by_id:
        for score, entry in res_scores_by_id.values():
            if score > best_res_score:
                best_res_score = score
                best_res_entry = entry

    if best_res_entry and best_res_score >= res_thresh:
        return "RESIDENT", best_res_entry, best_res_score

    best_vis_entry = None
    best_vis_score = 0.0
    vis_scores_by_id = {}

    for entry in visitors:
        emb = entry.get("embedding")
        if not emb:
            continue
        score = cosine_similarity(embedding, emb)
        vis_id = entry.get("id")
        if vis_id:
            if vis_id not in vis_scores_by_id or score > vis_scores_by_id[vis_id][0]:
                vis_scores_by_id[vis_id] = (score, entry)
        elif score > best_vis_score:
            best_vis_score = score
            best_vis_entry = entry

    if vis_scores_by_id:
        for score, entry in vis_scores_by_id.values():
            if score > best_vis_score:
                best_vis_score = score
                best_vis_entry = entry

    if best_vis_entry and best_vis_score >= vis_thresh:
        return "VISITOR", best_vis_entry, best_vis_score

    return "UNKNOWN", None, max(best_res_score, best_vis_score)


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
