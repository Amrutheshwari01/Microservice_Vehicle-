import pytest
from app.models.user import User
from app.schemas.auth import UserSignUp, UserLogin
from app.api.v1.auth import signup, login, get_current_user_profile

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

