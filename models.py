from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

class PostCreate(BaseModel):
    title: str
    content: str

class Login(BaseModel):
    email: EmailStr
    password: str

class comment(BaseModel):
    post_id: str
    comment: str