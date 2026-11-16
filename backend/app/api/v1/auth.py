import os
import json
import logging
import hashlib
import binascii
import jwt
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.schemas.auth import (
    UserSignUp,
    UserLogin,
    AuthResponse,
    UserProfile,
    FaceLoginRequest,
    FaceEnrollRequest
)
from app.inter_service.wallet_client import _MOCK_WALLET_BALANCES, WalletClient
from app.api.deps import get_current_actor
from app.utils.face_service import (
    extract_face_descriptor,
    compare_face_descriptors,
    match_face_against_users
)

logger = logging.getLogger("auth_service")

router = APIRouter(prefix="/auth", tags=["Authentication & Citizen Accounts"])

def hash_password(password: str) -> str:
    salt = hashlib.sha256(os.urandom(60)).hexdigest().encode('ascii')
    pwdhash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    pwdhash = binascii.hexlify(pwdhash)
    return (salt + pwdhash).decode('ascii')

def verify_password(stored_password: str, provided_password: str) -> bool:
    salt = stored_password[:64]
    stored_hash = stored_password[64:]
    pwdhash = hashlib.pbkdf2_hmac('sha256', provided_password.encode('utf-8'), salt.encode('ascii'), 100000)
    pwdhash = binascii.hexlify(pwdhash).decode('ascii')
    return pwdhash == stored_hash

def create_jwt_for_user(user: User) -> str:
    personas = ["CITIZEN"]
    if user.role == "VEHICLE_OWNER":
        personas.extend(["VEHICLE_OWNER", "RENTER"])
    elif user.role == "DELIVERY_PERSON":
        personas.extend(["DELIVERY_PERSON", "RENTER"])
    elif user.role == "ADMIN":
        personas.extend(["ADMIN", "RTO_OFFICIAL", "VEHICLE_OWNER", "RENTER"])
    else:
        personas.append("RENTER")

    lic_classes = [c.strip() for c in user.driving_licence_classes.split(",") if c.strip()]
    
    claims = {
        "sub": user.id,
        "citizen_id": user.id,
        "name": user.name,
        "email": user.email,
        "kyc_tier": user.kyc_tier,
        "personas": personas,
        "driving_licence_classes": lic_classes,
        "exp": datetime.utcnow() + timedelta(days=14),
        "iss": "agrilink-cis-identity"
    }
    return jwt.encode(claims, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def signup(user_in: UserSignUp, db: Session = Depends(get_db)):
    """
    Register a new user with their chosen credentials and optional face biometrics.
    """
    clean_email = user_in.email.lower().strip()
    existing = db.query(User).filter(User.email == clean_email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"An account with email '{clean_email}' already exists. Please sign in instead."
        )

    # Process face enrollment if image provided
    face_desc_json = None
    face_thumb = None
    if user_in.face_image:
        try:
            desc_vec, thumb, _ = extract_face_descriptor(user_in.face_image)
            face_desc_json = json.dumps(desc_vec)
            face_thumb = thumb
        except Exception as e:
            logger.warning(f"Could not extract face descriptor during signup: {e}")

    hashed = hash_password(user_in.password)
    user = User(
        name=user_in.name.strip(),
        email=clean_email,
        phone=user_in.phone,
        password_hash=hashed,
        role=user_in.role.upper(),
        kyc_tier=user_in.kyc_tier.upper(),
        driving_licence_classes=user_in.driving_licence_classes.upper(),
        face_descriptor=face_desc_json,
        face_thumbnail=face_thumb
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Initialize wallet with ₹30,000 for rental holds / transactions
    _MOCK_WALLET_BALANCES[user.id] = 30000.0

    token = create_jwt_for_user(user)
    lic_classes = [c.strip() for c in user.driving_licence_classes.split(",") if c.strip()]
    personas = ["CITIZEN", user.role.upper()]
    if user.role.upper() == "VEHICLE_OWNER":
        personas.append("RENTER")

    return AuthResponse(
        access_token=token,
        token_type="Bearer",
        user=UserProfile(
            id=user.id,
            name=user.name,
            email=user.email,
            phone=user.phone,
            role=user.role,
            kyc_tier=user.kyc_tier,
            personas=personas,
            driving_licence_classes=lic_classes,
            has_face_enrolled=bool(user.face_descriptor),
            face_thumbnail=user.face_thumbnail,
            wallet_balance=_MOCK_WALLET_BALANCES.get(user.id, 30000.0)
        )
    )

@router.post("/login", response_model=AuthResponse)
def login(login_in: UserLogin, db: Session = Depends(get_db)):
    """
    Authenticate using email and password.
    """
    clean_email = login_in.email.lower().strip()
    user = db.query(User).filter(User.email == clean_email).first()
    if not user or not verify_password(user.password_hash, login_in.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password. Please verify your credentials."
        )

    token = create_jwt_for_user(user)
    lic_classes = [c.strip() for c in user.driving_licence_classes.split(",") if c.strip()]
    personas = ["CITIZEN", user.role]
    if user.role == "VEHICLE_OWNER":
        personas.append("RENTER")

    # Ensure wallet balance exists
    if user.id not in _MOCK_WALLET_BALANCES:
        _MOCK_WALLET_BALANCES[user.id] = 25000.0

    return AuthResponse(
        access_token=token,
        token_type="Bearer",
        user=UserProfile(
            id=user.id,
            name=user.name,
            email=user.email,
            phone=user.phone,
            role=user.role,
            kyc_tier=user.kyc_tier,
            personas=personas,
            driving_licence_classes=lic_classes,
            has_face_enrolled=bool(user.face_descriptor),
            face_thumbnail=user.face_thumbnail,
            wallet_balance=_MOCK_WALLET_BALANCES.get(user.id, 25000.0)
        )
    )

@router.post("/face-login", response_model=AuthResponse)
def face_login(req: FaceLoginRequest, db: Session = Depends(get_db)):
    """
    Authenticate securely using face recognition.
    Supports 1:1 face verification if email/username is provided, or 1:N recognition against enrolled fleet users.
    """
    try:
        captured_desc, thumb, detected = extract_face_descriptor(req.face_image)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unable to process face image: {str(e)}"
        )

    matched_user = None

    if req.email:
        clean_email = req.email.lower().strip()
        user = db.query(User).filter(User.email == clean_email).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No account found registered with email '{clean_email}'."
            )
        if not user.face_descriptor:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Face biometric is not yet enrolled for this account. Please sign in with your password to enroll your face."
            )
        try:
            stored_desc = json.loads(user.face_descriptor)
            similarity = compare_face_descriptors(captured_desc, stored_desc)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Biometric descriptor comparison encountered an internal error."
            )

        if similarity < 0.65:
            conf_pct = max(0, int(similarity * 100))
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Face verification failed. Match confidence was {conf_pct}% (minimum required: 65%). Please ensure your face is well-lit and directly facing the camera."
            )
        matched_user = user
    else:
        # 1:N matching across all enrolled users
        candidates = db.query(User).filter(User.face_descriptor.isnot(None)).all()
        if not candidates:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No registered accounts have face biometrics enrolled yet. Please create an account or sign in with password first."
            )
        match_result = match_face_against_users(captured_desc, candidates, threshold=0.65)
        if not match_result:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Face not recognized. Please face the camera squarely in good lighting or enter your email and password."
            )
        matched_user, similarity = match_result

    token = create_jwt_for_user(matched_user)
    lic_classes = [c.strip() for c in matched_user.driving_licence_classes.split(",") if c.strip()]
    personas = ["CITIZEN", matched_user.role]
    if matched_user.role == "VEHICLE_OWNER":
        personas.append("RENTER")

    if matched_user.id not in _MOCK_WALLET_BALANCES:
        _MOCK_WALLET_BALANCES[matched_user.id] = 25000.0

    return AuthResponse(
        access_token=token,
        token_type="Bearer",
        user=UserProfile(
            id=matched_user.id,
            name=matched_user.name,
            email=matched_user.email,
            phone=matched_user.phone,
            role=matched_user.role,
            kyc_tier=matched_user.kyc_tier,
            personas=personas,
            driving_licence_classes=lic_classes,
            has_face_enrolled=True,
            face_thumbnail=matched_user.face_thumbnail,
            wallet_balance=_MOCK_WALLET_BALANCES.get(matched_user.id, 25000.0)
        )
    )

