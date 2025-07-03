import logging

from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm

from app.depends.depends import get_db_session, token_verifier
from app.auth.auth_user import UserUseCases
from app.schemas.user_schemas import User


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

user_router = APIRouter(prefix='/user')
test_router = APIRouter(prefix='/test')

@user_router.post('/register')
def user_register(user:User, db_session: Session = Depends(get_db_session)):

    uc = UserUseCases(db_session=db_session)
    uc.user_register(user=user)
    return JSONResponse(
        content={'msg': 'success'},
        status_code=status.HTTP_201_CREATED
    )


@user_router.post('/login')
def user_login(login_request_form: OAuth2PasswordRequestForm = Depends(), db_session: Session = Depends(get_db_session)):

    uc = UserUseCases(db_session=db_session)

    user = User(
        username=login_request_form.username,
        password=login_request_form.password
    )

    try:
        token_data = uc.user_login(user=user, expires_in=60)
        logger.info(f"Login successful for user: {user.username}")
        return JSONResponse(
            content=token_data,
            status_code=status.HTTP_200_OK
        )
    except Exception as e:
        logger.error(f"Login failed for user {user.username}: {e}")


@test_router.get('/test')
def test_user_verify(token_verify = Depends(token_verifier)):
    return 'It works!'
