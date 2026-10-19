import os
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Boolean, ForeignKey, String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "CHANGE_THIS_DEVELOPMENT_SECRET_BEFORE_DEPLOYING")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    items: Mapped[list["Item"]] = relationship(back_populates="owner", cascade="all, delete-orphan")

class Item(Base):
    __tablename__ = "items"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(String(500), default="")
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    owner: Mapped[User] = relationship(back_populates="items")

Base.metadata.create_all(bind=engine)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

app = FastAPI(
    title="JWT Authentication Microservice",
    description="A beginner-friendly REST API with registration, login, JWT bearer authentication, and protected CRUD operations.",
    version="1.0.0",
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

DB = Annotated[Session, Depends(get_db)]
TokenStr = Annotated[str, Depends(oauth2_scheme)]

class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_.-]+$")
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=8, max_length=72)

class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    email: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class ItemCreate(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=500)
    completed: bool = False

class ItemUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    completed: bool | None = None

class ItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    description: str
    completed: bool

def create_access_token(subject: str) -> str:
    expires = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": subject, "exp": expires}, SECRET_KEY, algorithm=ALGORITHM)

def authenticate_user(db: Session, username: str, password: str):
    user = db.scalar(select(User).where(User.username == username))
    if not user or not pwd_context.verify(password, user.hashed_password):
        return None
    return user

def get_current_user(token: TokenStr, db: DB) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired authentication token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise credentials_error
    except JWTError:
        raise credentials_error
    user = db.scalar(select(User).where(User.username == username))
    if user is None:
        raise credentials_error
    return user

CurrentUser = Annotated[User, Depends(get_current_user)]

@app.get("/", tags=["Health"])
def root():
    return {"message": "JWT Authentication Microservice is running", "docs": "/docs"}

@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok"}

@app.post("/auth/register", response_model=UserOut, status_code=status.HTTP_201_CREATED, tags=["Authentication"])
def register(payload: UserCreate, db: DB):
    if db.scalar(select(User).where(User.username == payload.username)):
        raise HTTPException(status_code=409, detail="Username already registered")
    if db.scalar(select(User).where(User.email == payload.email)):
        raise HTTPException(status_code=409, detail="Email already registered")
    user = User(
        username=payload.username,
        email=payload.email,
        hashed_password=pwd_context.hash(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@app.post("/auth/login", response_model=Token, tags=["Authentication"])
def login(form: Annotated[OAuth2PasswordRequestForm, Depends()], db: DB):
    user = authenticate_user(db, form.username, form.password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {"access_token": create_access_token(user.username), "token_type": "bearer"}

@app.get("/users/me", response_model=UserOut, tags=["Users"])
def read_me(current_user: CurrentUser):
    return current_user

@app.post("/items", response_model=ItemOut, status_code=201, tags=["Items"])
def create_item(payload: ItemCreate, db: DB, current_user: CurrentUser):
    item = Item(**payload.model_dump(), owner_id=current_user.id)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item

@app.get("/items", response_model=list[ItemOut], tags=["Items"])
def list_items(db: DB, current_user: CurrentUser):
    return list(db.scalars(select(Item).where(Item.owner_id == current_user.id).order_by(Item.id)))

def get_owned_item(db: Session, item_id: int, user_id: int) -> Item:
    item = db.scalar(select(Item).where(Item.id == item_id, Item.owner_id == user_id))
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

@app.get("/items/{item_id}", response_model=ItemOut, tags=["Items"])
def read_item(item_id: int, db: DB, current_user: CurrentUser):
    return get_owned_item(db, item_id, current_user.id)

@app.put("/items/{item_id}", response_model=ItemOut, tags=["Items"])
def update_item(item_id: int, payload: ItemUpdate, db: DB, current_user: CurrentUser):
    item = get_owned_item(db, item_id, current_user.id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item

@app.delete("/items/{item_id}", status_code=204, tags=["Items"])
def delete_item(item_id: int, db: DB, current_user: CurrentUser):
    item = get_owned_item(db, item_id, current_user.id)
    db.delete(item)
    db.commit()
    return None