@router.post("/enroll-face", response_model=UserProfile)
def enroll_face(
    req: FaceEnrollRequest,
    actor: dict = Depends(get_current_actor),
    db: Session = Depends(get_db)
):
    """
    Enroll or update face biometrics for the authenticated user.
    """
    citizen_id = actor.get("citizen_id")
    user = db.query(User).filter(User.id == citizen_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User account not found.")

    try:
        desc_vec, thumb, _ = extract_face_descriptor(req.face_image)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unable to process face image: {str(e)}"
        )

    user.face_descriptor = json.dumps(desc_vec)
    user.face_thumbnail = thumb
    db.commit()
    db.refresh(user)

    lic_classes = [c.strip() for c in user.driving_licence_classes.split(",") if c.strip()]
    personas = ["CITIZEN", user.role]
    if user.role == "VEHICLE_OWNER":
        personas.append("RENTER")

    return UserProfile(
        id=user.id,
        name=user.name,
        email=user.email,
        phone=user.phone,
        role=user.role,
        kyc_tier=user.kyc_tier,
        personas=personas,
        driving_licence_classes=lic_classes,
        has_face_enrolled=True,
        face_thumbnail=user.face_thumbnail,
        wallet_balance=_MOCK_WALLET_BALANCES.get(user.id, 25000.0)
    )

@router.get("/me", response_model=UserProfile)
def get_current_user_profile(
    actor: dict = Depends(get_current_actor),
    db: Session = Depends(get_db)
):
    """
    Retrieve the current logged-in user's profile and live balance.
    """
    citizen_id = actor.get("citizen_id")
    user = db.query(User).filter(User.id == citizen_id).first()
    
    if user:
        lic_classes = [c.strip() for c in user.driving_licence_classes.split(",") if c.strip()]
        personas = ["CITIZEN", user.role]
        if user.role == "VEHICLE_OWNER":
            personas.append("RENTER")
        return UserProfile(
            id=user.id,
            name=user.name,
            email=user.email,
            phone=user.phone,
            role=user.role,
            kyc_tier=user.kyc_tier,
            personas=personas,
            driving_licence_classes=lic_classes,
            has_face_enrolled=bool(user.face_descriptor),
            face_thumbnail=user.face_thumbnail,
            wallet_balance=_MOCK_WALLET_BALANCES.get(user.id, 25000.0)
        )
    else:
        # Fallback for mock demo profiles
        return UserProfile(
            id=actor.get("citizen_id", "GUEST"),
            name=actor.get("name", "Guest"),
            email=actor.get("email", "guest@agrilink.in"),
            role="RENTER",
            kyc_tier=actor.get("kyc_tier", "T1"),
            personas=actor.get("personas", ["CITIZEN"]),
            driving_licence_classes=actor.get("driving_licence_classes", ["LMV"]),
            has_face_enrolled=False,
            face_thumbnail=None,
            wallet_balance=_MOCK_WALLET_BALANCES.get(actor.get("citizen_id"), 20000.0)
        )
