from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from app.models.database import User, get_db

# Конфигурация
SECRET_KEY = "super_secret_key_vkr" # В реальности хранится в .env
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

import bcrypt

def get_password_hash(password: str):
    # Превращаем строку в байты
    pwd_bytes = password.encode('utf-8')
    # Генерируем соль
    salt = bcrypt.gensalt()
    # Хешируем
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    # Возвращаем как строку для хранения в БД
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str):
    return bcrypt.checkpw(
        plain_password.encode('utf-8'), 
        hashed_password.encode('utf-8')
    )

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Не удалось проверить учетные данные",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # 1. Декодируем токен
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # 2. Ищем пользователя в базе данных
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    
    # 3. Возвращаем объект пользователя
    return user




def check_admin_role(current_user: User = Depends(get_current_user)):
    """Только для роли admin"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Нет доступа"
        )
    return current_user

def check_support_role(current_user: User = Depends(get_current_user)):
    """Для ролей support и admin"""
    if current_user.role not in ["support", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Доступ запрещен: только для сотрудников поддержки"
        )
    return current_user