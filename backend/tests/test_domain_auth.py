import pytest
import cv2
import numpy as np
import base64
from fastapi import HTTPException
from app.models.user import User
from app.schemas.auth import (
    UserSignUp,
    UserLogin,
    FaceLoginRequest,
    FaceEnrollRequest
)
from app.api.v1.auth import signup, login, face_login, enroll_face, get_current_user_profile

def make_test_face_b64(eye_pos: int = 65, mouth_w: int = 20) -> str:
    """Generates synthetic face image for testing biometrics."""
    img = np.full((160, 160, 3), 220, dtype=np.uint8)
    cv2.ellipse(img, (80, 80), (50, 65), 0, 0, 360, (180, 200, 230), -1)
    cv2.circle(img, (60, eye_pos), 8, (40, 40, 40), -1)
    cv2.circle(img, (100, eye_pos), 8, (40, 40, 40), -1)
    cv2.line(img, (80, 75), (80, 95), (60, 60, 60), 2)
    cv2.ellipse(img, (80, 115), (mouth_w, 10), 0, 0, 180, (50, 50, 150), 3)
    _, buf = cv2.imencode('.jpg', img)
    return "data:image/jpeg;base64," + base64.b64encode(buf).decode('ascii')

def test_user_signup_and_login_flow(db):
    # 1. Sign up new custom user
    signup_data = UserSignUp(
        name="Anand Kumar",
        email="anand@example.com",
        password="secretpassword123",
        phone="+91 98111 22334",
        role="VEHICLE_OWNER",
        kyc_tier="T2",
        driving_licence_classes="LMV,HMV"
    )
    res = signup(signup_data, db)
    assert res.access_token is not None
    assert res.user.email == "anand@example.com"
    assert res.user.name == "Anand Kumar"
    assert res.user.role == "VEHICLE_OWNER"
    assert res.user.wallet_balance == 30000.0

    # 2. Login with correct credentials
    login_data = UserLogin(email="anand@example.com", password="secretpassword123")
    login_res = login(login_data, db)
    assert login_res.access_token is not None
    assert login_res.user.email == "anand@example.com"

    # 3. Login with wrong password must fail
    wrong_login = UserLogin(email="anand@example.com", password="wrongpassword")
    with pytest.raises(Exception):
        login(wrong_login, db)

    # 4. Duplicate email sign up must fail
    with pytest.raises(Exception):
        signup(signup_data, db)

def test_username_auto_qualify(db):
    # Entering 'guest' or 'myuser' without '@' should auto-qualify to @agrilink.in
    signup_data = UserSignUp(
        name="Guest User",
        email="guest",
        password="guestpassword123",
        role="RENTER"
    )
    res = signup(signup_data, db)
    assert res.user.email == "guest@agrilink.in"

    # Login with plain 'guest'
    login_data = UserLogin(email="guest", password="guestpassword123")
    l_res = login(login_data, db)
    assert l_res.user.email == "guest@agrilink.in"

def test_face_signup_and_login_workflow(db):
    face_img = make_test_face_b64(eye_pos=65, mouth_w=20)
    
    # 1. Register with Face biometric image
    signup_data = UserSignUp(
        name="Himanshu FaceTest",
        email="himanshu.facetest@example.com",
        password="securepass456",
        role="RENTER",
        face_image=face_img
    )
    reg_res = signup(signup_data, db)
    assert reg_res.user.has_face_enrolled is True
    assert reg_res.user.face_thumbnail is not None
    assert reg_res.access_token is not None

    # Check user record in DB
    user_db = db.query(User).filter(User.email == "himanshu.facetest@example.com").first()
    assert user_db is not None
    assert user_db.face_descriptor is not None

    # 2. Successful 1:1 Face Login with email & face
    # Minor variance in same person's face (e.g. eye_pos=65, mouth_w=22)
    same_person_img = make_test_face_b64(eye_pos=65, mouth_w=22)
    face_req = FaceLoginRequest(
        email="himanshu.facetest@example.com",
        face_image=same_person_img
    )
    f_res = face_login(face_req, db)
    assert f_res.access_token is not None
    assert f_res.user.email == "himanshu.facetest@example.com"
    assert f_res.user.name == "Himanshu FaceTest"

    # 3. Successful 1:N Biometric Face Login without entering email
    n_req = FaceLoginRequest(face_image=same_person_img)
    n_res = face_login(n_req, db)
    assert n_res.access_token is not None
    assert n_res.user.email == "himanshu.facetest@example.com"

    # 4. Face mismatch rejection
    # Impostor with different face structure (eye_pos=45, mouth_w=10)
    impostor_img = make_test_face_b64(eye_pos=45, mouth_w=10)
    bad_req = FaceLoginRequest(
        email="himanshu.facetest@example.com",
        face_image=impostor_img
    )
    with pytest.raises(HTTPException) as exc_info:
        face_login(bad_req, db)
    assert exc_info.value.status_code == 401
    assert "verification failed" in exc_info.value.detail.lower()

def test_face_enroll_endpoint(db):
    # User signs up without face
    signup_data = UserSignUp(
        name="Kavita Rao",
        email="kavita@example.com",
        password="kavitapassword",
        role="RENTER"
    )
    signup_res = signup(signup_data, db)
    assert signup_res.user.has_face_enrolled is False

    # Try face login before enrollment -> should fail
    face_img = make_test_face_b64(eye_pos=60, mouth_w=25)
    with pytest.raises(HTTPException) as exc_info:
        face_login(FaceLoginRequest(email="kavita@example.com", face_image=face_img), db)
    assert exc_info.value.status_code == 400

    # User enrolls face biometrics
    actor = {"citizen_id": signup_res.user.id}
    enroll_req = FaceEnrollRequest(face_image=face_img)
    updated_profile = enroll_face(enroll_req, actor=actor, db=db)
    assert updated_profile.has_face_enrolled is True

    # Now face login should succeed
    login_succ = face_login(FaceLoginRequest(email="kavita@example.com", face_image=face_img), db)
    assert login_succ.user.email == "kavita@example.com"

