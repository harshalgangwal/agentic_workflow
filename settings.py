"""
config/settings.py
Central configuration for the claims processing system.
Loads from environment variables with sensible defaults.
"""
import os
from pathlib import Path
from dotenv import load_dotenv
 
load_dotenv()
 
BASE_DIR = Path(__file__).parent.parent
 
# Ollama settings
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
OLLAMA_VISION_MODEL = os.getenv("OLLAMA_VISION_MODEL", "qwen2.5:7b")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "120"))
 
# Database settings
DB_PATH = os.getenv("DB_PATH", str(BASE_DIR / "database" / "claims.db"))
 
# Policy settings
POLICY_PATH = os.getenv("POLICY_PATH", str(BASE_DIR / "policies" / "policy_terms.json"))
 
# File upload settings
UPLOAD_DIR = os.getenv("UPLOAD_DIR", str(BASE_DIR / "uploads"))
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "20"))
 
# OCR settings
OCR_CONFIDENCE_THRESHOLD = float(os.getenv("OCR_CONFIDENCE_THRESHOLD", "0.6"))
OCR_LANGUAGE = os.getenv("OCR_LANGUAGE", "en")
 
# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_DIR = os.getenv("LOG_DIR", str(BASE_DIR / "logs"))
 
# Confidence thresholds
CONFIDENCE_FULL_PIPELINE = 0.90
CONFIDENCE_DEGRADED = 0.65
CONFIDENCE_HIGH_VALUE_MANUAL = 0.80
 
# Ensure directories exist
Path(UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
Path(LOG_DIR).mkdir(parents=True, exist_ok=True)
Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
