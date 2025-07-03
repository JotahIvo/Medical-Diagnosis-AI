import logging

from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.db.connection import Session as ss
from app.auth.auth_user import UserUseCases


oauth_scheme = OAuth2PasswordBearer(tokenUrl='/user/login')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_db_session():
    try:
        session = ss()
        yield session
    finally:
        session.close()


def token_verifier(db_session: Session = Depends(get_db_session), token = Depends(oauth_scheme)):
    
    logger.debug(f"Token received: {token}")
    try:
        uc = UserUseCases(db_session=db_session)
        user_info = uc.verify(access_token=token)
        logger.debug(f"User information (decoded from token): {user_info}")
        return user_info
    except HTTPException as e:
        logger.error(f"Authentication error: {e.detail}")
        raise 
    except Exception as e:
        logger.exception(f"Unexpected error while verifying token: {e}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token")
