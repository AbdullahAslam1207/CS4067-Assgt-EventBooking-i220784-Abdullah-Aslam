from fastapi import FastAPI, HTTPException, Depends 
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select
from sqlalchemy import Column, Integer, String, MetaData, Table


#againagainagainagainjjj
DATABASE_URL = "postgresql+asyncpg://postgres:1234@localhost:5432/users_db"

engine = create_async_engine(DATABASE_URL, echo=True)
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
metadata = MetaData()

users_table = Table(
    "users", metadata,
    Column("id", Integer, primary_key=True, index=True),
    Column("username", String, unique=True, index=True),
    Column("password", String),
)

app = FastAPI()

class LoginRequest(BaseModel):
    username: str
    password: str

async def get_db():
    async with async_session() as session:
        yield session

@app.post("/login")
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    query = select(users_table).where(users_table.c.username == request.username, users_table.c.password == request.password)
    result = await db.execute(query)
    user = result.fetchone()
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    return {"message": "Login successful", "user_id": user.id}

@app.get('/')
async def home():
    return {"Hello": "kaisay ho"}
