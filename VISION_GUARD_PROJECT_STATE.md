# Vision Guard: Project State & Technical Documentation
*Nyayo Estate Smart Surveillance System*

This document presents the verified, concrete technical state of the Vision Guard codebase to support the writing of Chapters 4, 5, and 6 of the project report paper.

---

## 0. Project-wide facts

- **Actual Database in Use**:
  - **Development**: SQLite 3 (`db.sqlite3` using `django.db.backends.sqlite3`).
  - **Production**: MySQL 8.0 (`django.db.backends.mysql`, enabled via `DB_ENGINE=mysql` in environment configuration).
  - **PostgreSQL / pgvector Status**: **NOT IN USE**. Vector similarity search for face embeddings (512-dimensional floating-point vectors from DeepFace `Facenet512`) is performed **in-memory** in Python via NumPy dot product and norm calculation (`cosine_similarity` in `vision_engine/recognition.py` and `recognition/services/embedding_utils.py`). Embeddings are fetched via REST API and cached in RAM (`EmbeddingCache`).

- **Full Confirmed Tech Stack & Versions**:
  - **Python**: 3.12.5 (Measured runtime environment; Python 3.10+ supported).
  - **Django**: 6.0.5 (`requirements.txt`).
  - **Django REST Framework**: 3.17.1 (`requirements.txt`).
  - **YOLOv8 Variant**: YOLOv8 Nano (`yolov8n.pt`, loaded via Ultralytics API in `vision_engine/detection.py` line 23).
  - **DeepFace Backend**: `Facenet512` model (`model_name="Facenet512"` in `vision_engine/recognition.py` line 49 and `residents/services/face_enrollment.py` line 20), using `retinaface` as the primary face detector backend (`FACE_DETECTOR_BACKEND` env var, default `"retinaface"` in `vision_engine/config.py` line 13 and `residents/services/face_enhancement.py` line 18).
  - **OpenCV**: `opencv-python` 4.13.0.92 (`requirements.txt`).
  - **Scikit-learn**: **NOT IN USE**. Vector math is executed directly via `numpy` (bundled with OpenCV/DeepFace).
  - **Twilio**: **NOT IN USE** (No SMS or Twilio integration exists in `requirements.txt` or the codebase).
  - **Asynchronous & WebSocket Stack**: `channels` 4.3.2, `channels-redis` 4.3.0, `daphne` 4.2.1, `redis` 8.0.0.
  - **HTTP & Environment Utilities**: `requests` 2.32.5, `python-dotenv` 1.0.1, `mysqlclient` 2.2.7, `Pillow` (PIL).
  - **Frontend UI Framework**: Bootstrap 5 (CSS/JS) with Django Templates.

- **List of Django Apps/Modules**:
  - `accounts`: Manages user authentication, custom user models (`CustomUser`), roles (`ADMIN`, `GUARD`, `RESIDENT`), and login views.
  - `cameras`: Manages security camera metadata, stream URL endpoints (RTSP, HTTP, USB webcams), operational statuses (`ONLINE`, `OFFLINE`, `MAINTENANCE`), and management commands (`run_vanguard`).
  - `detections`: Logs real-time YOLOv8 object detections (persons, vehicles, bicycles, motorcycles), calculates live camera stats (`CameraLiveStats`), and tracks security incidents (`Incident`).
  - `residents`: Handles resident records, photo registration, single & multi-angle facial enrollment (`Resident`, `ResidentEmbedding`), and face enhancement via webcam.
  - `visitors`: Tracks estate visitors via UUIDs, logs visit counts, matches returning visitors using face embeddings, and associates visitors with resident profiles.
  - `recognition`: Log facial recognition events (`RecognitionEvent`), caches vector embeddings in memory (`EmbeddingCache`), executes similarity matching, and enforces event cooldowns.
  - `dashboard`: Renders the security operations interface, live multi-camera monitoring grid (`monitor`), interactive estate camera map (`map`), and real-time detection summaries.
  - `notifications`: Manages system alerts (`Notification`), deduplicates events per track ID, classifies alert severity (`INFO`, `WARNING`, `HIGH`), attaches JPEG snapshots, and provides stream jump links.
  - `vision_engine`: Independent Python package containing the multi-threaded computer vision pipeline (YOLOv8 tracking, DeepFace recognition, loitering/restricted zone behaviour engine, and local HTTP MJPEG video stream server).

