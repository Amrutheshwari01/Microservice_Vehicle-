import os
from pydantic_settings import BaseSettings

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_DEFAULT_STORE = os.path.join(_REPO_ROOT, "encrypted_filestore")
_DEFAULT_DB = f"sqlite:///{os.path.join(_REPO_ROOT, 'rto_service.db').replace(os.sep, '/')}"

class Settings(BaseSettings):
    PROJECT_NAME: str = "AgriLink Commercial Fleet & Logistics Platform"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/v1"
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", _DEFAULT_DB)
    
    # Security & User Identity
    JWT_SECRET: str = os.getenv("JWT_SECRET", "agrilink-fleet-platform-secret-key-2026")
    JWT_ALGORITHM: str = "HS256"
    MOCK_IDENTITY_URL: str = os.getenv("MOCK_IDENTITY_URL", "http://localhost:8000/v1/mock-identity")
    
    # Wallet Service
    WALLET_SERVICE_URL: str = os.getenv("WALLET_SERVICE_URL", "http://localhost:8000/v1/mock-wallet")
    
    # Logistics Integration
    AGRILINK_SERVICE_URL: str = os.getenv("AGRILINK_SERVICE_URL", "http://localhost:8000/v1/mock-agrilink")
    
    # Registry Adapter
    REGISTRY_MOCK_FAILURE_RATE: float = 0.0 # for testing retries
    REGISTRY_AUTO_VERIFY: bool = True
    
    # Document Storage
    ENCRYPTED_STORE_PATH: str = os.getenv("ENCRYPTED_STORE_PATH", _DEFAULT_STORE)
    
    # Booking SLA limits
    BOOKING_HOLD_TIMEOUT_SECONDS: int = 60
    
    class Config:
        env_file = ".env"

settings = Settings()
