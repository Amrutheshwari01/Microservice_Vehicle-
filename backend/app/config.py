import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "AgriLink RTO & Vehicle Registry Microservice"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/v1"
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./rto_service.db")
    
    # Security & Citizen Identity (CIS-M4)
    JWT_SECRET: str = os.getenv("JWT_SECRET", "agrilink-rto-microservice-secret-key-2026")
    JWT_ALGORITHM: str = "HS256"
    MOCK_IDENTITY_URL: str = os.getenv("MOCK_IDENTITY_URL", "http://localhost:8000/v1/mock-identity")
    
    # Wallet Service (CIS-M6)
    WALLET_SERVICE_URL: str = os.getenv("WALLET_SERVICE_URL", "http://localhost:8000/v1/mock-wallet")
    
    # AgriLink System (AGL-M5)
    AGRILINK_SERVICE_URL: str = os.getenv("AGRILINK_SERVICE_URL", "http://localhost:8000/v1/mock-agrilink")
    
    # Registry Adapter
    REGISTRY_MOCK_FAILURE_RATE: float = 0.0 # for testing retries
    REGISTRY_AUTO_VERIFY: bool = True
    
    # Storage
    ENCRYPTED_STORE_PATH: str = os.getenv("ENCRYPTED_STORE_PATH", "./encrypted_filestore")
    
    # SLA & Timeout limits
    BOOKING_HOLD_TIMEOUT_SECONDS: int = 60 # RTO-N02
    
    class Config:
        env_file = ".env"

settings = Settings()