- **Architecture Diagram Status**:
  - **NOT AVAILABLE / NEEDS TO BE CREATED**

---

## 1. Chapter 4 — System Analysis and Requirement Modeling

### Current (manual) system
- **Description**: Security at Nyayo Estate currently relies on physical security guards stationed at entry/exit gates who manually record visitor details, vehicle registration numbers, and identity cards in paper logbooks. Security officers perform manual patrols and monitor passive CCTV video feeds without real-time alerting. Incident investigation requires manually rewinding hours of recorded footage after a break-in or unauthorized entry occurs.
- **Flowchart / DFD of Manual Process**: **NOT AVAILABLE / NEEDS TO BE CREATED**

### Fact-finding results
- **Summary**: **NOT AVAILABLE / NEEDS TO BE CREATED** (No raw questionnaire data, interview transcripts, or empirical survey statistics are present in the codebase repository).

### Functional requirements
1. **Resident Registration & Facial Enrollment**: **Fully Implemented**. Supports single-photo enrollment (`FaceEnrollmentService`) and multi-capture webcam face enhancement (`FaceEnhancementService` creating multiple `ResidentEmbedding` vectors per resident using `Facenet512` and `retinaface`).
2. **Visitor Intelligence & Visit Tracking**: **Fully Implemented**. Automatic registration of unknown faces, vector embedding matching across visits (`VisitorTrackingService`), deduplication, visit counter incrementing, and linking visitors to specific resident host profiles.
3. **Real-time Object Detection & Tracking**: **Fully Implemented**. Multi-threaded YOLOv8 instance tracking (`DetectionEngine.infer`) filtering persons, cars, buses, trucks, bicycles, and motorcycles across configurable frame skip intervals (`DETECTION_FRAME_SKIP`).
4. **Facial Recognition Match Logic**: **Fully Implemented**. Asynchronous DeepFace `Facenet512` embedding generation with cosine similarity matching (`match_embedding`), prioritizing residents over visitors, with configurable similarity threshold (default 0.65) and 30-second event cooldown (`RECOGNITION_COOLDOWN_SECONDS`).
5. **Anomaly & Behaviour Detection**: **Fully Implemented**. In-memory spatial-temporal track history (`TrackHistory`), loitering detection (dwell time > 120s within a 50px radius), and restricted zone polygon intrusion detection (`point_in_polygon` with `RESTRICTED_ZONES_JSON` configuration).
6. **Alert Generation & Notification Dispatch**: **Fully Implemented**. Automatic notification creation (`NotificationService`) with severity levels (`INFO`, `WARNING`, `HIGH`), deduplication per track ID, loitering exclusion for verified residents, base64 snapshot attachments, and direct live stream links.
7. **Security Dashboard & Operations View**: **Fully Implemented**. Dynamic dashboard displaying active camera stats, live detection timelines, active security incidents, recognition feed, interactive estate camera map with GPS coordinates, and live multi-camera MJPEG stream monitoring.

### Non-functional requirements
- **Measured Performance Figures**: Engine operates with configurable `DETECTION_FRAME_SKIP` (default 3), `RECOGNITION_FRAME_SKIP` (10), `INFERENCE_IMGSZ` (416), and `STREAM_FPS_SLEEP` (0.033s / ~30 FPS stream loop). Empirical FPS, CPU/GPU utilisation, and end-to-end frame latency benchmarks across specific hardware setups: **NOT AVAILABLE / NEEDS TO BE CREATED**.
- **Measured Accuracy Figures**: Formal mAP% object detection precision or DeepFace ROC/accuracy benchmarking on estate test video datasets: **NOT AVAILABLE / NEEDS TO BE CREATED**.
- **Security & Privacy Requirements**:
  - Role-based access control via `CustomUser.role` (`ADMIN`, `GUARD`, `RESIDENT`).
  - Token-based API authentication for vision engine endpoints via `X-Engine-Token` header validated against `VISION_GUARD_ENGINE_TOKEN`.
  - Django session authentication, CSRF token validation, and configurable SSL/HSTS security headers (`SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`).
