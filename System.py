from fastapi import APIRouter, HTTPException, Header
from models import UserCreate, PostCreate
from database import get_database
import jwt as pyjwt
from datetime import datetime, timedelta
from typing import Optional
from bson.objectid import ObjectId

# JWT Configuration
SECRET_KEY = "your-secret-key-change-this-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

router = APIRouter()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = pyjwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str = Header(None)):
    """Verify JWT token and extract user email"""
    if not token:
        raise HTTPException(status_code=401, detail="Token missing")
    
    try:
        if token.startswith("Bearer "):
            token = token[7:]
        payload = pyjwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("email")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return email
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except pyjwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


@router.post("/register")
async def register_user(user: UserCreate):
    """Register a new user"""
    db = get_database()
    users_collection = db.get_collection("users")
    
    if await users_collection.find_one({"email": user.email}):
        raise HTTPException(status_code=400, detail="User already exists")

    user_dict = {
        "username": user.username,
        "email": user.email,
        "password": user.password
    }

    await users_collection.insert_one(user_dict)
    return {"message": "User registered successfully"}


@router.post("/login")
async def login_user(user: UserCreate):
    """Login user and return JWT token"""
    db = get_database()
    users_collection = db.get_collection("users")
    
    existing_user = await users_collection.find_one({"email": user.email})
    if not existing_user or existing_user["password"] != user.password:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"email": user.email}, expires_delta=access_token_expires)
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/create-post")
async def create_post(post: PostCreate, authorization: str = Header(None)):
    """Create a new post - author is extracted from JWT token"""
    user_email = verify_token(authorization)
    
    db = get_database()
    posts_collection = db.get_collection("posts")

    post_dict = {
        "title": post.title,
        "content": post.content,
        "author": user_email,
        "comments": []
    }

    result = await posts_collection.insert_one(post_dict)
    return {"message": "Post created successfully", "post_id": str(result.inserted_id)}


@router.post("/comment")
async def comment_on_post(post_id: str, comment: str, authorization: str = Header(None)):
    """Add comment to a post - commenter is extracted from JWT token"""
    user_email = verify_token(authorization)
    
    db = get_database()
    posts_collection = db.get_collection("posts")

    post = await posts_collection.find_one({"_id": ObjectId(post_id)})
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    comment_dict = {
        "commenter": user_email,
        "comment": comment,
    }

    if "comments" not in post:
        post["comments"] = []
    post["comments"].append(comment_dict)

    await posts_collection.update_one({"_id": ObjectId(post_id)}, {"$set": {"comments": post["comments"]}})
    return {"message": "Comment added successfully"}


@router.get("/view-comments/{post_id}")
async def view_comments(post_id: str):
    """View all comments on a post"""
    db = get_database()
    posts_collection = db.get_collection("posts")

    post = await posts_collection.find_one({"_id": ObjectId(post_id)})
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    return {"comments": post.get("comments", [])}


@router.delete("/delete-comment/{post_id}")
async def delete_comment(post_id: str, comment: str, authorization: str = Header(None)):
    """Delete a comment - only the user who wrote it can delete"""
    user_email = verify_token(authorization)
    
    db = get_database()
    posts_collection = db.get_collection("posts")

    post = await posts_collection.find_one({"_id": ObjectId(post_id)})
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    comments = post.get("comments", [])
    updated_comments = [c for c in comments if not (c["commenter"] == user_email and c["comment"] == comment)]

    if len(updated_comments) == len(comments):
        raise HTTPException(status_code=403, detail="Comment not found or you don't have permission to delete")

    await posts_collection.update_one({"_id": ObjectId(post_id)}, {"$set": {"comments": updated_comments}})
    return {"message": "Comment deleted successfully"}
