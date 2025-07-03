import logging
import datetime
from datetime import timedelta
from decouple import config

from fastapi import status
from fastapi.exceptions import HTTPException 
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from passlib.context import CryptContext
from jose import jwt, JWTError

from app.db.models import UserModel
from app.schemas.user_schemas import User


SECRET_KEY = config('SECRET_KEY')
ALGORITHM = config('ALGORITHM')

crypt_context = CryptContext(schemes=['sha256_crypt'])

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UserUseCases:
    def __init__(self, db_session: Session):
        self.db_session = db_session

    def user_register(self, user: User):
        user_model = UserModel(
            username=user.username,
            password=crypt_context.hash(user.password)
        )
        try:
            self.db_session.add(user_model)
            self.db_session.commit()
        except IntegrityError:
            logger.error(f"Error registering user: username '{user.username}' already exists.")
            self.db_session.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='User already exists'
            )

    def user_login(self, user: User, expires_in: int = 30):
        user_on_db = self.db_session.query(UserModel).filter_by(username=user.username).first()

        if user_on_db is None:
            logger.warning(f"Login attempt with non-existent user: '{user.username}'.")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Invalid username or password'
            )
        
        if not crypt_context.verify(user.password, user_on_db.password):
            logger.warning(f"Password check failed for user: '{user.username}'.")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Invalid username or password'
            )
        
        exp = datetime.datetime.now(datetime.timezone.utc) + timedelta(minutes=expires_in)

        payload = {
            'sub': user.username,
            'user_id': user_on_db.id,
            'exp': exp
        }

        access_token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

        logger.info(f"User '{user.username}' logged in successfully.")
        return {
            'token_type': 'bearer',
            'access_token': access_token,
            'expires_at': exp.isoformat()
        }
    

    def verify(self, access_token):
        logger.debug(f"Verifying token: {access_token}")
        try:
            logger.debug(f"Secret key used: {SECRET_KEY}")
            logger.debug(f"Algorithm used: {ALGORITHM}")
            data = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Invalid access token'
            )
        
        logger.debug(f"Token successfully decoded. Payload: {data}")
        user_on_db = self.db_session.query(UserModel).filter_by(username=data['sub']).first()

        if user_on_db is None:
            logger.warning(f"User '{data['sub']}' not found in database.")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Invalid access token'
            )
        return data