- **Usability, Scalability & Reliability Notes**:
  - Non-blocking HTTP API queue (`AsyncAPIClient`) ensures network latency does not block the real-time video capture loop.
  - Thread-safe state isolation using Python `threading.Lock` for frame buffers and recognition caches.
  - Automatic video source reconnection logic upon detecting consecutive black frames (`BLACK_FRAME_RECONNECT_COUNT = 30`).

### Modelling diagrams
- **Actors and Use Cases (Use Case Diagram)**:
  - **Actors**: Estate Resident, Visitor, Security Guard, Administrator, Vision Guard AI Engine.
  - **Use Cases**:
    - *Estate Resident*: Submit profile details, perform multi-angle webcam face enhancement.
    - *Visitor*: Gate entry scan, automatic visitor profile creation, visit count tracking.
    - *Security Guard*: Monitor live camera grid, receive real-time security notifications, inspect security incident timeline, review recognition feed, view estate map.
    - *Administrator*: Register and manage cameras, configure restricted zones, trigger resident face re-enrollment, manage user accounts.
    - *Vision Guard AI Engine*: Capture stream frames, run YOLOv8 object tracking, extract DeepFace facial embeddings, calculate spatial-temporal loitering/zone entry, transmit async telemetry to Django REST API.
- **Data Flow Description (DFD Context & Level-1)**:
  - *Context Level*: Security Cameras stream video to Vision Engine; Vision Engine posts detection logs, face match events, and behaviour alerts to Vision Guard Backend; Backend displays live alerts and metrics to Security Guards and Administrators; Residents supply registration data to Backend.
  - *Level-1 Processes*:
    1. `1.0 Video Stream Ingestion`: Ingests RTSP/USB video stream, manages frame buffer (`_capture_loop`).
    2. `2.0 Object Detection & Tracking`: Executes YOLOv8 tracking, extracts person/vehicle bounding boxes (`DetectionEngine`).
    3. `3.0 Facial Extraction & Matching`: Crops faces, generates DeepFace `Facenet512` embeddings, performs cosine similarity matching against cached resident/visitor vectors (`_recognize_persons`).
    4. `4.0 Anomaly & Behaviour Analysis`: Evaluates person track dwell time (>120s) and polygon collision (`point_in_polygon`).
    5. `5.0 Incident & Alert Processing`: Deduplicates alerts by track ID, maps severity, attaches JPEG snapshot, persists `Incident` and `Notification` models.
    6. `6.0 Dashboard & Live Monitoring`: Serves real-time MJPEG streams, live camera statistics, and incident timelines to frontend templates.
- **Class / ER Model Structure**: Detailed in Section 2 (Database Design).

### Hardware/software requirements
- **Minimum Hardware Specifications**:
  - *Cameras*: USB Webcam (DirectShow/MSMF on Windows) or RTSP/HTTP IP Security Cameras (1080p @ 15–30 FPS).
  - *Server / Laptop*: Multi-core x86_64 CPU (Intel Core i5/i7 10th Gen+ or AMD Ryzen 5/7), 8 GB – 16 GB RAM, 100 GB+ SSD storage, optional CUDA-capable NVIDIA GPU (e.g. RTX 3050+) for hardware-accelerated YOLOv8 & DeepFace inference.
- **Software & Operating System Requirements**:
  - *Operating System*: Windows 10/11 or Linux (Ubuntu 20.04/22.04 LTS).
  - *Environment*: Python 3.10+ (tested on Python 3.12.5), Django 6.0.5, OpenCV 4.13.0, Ultralytics YOLOv8 8.4.59, DeepFace 0.0.93, TensorFlow/tf-keras 2.20.1, MySQL 8.0 (production) or SQLite 3 (development).

---

## 2. Chapter 5 — System Design

### System architecture
- **High-Level Architecture**: Decoupled dual-process system:
  1. **Django Web Application Backend**: Handles HTTP/REST API requests, ORM database persistence, session authentication, template rendering, WebSocket notification layers (via Django Channels), and management command orchestration (`run_vanguard`).
  2. **Vision Engine Daemon (`vision_engine`)**: Autonomous multi-threaded Python process (`_capture_loop`, `_stream_loop`, `_detection_loop`, worker threads for `_recognize_persons`). Communicates with Django backend via REST API calls using `AsyncAPIClient` authenticated with `X-Engine-Token` header. Streams live annotated video over HTTP using an internal MJPEG server (`vision_engine/mjpeg_server.py`).
  3. **Database Layer**: SQLite 3 for local development, MySQL 8.0 for production deployment.
