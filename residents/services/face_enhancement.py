"""
Service for enhancing resident face recognition with multiple webcam captures.
"""
import base64
import io
from PIL import Image
from residents.models import Resident, ResidentEmbedding
from recognition.services.embedding_utils import cosine_similarity


class FaceEnhancementService:
    """
    Handles multi-image face enrollment from webcam captures.
    Creates one ResidentEmbedding per successful image.
    """
    
    EMBEDDING_MODEL = "Facenet512"
    FACE_DETECTOR_BACKEND = "retinaface"
    MAX_IMAGES = 10
    MAX_IMAGE_SIZE_BYTES = 2 * 1024 * 1024  # 2 MB per image
    MAX_IMAGE_PIXELS = 4096 * 4096  # 16 megapixels (prevents high-resolution attacks)
    
    @staticmethod
    def process_webcam_captures(resident: Resident, base64_images: list) -> dict:
        """
        Process multiple base64-encoded webcam captures.
        
        Args:
            resident: Resident to enhance
            base64_images: List of base64-encoded JPEG strings
        
        Returns:
            {
                'success': bool,
                'embeddings_created': int,
                'embeddings': [embedding_ids],
                'errors': [error messages],
                'message': str
            }
        """
        from deepface import DeepFace
        import os
        
        result = {
            'success': False,
            'embeddings_created': 0,
            'embeddings': [],
            'errors': [],
        }
        
        if not base64_images:
            result['message'] = "No images provided"
            return result
        
        # Validate request limits before processing
        if len(base64_images) > FaceEnhancementService.MAX_IMAGES:
            result['errors'].append(f"Too many images: {len(base64_images)} exceeds maximum of {FaceEnhancementService.MAX_IMAGES}")
            result['message'] = f"Request rejected: exceeded image limit ({FaceEnhancementService.MAX_IMAGES} max)"
            return result
        
        # Validate image sizes before processing (decode and measure actual bytes)
        for idx, base64_str in enumerate(base64_images, 1):
            try:
                # Decode base64 strictly to measure actual image data size
                image_data = base64.b64decode(base64_str, validate=True)
                
                # Reject if decoded size exceeds limit
                if len(image_data) > FaceEnhancementService.MAX_IMAGE_SIZE_BYTES:
                    result['errors'].append(f"Image {idx}: exceeds size limit (max {FaceEnhancementService.MAX_IMAGE_SIZE_BYTES // (1024*1024)} MB)")
                    result['message'] = f"Request rejected: image {idx} exceeds size limit"
                    return result
                
                # Validate image dimensions
                image = Image.open(io.BytesIO(image_data))
                pixel_count = image.width * image.height
                
                if pixel_count > FaceEnhancementService.MAX_IMAGE_PIXELS:
                    result['errors'].append(f"Image {idx}: exceeds pixel limit ({image.width}x{image.height}={pixel_count} pixels, max {FaceEnhancementService.MAX_IMAGE_PIXELS})")
                    result['message'] = f"Request rejected: image {idx} exceeds dimension limit"
                    return result
                
            except Exception as e:
                result['errors'].append(f"Image {idx}: invalid or corrupted image data - {str(e)}")
                result['message'] = f"Request rejected: image {idx} is invalid"
                return result
        
        backend = os.environ.get("FACE_DETECTOR_BACKEND", FaceEnhancementService.FACE_DETECTOR_BACKEND)
        
        for idx, base64_str in enumerate(base64_images, 1):
            try:
                # Decode base64 to image
                image_data = base64.b64decode(base64_str)
                image = Image.open(io.BytesIO(image_data)).convert('RGB')
                
                # Convert PIL Image to numpy array
                import numpy as np
                image_array = np.array(image)
                
                # Extract and generate embedding
                try:
                    # Generate embedding; represent() performs detection internally.
                    embedding_result = DeepFace.represent(
                        img_path=image_array,
                        model_name=FaceEnhancementService.EMBEDDING_MODEL,
                        detector_backend=backend,
                        enforce_detection=True,
                        align=True,
                    )
                    
                    if not embedding_result:
                        result['errors'].append(f"Image {idx}: Failed to generate embedding")
                        continue
                    
                    embedding_vector = embedding_result[0]["embedding"]                    
                    # Create ResidentEmbedding record
                    embedding_record = ResidentEmbedding.objects.create(
                        resident=resident,
                        embedding=embedding_vector,
                        quality_score=None,  # Sprint 2: Can add quality scoring in future
                        is_active=True,
                    )
                    
                    result['embeddings_created'] += 1
                    result['embeddings'].append(embedding_record.id)
                    
                except Exception as e:
                    result['errors'].append(f"Image {idx}: {str(e)}")
                    continue
                    
            except Exception as e:
                result['errors'].append(f"Image {idx}: Failed to process - {str(e)}")
                continue
        
        result['success'] = result['embeddings_created'] > 0
        
        if result['success']:
            result['message'] = f"Successfully created {result['embeddings_created']} embedding(s)"
        else:
            result['message'] = "Failed to create any embeddings"
        
        return result
    
    @staticmethod
    def get_resident_embeddings(resident: Resident) -> list:
        """Get all active embeddings for a resident."""
        return ResidentEmbedding.objects.filter(
            resident=resident,
            is_active=True,
        ).order_by('-created_at')
    
    @staticmethod
    def get_embedding_count(resident: Resident) -> int:
        """Get count of active embeddings."""
        return ResidentEmbedding.objects.filter(
            resident=resident,
            is_active=True,
        ).count()
