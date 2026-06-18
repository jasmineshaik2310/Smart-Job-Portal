from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

# MongoDB Atlas connection string
MONGODB_URI = "mongodb+srv://jasmineshaik2310_db_user:8PKSw77bCKz5p2to@cluster0.iwwlfag.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

# Connect to MongoDB
client = MongoClient(MONGODB_URI)

# Database name
db = client.smartjob_portal

# Collections
users_collection = db.users
jobs_collection = db.jobs
resumes_collection = db.resumes
applications_collection = db.applications
matches_collection = db.matches

# Test connection
try:
    client.admin.command('ping')
    print("✅ Connected to MongoDB Atlas successfully!")
except Exception as e:
    print(f"❌ Failed to connect to MongoDB: {e}")