- **Deployment View**:
  - `Video Cameras (RTSP/USB)` -> `Vision Engine Daemon (Edge / AI Server Node)` -> `Django Web Server (WSGI/ASGI)` -> `Database (MySQL 8)` -> `Client Web Browser (Bootstrap 5 Dashboard)`.

### Database design
- **Conceptual Design**:
  - `CustomUser`: Security user account with designated role (`ADMIN`, `GUARD`, `RESIDENT`).
  - `Camera`: Physical surveillance camera location and stream endpoint.
  - `Detection`: Bounding box object record generated by YOLOv8.
  - `Incident`: Grouped security event with calculated risk score (0–100) and severity rating.
  - `CameraLiveStats`: Real-time aggregated live counts per camera.
  - `Resident`: Estate resident record with primary photo and enrollment status.
  - `ResidentEmbedding`: Vector embedding record (512 float array) for multi-angle face enhancement.
  - `Visitor`: Estate visitor record with UUID, snapshot, visit counter, and host resident link.
  - `RecognitionEvent`: Log of face recognition outcome (`RESIDENT`, `VISITOR`, `UNKNOWN`).
  - `Notification`: Real-time system alert with severity, snapshot attachment, and live stream jump link.

- **Logical Design (Models Schema)**:
  - `accounts.CustomUser` ([models.py](file:///c:/Users/Michael/Desktop/projects/Vision_Gaurd/accounts/models.py)): `id` (AutoField), `username` (CharField), `password` (CharField), `role` (CharField: ADMIN/GUARD/RESIDENT, default GUARD), `phone_number` (CharField 15, blank/null).
  - `cameras.Camera` ([models.py](file:///c:/Users/Michael/Desktop/projects/Vision_Gaurd/cameras/models.py)): `id` (BigAutoField), `name` (CharField 100), `ip_address` (GenericIPAddressField, blank/null), `stream_url` (CharField 500), `location_name` (CharField 255), `latitude` (DecimalField 9,6, blank/null), `longitude` (DecimalField 9,6, blank/null), `status` (CharField 20: ONLINE/OFFLINE/MAINTENANCE), `is_active` (BooleanField, default True), `created_at`, `updated_at` (DateTimeField).
  - `detections.Detection` ([models.py](file:///c:/Users/Michael/Desktop/projects/Vision_Gaurd/detections/models.py)): `id` (BigAutoField), `camera_id` (FK -> Camera), `label` (CharField 20: PERSON/VEHICLE/BICYCLE/MOTORCYCLE), `class_name` (CharField 50), `confidence` (FloatField), `timestamp` (DateTimeField), `thumbnail` (ImageField), `x_min`, `y_min`, `x_max`, `y_max` (FloatField).
  - `detections.Incident` ([models.py](file:///c:/Users/Michael/Desktop/projects/Vision_Gaurd/detections/models.py)): `id` (BigAutoField), `camera_id` (FK -> Camera, SET_NULL, null=True), `start_time` (DateTimeField), `end_time` (DateTimeField, blank/null), `lead_detection_id` (OneToOne -> Detection, SET_NULL, null=True), `risk_score` (IntegerField 0-100, default 0), `severity` (CharField 10: LOW/MEDIUM/HIGH/CRITICAL), `summary` (TextField), `status` (CharField 20: OPEN/INVESTIGATING/RESOLVED/FALSE_ALARM), `ai_analysis` (TextField).
  - `detections.CameraLiveStats` ([models.py](file:///c:/Users/Michael/Desktop/projects/Vision_Gaurd/detections/models.py)): `id` (BigAutoField), `camera_id` (OneToOne -> Camera), `people_count` (PositiveIntegerField), `vehicle_count` (PositiveIntegerField), `detected_names` (JSONField, default list), `updated_at` (DateTimeField).
  - `residents.Resident` ([models.py](file:///c:/Users/Michael/Desktop/projects/Vision_Gaurd/residents/models.py)): `id` (BigAutoField), `full_name` (CharField 200), `house_number` (CharField 50, db_index=True), `phone_number` (CharField 20), `photo` (ImageField), `face_embedding` (JSONField, default list), `enrollment_status` (CharField 20: PENDING/ENROLLED/FAILED), `enrollment_error` (TextField), `date_registered` (DateTimeField), `is_active` (BooleanField, default True).
  - `residents.ResidentEmbedding` ([models.py](file:///c:/Users/Michael/Desktop/projects/Vision_Gaurd/residents/models.py)): `id` (BigAutoField), `resident_id` (FK -> Resident), `embedding` (JSONField, default list), `quality_score` (FloatField, null/blank), `created_at` (DateTimeField), `is_active` (BooleanField, default True). Index: `(resident, is_active)`.
  - `visitors.Visitor` ([models.py](file:///c:/Users/Michael/Desktop/projects/Vision_Gaurd/visitors/models.py)): `id` (BigAutoField), `visitor_uuid` (UUIDField, default uuid4, unique=True), `face_embedding` (JSONField, default list), `snapshot` (ImageField), `first_seen` (DateTimeField), `last_seen` (DateTimeField), `visit_count` (PositiveIntegerField, default 1), `associated_resident_id` (FK -> Resident, SET_NULL, null=True), `notes` (TextField), `is_known` (BooleanField, default False).
  - `recognition.RecognitionEvent` ([models.py](file:///c:/Users/Michael/Desktop/projects/Vision_Gaurd/recognition/models.py)): `id` (BigAutoField), `camera_id` (FK -> Camera), `person_type` (CharField 20: RESIDENT/VISITOR/UNKNOWN), `resident_id` (FK -> Resident, SET_NULL, null=True), `visitor_id` (FK -> Visitor, SET_NULL, null=True), `confidence` (FloatField), `snapshot` (ImageField), `timestamp` (DateTimeField, db_index=True), `cooldown_key` (CharField 100, db_index=True).
  - `notifications.Notification` ([models.py](file:///c:/Users/Michael/Desktop/projects/Vision_Gaurd/notifications/models.py)): `id` (BigAutoField), `title` (CharField 255), `message` (TextField), `severity` (CharField 10: INFO/WARNING/HIGH), `camera_id` (FK -> Camera, SET_NULL, null=True), `snapshot` (ImageField), `is_read` (BooleanField, default False), `metadata` (JSONField), `created_at` (DateTimeField).

- **Physical Design**:
  - Engine: SQLite 3 (dev) / MySQL 8.0 (production).
  - Indexing: B-tree indexes on `Resident.house_number`, `RecognitionEvent.timestamp`, `RecognitionEvent.cooldown_key`, composite index on `ResidentEmbedding(resident, is_active)`, unique index on `Visitor.visitor_uuid`.
  - Vector Similarity Implementation: Vectors are stored as float arrays in `JSONField` columns. Cosine similarity matching is computed in Python memory (`cosine_similarity` in `vision_engine/recognition.py`) against RAM-cached vector sets (`EmbeddingCache`).
- **ER Diagram Status**: **NOT AVAILABLE / NEEDS TO BE CREATED**

### Module/component design
- **Object Detection Pipeline**: Input: BGR video frames. Output: Track IDs, bounding boxes, object class names, confidence scores. Component: `DetectionEngine` in `vision_engine/detection.py`.
- **Facial Recognition Engine**: Input: Bounded face image crops. Output: 512-dim embedding, identity type (`RESIDENT`, `VISITOR`, `UNKNOWN`), match confidence. Component: `_recognize_persons` in `vision_engine/pipeline.py` using DeepFace `Facenet512` & `retinaface`.
- **Anomaly Detection Module**: Input: Track centroid history & timestamp queue. Output: Loitering events (>120s dwell) & restricted zone entries (`point_in_polygon`). Component: `TrackHistory` and `point_in_polygon` in `vision_engine/behaviour.py`.
- **Alerting Module**: Input: Incident events from engine API calls. Output: `Notification` records, severity classification, track deduplication, base64 snapshot storage. Component: `NotificationService` in `notifications/services.py`.
- **Dashboard Interface Module**: Input: REST API telemetry and ORM queries. Output: Rendered HTML dashboard, live stream grid, camera maps, and notification panels. Component: Views in `dashboard/views.py`, `recognition/views.py`, `notifications/views.py`.
- **Known Technical Debt**:
  1. Default hardcoded engine API fallbacks (`http://localhost:8000` / `http://127.0.0.1:8050`).
  2. Single-camera hardcoded CLI defaults (`camera_id=1`, `stream_url=0`) in `detection_engine.py`.
  3. Track identity cache (`_track_identities`) is process-local to the engine instance; engine restarts clear track cache.
  4. CPU face recognition inference can queue background worker threads under high crowd density.

### Interface/dashboard design
- **Dashboard Pages & Screens**:
  1. `Main Dashboard (/)`: Metrics overview (Cameras, Detections Today, Residents, Visitors), Active Incident Table with risk score badges, Recent Detections feed, and Recognition Feed summary.
  2. `Live Monitor (/monitor/)`: Multi-camera MJPEG stream grid overlaying real-time people/vehicle counts updated dynamically via REST API polling.
  3. `Estate Map (/map/)`: Interactive Leaflet map displaying camera locations by GPS coordinates with online/offline status indicators.
  4. `Residents Directory (/residents/)`: Resident list with search, photo display, enrollment status badge, and link to Enhance Face tool.
  5. `Enhance Face View (/residents/<id>/enhance-face/)`: Interactive webcam capture tool taking up to 10 multi-angle face photos to build multi-embedding profile.
  6. `Visitors Log (/visitors/)`: Directory listing visitors by UUID, displaying visit count, snapshot, notes, host resident link, and known/unknown status.
  7. `Recognition Feed (/recognition/feed/)`: Dedicated feed showing real-time facial recognition events with snapshots, confidence percentage, and timestamps.
  8. `Notification Center (/notifications/)`: Alert list sorted by severity (`INFO`, `WARNING`, `HIGH`) with snapshot preview, "Mark as Read" action, and "View Live" stream jump link.
- **Screenshots / Wireframes Status**: **NOT AVAILABLE / NEEDS TO BE CREATED**

---

## 3. Chapter 6 — System Implementation

### Tools used
- **IDE**: Antigravity IDE / Visual Studio Code / PyCharm.
- **Version Control**: Git & GitHub (`vision_guard` workspace repository).
- **Backend Framework**: Django 6.0.5, Django REST Framework 3.17.1, Django Channels 4.3.2.
- **Computer Vision & Deep Learning**: OpenCV 4.13.0, Ultralytics YOLOv8 8.4.59, DeepFace 0.0.93, tf-keras 2.20.1, NumPy, Pillow.
- **Database Engine**: SQLite 3 (dev), MySQL 8.0 (`mysqlclient 2.2.7` for production).
- **Testing Framework**: Django Test Framework (`django.test.TestCase`, `django.test.Client`).
- **Frontend Technologies**: HTML5, Vanilla JavaScript, Bootstrap 5, Leaflet.js.

### Test plan
- **Modules with Comprehensive Unit Tests**:
  - `residents` ([tests.py](file:///c:/Users/Michael/Desktop/projects/Vision_Gaurd/residents/tests.py)): 13 unit tests covering photo-less enrollment failure, multi-embedding storage, quality scores, deactivation, legacy embedding compatibility, image count limits, pixel dimension limits (5000x5000 rejection), and view authentication.
  - `visitors` ([tests.py](file:///c:/Users/Michael/Desktop/projects/Vision_Gaurd/visitors/tests.py)): 2 unit tests covering new visitor profile creation and repeat visitor visit count incrementing.
  - `recognition` ([tests.py](file:///c:/Users/Michael/Desktop/projects/Vision_Gaurd/recognition/tests.py)): 14 unit tests covering resident identification flow, unknown face visitor creation, 30s cooldown duplicate blocking, cosine similarity math, multi-embedding cache serialization, inactive resident filtering, and resident-over-visitor match prioritization logic.
  - `detections` ([tests.py](file:///c:/Users/Michael/Desktop/projects/Vision_Gaurd/detections/tests.py)): 3 unit tests covering loitering incident creation per cooldown window, restricted zone high-risk incident creation, and threat scoring risk severity thresholds.
  - `notifications` ([tests.py](file:///c:/Users/Michael/Desktop/projects/Vision_Gaurd/notifications/tests.py)): 12 unit tests covering notification ordering, live URL generation, unknown deduplication, loitering deduplication, **resident loitering exclusion business rule**, view live redirects, auto-mark-read, and API integration.
  - `vision_engine` ([tests.py](file:///c:/Users/Michael/Desktop/projects/Vision_Gaurd/vision_engine/tests.py)): 6 unit tests covering bounded track history, dwell time calculation, movement resets, track expiration cleanup, loitering cooldown timers, and `point_in_polygon` restricted zone geometry.
- **Known Low Coverage / Missing Test Areas**:
  - `accounts`: Only default placeholder (`TestCase` without custom user auth test cases).
  - `cameras`: Only default placeholder (`TestCase` without camera CRUD/RTSP endpoint tests).
  - `dashboard`: Only default placeholder (`TestCase` without view rendering test cases).
- **Test Data Used**:
  - Synthetic 512-dim embedding vectors (`[1.0] + [0.0]*511`, `[0.5]*512`).
  - Base64 image strings and PIL-generated images (e.g. 5000x5000 pixel over-sized image for dimension security tests).
  - Synthetic spatial points `(x, y)` and epoch timestamps for geometry tests.
  - Real-world USB webcam input (Stream `0`) under ambient room lighting.

### Test results
- **Django Automated Test Suite Results**:
  - **Command Executed**: `python manage.py test`
  - **Total Tests Found & Executed**: **50 tests**
  - **Pass Status**: **50 Passed, 0 Failed, 0 Errors (OK)**
  - **Execution Time**: **65.266 seconds**
  - **System Checks**: 0 issues identified.
- **Formal Benchmarks**: Empirical mAP metrics or DeepFace ROC curves on estate field video recordings: **NOT AVAILABLE / NEEDS TO BE CREATED**.

### Change-over technique
- **Proposed Change-Over Approach**: **Phased Rollout / Parallel Run Combination**:
  1. *Phase 1 (Parallel Run at Main Gate)*: Deploy Vision Guard system at Main Gate 1 alongside existing security guards and manual logbooks. Run Vision Guard camera stream and automated logging in parallel with manual logbooks for 2–4 weeks to validate recognition accuracy, refine face enrollment, and calibrate loitering dwell thresholds without relying solely on automated alerts.
  2. *Phase 2 (Phased Gate Rollout)*: Expand Vision Guard to internal estate perimeter cameras, visitor exit gates, and restricted utility areas (e.g., server rooms, water pump house). Shift gate guards from manual paper logging to digital validation via the Vision Guard dashboard on tablet/desktop devices.
  3. *Phase 3 (Full Direct Cutover for Incident Reporting)*: Fully replace paper logbooks with automated visitor tracking, resident facial recognition, and instant loitering alert notifications across all estate access points.

### Code sample for appendix
1. **Vision Engine Detection & Recognition Pipeline Loop**:
   - **File**: `vision_engine/pipeline.py` ([lines 179–285](file:///c:/Users/Michael/Desktop/projects/Vision_Gaurd/vision_engine/pipeline.py#L179-L285))
   - **Function**: `VisionGuardEngine._detection_loop`
   - Demonstrates multi-threaded YOLOv8 inference, track identity caching, loitering/zone geometry evaluation, and non-blocking worker thread spawning for facial recognition.

2. **Facial Embedding Generation & Vector Cosine Match Prioritization**:
   - **File**: `vision_engine/recognition.py` ([lines 19–129](file:///c:/Users/Michael/Desktop/projects/Vision_Gaurd/vision_engine/recognition.py#L19-L129))
   - **Functions**: `cosine_similarity`, `generate_embedding`, `match_embedding`
   - Demonstrates DeepFace `Facenet512` representation, normalized vector math, and resident-over-visitor match prioritization.

3. **Behavioral Incident Deduplication & Threat Scoring Service**:
   - **File**: `detections/services/behaviour_incidents.py` ([lines 16–46](file:///c:/Users/Michael/Desktop/projects/Vision_Gaurd/detections/services/behaviour_incidents.py#L16-L46))
   - **Function**: `create_behaviour_incident`
   - Demonstrates risk scoring, threat severity mapping (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`), and database incident deduplication within cooldown windows.

4. **Notification Service & Business Rule Enforcement**:
   - **File**: `notifications/services.py` ([lines 18–101](file:///c:/Users/Michael/Desktop/projects/Vision_Gaurd/notifications/services.py#L18-L101))
   - **Class**: `NotificationService` (`notify_resident`, `notify_unknown`, `notify_loitering`)
   - Demonstrates business rule enforcement (residents excluded from loitering alerts), severity tagging, base64 snapshot attachment, and unread notification deduplication.

