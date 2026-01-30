from fastapi import APIRouter, HTTPException, Header
from models import UserCreate, PostCreate, Login, comment
from database import get_database
import jwt as pyjwt
from datetime import datetime, timedelta
from typing import Optional
from bson.objectid import ObjectId

# JWT Configuration
SECRET_KEY = "your-secret-key-change-this-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 24*60*30

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
async def login_user(user: Login):
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
#view posts 
@router.get("/view-posts")
async def view_posts():
    """View all posts"""
    db = get_database()
    posts_collection = db.get_collection("posts")

    posts_cursor = posts_collection.find({})
    posts = []
    async for post in posts_cursor:
        post["_id"] = str(post["_id"])  # Convert ObjectId to string
        posts.append(post)

    return {"posts": posts}



#comment file on post with json in body
@router.post("/comment")
async def comment_on_post(data: comment, authorization: str = Header(None)):
    """Comment on a post"""
    user_email = verify_token(authorization)
    
    db = get_database()
    posts_collection = db.get_collection("posts")
    comment_collection = db.get_collection("comments")

    post = await posts_collection.find_one({"_id": ObjectId(data.post_id)})
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    comment_entry = {
        "post_id": data.post_id,
        "commenter": user_email,
        "comment": data.comment,
        "timestamp": datetime.utcnow()
    }

    await comment_collection.insert_one(comment_entry)
    
    return {"message": "Comment added successfully"}


@router.get("/view-comments/{post_id}")
async def view_comments(post_id: str):
    """View all comments on a post"""
    db = get_database()
    posts_collection = db.get_collection("posts")
    comment_collection = db.get_collection("comments")
    

    post = await posts_collection.find_one({"_id": ObjectId(post_id)})
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    

    comments = await comment_collection.find({"post_id": post_id}).to_list(length=100)
    for comment in comments:
        comment["_id"] = str(comment["_id"])  # Convert ObjectId to string
    return {"posts": [post], "comments": comments}




# I will select comment as the commenter and I will delete it if theres multiple comments from same user on a post I can choose which one to delete

@router.delete("/delete-comment/{post_id}")
async def delete_comment(post_id: str, authorization: str = Header(None)):
    """Delete a comment made by the user on a post"""
    user_email = verify_token(authorization)
    
    db = get_database()
    posts_collection = db.get_collection("collections")

    post = await posts_collection.find_one({"_id": ObjectId(post_id)})
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    await posts_collection.update_one(
        {"_id": ObjectId(post_id)},
        {"$pull": {"comments": {"commenter": user_email}}}
    )

    return {"message": "Comment deleted successfully"}