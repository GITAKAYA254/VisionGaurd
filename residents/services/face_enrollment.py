from residents.models import Resident


class FaceEnrollmentService:
    @staticmethod
    def enroll(resident: Resident) -> Resident:
        if not resident.photo:
            resident.enrollment_status = Resident.ENROLLMENT_FAILED
            resident.enrollment_error = "No photo provided."
            resident.save(update_fields=["enrollment_status", "enrollment_error"])
            return resident

        try:
            import os
            from deepface import DeepFace

            backend = os.environ.get("FACE_DETECTOR_BACKEND", "retinaface")
            result = DeepFace.represent(
                img_path=resident.photo.path,
                model_name="Facenet512",
                enforce_detection=True,
                detector_backend=backend,
            )
            if not result:
                raise ValueError("No face detected in photo.")

            resident.face_embedding = result[0]["embedding"]
            resident.enrollment_status = Resident.ENROLLMENT_ENROLLED
            resident.enrollment_error = ""
        except Exception as e:
            resident.enrollment_status = Resident.ENROLLMENT_FAILED
            resident.enrollment_error = str(e)

        resident.save(
            update_fields=["face_embedding", "enrollment_status", "enrollment_error"]
        )
        return resident
