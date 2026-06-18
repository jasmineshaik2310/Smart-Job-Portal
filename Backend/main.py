from fastapi import FastAPI, HTTPException, Form, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
import os
import json
from datetime import datetime, timedelta
from typing import Optional, List
import uuid
import hashlib
import random
from bson import ObjectId
from pymongo import MongoClient
import motor.motor_asyncio
from dotenv import load_dotenv
import certifi
from urllib.parse import quote_plus

# Load environment variables
load_dotenv()

# MongoDB Atlas connection string - Get from environment variable
# If you want to use the password with # character, it will be automatically encoded
MONGODB_USERNAME = os.getenv('MONGODB_USERNAME', 'jasmineshaik2310_db_user')
MONGODB_PASSWORD = os.getenv('MONGODB_PASSWORD', 'jasmineshaik36#23#')
MONGODB_CLUSTER = os.getenv('MONGODB_CLUSTER', 'cluster0.iwwlfag.mongodb.net')
MONGODB_DATABASE = os.getenv('MONGODB_DATABASE', 'smartjob_portal')

# Encode the password to handle special characters like #
encoded_password = quote_plus(MONGODB_PASSWORD)

# Construct MongoDB URI
MONGODB_URI = os.getenv('MONGODB_URI', 
    f"mongodb+srv://{MONGODB_USERNAME}:{encoded_password}@{MONGODB_CLUSTER}/{MONGODB_DATABASE}?retryWrites=true&w=majority&appName=Cluster0"
)

# ==================== MONGODB CONNECTION WITH BETTER ERROR HANDLING ====================

print(f"🔌 Connecting to MongoDB Atlas...")
print(f"📊 Database: {MONGODB_DATABASE}")
print(f"👤 Username: {MONGODB_USERNAME}")

# Define MockCollection class here so it's available globally
class MockCollection:
    def __init__(self):
        self.data = []
        self.counter = 0
    
    def find_one(self, *args, **kwargs):
        return None
    
    def find(self, *args, **kwargs):
        return []
    
    def insert_one(self, data):
        self.counter += 1
        class Result:
            inserted_id = str(self.counter)
        return Result()
    
    def update_one(self, *args, **kwargs):
        pass
    
    def count_documents(self, *args, **kwargs):
        return 0

# Try multiple connection methods but with timeout
connected = False
client = None

# Method 1: Standard connection with certifi
try:
    print("🔄 Attempting connection with certifi...")
    client = MongoClient(
        MONGODB_URI,
        tlsCAFile=certifi.where(),
        serverSelectionTimeoutMS=5000,  # Reduced timeout
        connectTimeoutMS=5000,
        socketTimeoutMS=5000
    )
    # Test connection with short timeout
    client.admin.command('ping', serverSelectionTimeoutMS=5000)
    print("✅ Connected to MongoDB Atlas successfully!")
    connected = True
except Exception as e:
    print(f"⚠️ Method 1 failed: {str(e)[:100]}...")

# Method 2: With tlsAllowInvalidCertificates
if not connected:
    try:
        print("🔄 Attempting connection with tlsAllowInvalidCertificates...")
        client = MongoClient(
            MONGODB_URI,
            tlsCAFile=certifi.where(),
            tlsAllowInvalidCertificates=True,
            serverSelectionTimeoutMS=5000
        )
        client.admin.command('ping', serverSelectionTimeoutMS=5000)
        print("✅ Connected to MongoDB Atlas successfully!")
        connected = True
    except Exception as e:
        print(f"⚠️ Method 2 failed: {str(e)[:100]}...")

if not connected:
    print("\n❌ MongoDB connection failed. Using mock collections for development.")
    print("✅ Server will continue with in-memory data.")
    
    # Use mock collections
    users_collection = MockCollection()
    jobs_collection = MockCollection()
    resumes_collection = MockCollection()
    applications_collection = MockCollection()
    matches_collection = MockCollection()
    
    print("✅ Using mock collections for development")
else:
    # Database and collections
    db = client[MONGODB_DATABASE]
    users_collection = db.users
    jobs_collection = db.jobs
    resumes_collection = db.resumes
    applications_collection = db.applications
    matches_collection = db.matches
    
    print(f"\n✅ MongoDB connected successfully!")
    print(f"📊 Using database: {MONGODB_DATABASE}")

app = FastAPI(title="SmartJob Portal", version="1.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create directories
os.makedirs("uploads", exist_ok=True)
os.makedirs("static", exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory="../static"), name="static")

# Helper functions
def get_password_hash(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(plain_password, hashed_password):
    return hashlib.sha256(plain_password.encode()).hexdigest() == hashed_password

# ==================== FIXED TOKEN FUNCTIONS ====================

def generate_token(email):
    token = hashlib.sha256(f"{email}{datetime.now().timestamp()}".encode()).hexdigest()
    
    # For mock collections, just return the token without storing
    if isinstance(users_collection, MockCollection):
        return token
    
    # Store token in user document for real MongoDB
    users_collection.update_one(
        {"email": email},
        {"$set": {"token": token, "token_created": datetime.now()}},
        upsert=True
    )
    return token

def verify_token(token):
    if not token:
        return None
    
    # For development with mock collections, accept any token
    if isinstance(users_collection, MockCollection):
        # In development mode, return a dummy email
        return "jobseeker@demo.com"
    
    # Normal verification for real MongoDB
    user = users_collection.find_one({"token": token})
    if user:
        token_created = user.get("token_created")
        if token_created and datetime.now() - token_created < timedelta(hours=24):
            return user["email"]
    return None

# ============================================================

def serialize_doc(doc):
    """Convert MongoDB document to JSON serializable format"""
    if doc is None:
        return None
    
    if "_id" in doc:
        doc["_id"] = str(doc["_id"])
    
    # Convert ObjectId fields to strings
    for key, value in doc.items():
        if isinstance(value, ObjectId):
            doc[key] = str(value)
        elif isinstance(value, datetime):
            doc[key] = value.isoformat()
    
    return doc

# ==================== RULE-BASED MATCHING ENGINE ====================

# Predefined rules: Skill -> Job Roles mapping
SKILL_TO_JOB_RULES = {
    "Python": [
        {"title": "Python Developer", "weight": 10},
        {"title": "Backend Developer", "weight": 8},
        {"title": "Data Scientist", "weight": 9},
        {"title": "Machine Learning Engineer", "weight": 10},
        {"title": "AI Engineer", "weight": 9}
    ],
    "Java": [
        {"title": "Java Developer", "weight": 10},
        {"title": "Backend Developer", "weight": 8},
        {"title": "Android Developer", "weight": 9},
        {"title": "Software Engineer", "weight": 7}
    ],
    "JavaScript": [
        {"title": "Frontend Developer", "weight": 10},
        {"title": "Full Stack Developer", "weight": 9},
        {"title": "React Developer", "weight": 8},
        {"title": "Web Developer", "weight": 7}
    ],
    "React": [
        {"title": "React Developer", "weight": 10},
        {"title": "Frontend Developer", "weight": 9},
        {"title": "Full Stack Developer", "weight": 8}
    ],
    "Node.js": [
        {"title": "Backend Developer", "weight": 10},
        {"title": "Full Stack Developer", "weight": 9},
        {"title": "Node.js Developer", "weight": 10}
    ],
    "SQL": [
        {"title": "Database Developer", "weight": 10},
        {"title": "Data Analyst", "weight": 9},
        {"title": "Backend Developer", "weight": 7},
        {"title": "Data Scientist", "weight": 8}
    ],
    "Machine Learning": [
        {"title": "Machine Learning Engineer", "weight": 10},
        {"title": "AI Engineer", "weight": 10},
        {"title": "Data Scientist", "weight": 9}
    ],
    "Data Science": [
        {"title": "Data Scientist", "weight": 10},
        {"title": "Machine Learning Engineer", "weight": 9},
        {"title": "AI Engineer", "weight": 8}
    ],
    "TensorFlow": [
        {"title": "Machine Learning Engineer", "weight": 10},
        {"title": "AI Engineer", "weight": 9},
        {"title": "Deep Learning Engineer", "weight": 10}
    ],
    "Django": [
        {"title": "Python Developer", "weight": 9},
        {"title": "Backend Developer", "weight": 8},
        {"title": "Full Stack Developer", "weight": 7}
    ],
    "Flask": [
        {"title": "Python Developer", "weight": 8},
        {"title": "Backend Developer", "weight": 7},
        {"title": "API Developer", "weight": 8}
    ],
    "MongoDB": [
        {"title": "Database Developer", "weight": 8},
        {"title": "Backend Developer", "weight": 7},
        {"title": "Full Stack Developer", "weight": 6}
    ],
    "AWS": [
        {"title": "DevOps Engineer", "weight": 10},
        {"title": "Cloud Engineer", "weight": 10},
        {"title": "Backend Developer", "weight": 7}
    ],
    "Docker": [
        {"title": "DevOps Engineer", "weight": 9},
        {"title": "Cloud Engineer", "weight": 8},
        {"title": "Backend Developer", "weight": 6}
    ],
    "C++": [
        {"title": "C++ Developer", "weight": 10},
        {"title": "Software Engineer", "weight": 8},
        {"title": "Game Developer", "weight": 9}
    ]
}

# Job roles database with complete details
JOB_ROLES_DATABASE = [
    {
        "id": 1,
        "title": "Python Developer",
        "company": "TechCorp",
        "location": "Remote",
        "salary": "$80,000 - $100,000",
        "description": "Develop Python applications using Django/Flask",
        "required_skills": ["Python", "Django", "SQL"],
        "type": "full_time"
    },
    {
        "id": 2,
        "title": "Machine Learning Engineer",
        "company": "AI Solutions",
        "location": "San Francisco",
        "salary": "$120,000 - $150,000",
        "description": "Build ML models using TensorFlow/PyTorch",
        "required_skills": ["Python", "Machine Learning", "TensorFlow"],
        "type": "full_time"
    },
    {
        "id": 3,
        "title": "Data Scientist",
        "company": "DataWorks",
        "location": "New York",
        "salary": "$110,000 - $140,000",
        "description": "Analyze data and build predictive models",
        "required_skills": ["Python", "Data Science", "SQL"],
        "type": "full_time"
    },
    {
        "id": 4,
        "title": "Frontend Developer",
        "company": "WebStudio",
        "location": "Remote",
        "salary": "$70,000 - $90,000",
        "description": "Build responsive UIs with React",
        "required_skills": ["JavaScript", "React", "HTML", "CSS"],
        "type": "full_time"
    },
    {
        "id": 5,
        "title": "Backend Developer",
        "company": "ServerLogic",
        "location": "Austin",
        "salary": "$90,000 - $120,000",
        "description": "Develop scalable backend services",
        "required_skills": ["Python", "Node.js", "SQL"],
        "type": "full_time"
    },
    {
        "id": 6,
        "title": "Full Stack Developer",
        "company": "StartupHub",
        "location": "Remote",
        "salary": "$85,000 - $110,000",
        "description": "Work on both frontend and backend",
        "required_skills": ["JavaScript", "React", "Node.js", "SQL"],
        "type": "full_time"
    },
    {
        "id": 7,
        "title": "Java Developer",
        "company": "EnterpriseSoft",
        "location": "Chicago",
        "salary": "$85,000 - $105,000",
        "description": "Develop Java applications using Spring Boot",
        "required_skills": ["Java", "SQL"],
        "type": "full_time"
    },
    {
        "id": 8,
        "title": "DevOps Engineer",
        "company": "CloudTech",
        "location": "Remote",
        "salary": "$100,000 - $130,000",
        "description": "Manage CI/CD pipelines and cloud infrastructure",
        "required_skills": ["AWS", "Docker", "Python"],
        "type": "full_time"
    }
]

def calculate_match_score(resume_skills, job):
    """
    Calculate match score between resume skills and job requirements
    Using rule-based weighted scoring
    """
    if not resume_skills or not job:
        return 0
    
    job_skills = job.get("required_skills", [])
    if not job_skills:
        return 0
    
    # Convert to lowercase for case-insensitive matching
    resume_skills_lower = [s.lower() for s in resume_skills]
    job_skills_lower = [s.lower() for s in job_skills]
    
    # Calculate matches
    matches = 0
    
    for job_skill in job_skills_lower:
        # Check if skill exists in resume
        if any(job_skill in res_skill for res_skill in resume_skills_lower):
            matches += 1
        # Also check using rule-based weights (partial matches)
        else:
            for res_skill in resume_skills_lower:
                if job_skill in res_skill or res_skill in job_skill:
                    matches += 0.5
                    break
    
    # Calculate percentage
    match_percentage = (matches / len(job_skills)) * 100
    return min(round(match_percentage), 100)

def get_job_recommendations(resume_skills):
    """
    Get job recommendations based on resume skills using rule-based matching
    Returns sorted list of jobs with match scores
    """
    recommendations = []
    
    for job in JOB_ROLES_DATABASE:
        match_score = calculate_match_score(resume_skills, job)
        if match_score >= 30:  # Only show jobs with 30%+ match
            # Find matched skills
            matched = []
            for skill in job["required_skills"]:
                if any(skill.lower() in rs.lower() for rs in resume_skills):
                    matched.append(skill)
            
            recommendations.append({
                "id": job["id"],
                "title": job["title"],
                "company": job["company"],
                "location": job["location"],
                "salary": job["salary"],
                "description": job["description"],
                "type": job["type"],
                "match_score": match_score,
                "matched_skills": matched
            })
    
    # Sort by match score (highest first)
    recommendations.sort(key=lambda x: x["match_score"], reverse=True)
    return recommendations

def extract_skills_from_text(text):
    """Extract technical skills from resume text"""
    
    # Predefined skills list
    SKILLS_LIST = [
        "Python", "Java", "JavaScript", "React", "Node.js", "C++", "SQL",
        "Machine Learning", "Data Science", "TensorFlow", "PyTorch", "Django",
        "Flask", "MongoDB", "AWS", "Docker", "Kubernetes", "HTML", "CSS",
        "TypeScript", "Angular", "Vue.js", "Spring Boot", "C#", "PHP",
        "Ruby", "Swift", "Kotlin", "R", "Pandas", "NumPy", "Scikit-learn",
        "NLP", "Computer Vision", "Deep Learning", "Statistics", "Mathematics",
        "Git", "Linux", "Jenkins", "Terraform", "Ansible", "Azure", "GCP"
    ]
    
    text_lower = text.lower()
    found_skills = []
    
    for skill in SKILLS_LIST:
        if skill.lower() in text_lower:
            found_skills.append(skill)
    
    # Check for variations
    variations = {
        "js": "JavaScript",
        "reactjs": "React",
        "node": "Node.js",
        "py": "Python",
        "ml": "Machine Learning",
        "ai": "Artificial Intelligence",
        "dl": "Deep Learning",
        "cpp": "C++",
        "postgresql": "SQL",
        "mysql": "SQL"
    }
    
    for var, skill in variations.items():
        if var.lower() in text_lower and skill not in found_skills:
            found_skills.append(skill)
    
    return list(set(found_skills))  # Remove duplicates

# ==================== RESUME UPLOAD ENDPOINT ====================

@app.post("/api/resume/upload")
async def upload_resume(
    token: str = Form(...),
    file: UploadFile = File(...)
):
    """Upload resume and get job recommendations"""
    
    # Verify token
    email = verify_token(token)
    if not email:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    # For mock collections, create a mock user
    if isinstance(users_collection, MockCollection):
        user = {"_id": "mock_id", "email": email}
    else:
        user = users_collection.find_one({"email": email})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
    
    try:
        # Read file content
        content = await file.read()
        
        # Extract text based on file type
        extracted_text = ""
        if file.filename.endswith('.pdf'):
            # PDF parsing logic (use PyPDF2)
            import io
            from PyPDF2 import PdfReader
            pdf_file = io.BytesIO(content)
            pdf_reader = PdfReader(pdf_file)
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    extracted_text += page_text + "\n"
        elif file.filename.endswith('.docx'):
            # DOCX parsing logic
            import io
            import docx2txt
            extracted_text = docx2txt.process(io.BytesIO(content))
        else:
            # Plain text
            extracted_text = content.decode('utf-8', errors='ignore')
        
        # Extract skills from text
        extracted_skills = extract_skills_from_text(extracted_text)
        
        # Get job recommendations using rule-based matching
        job_recommendations = get_job_recommendations(extracted_skills)
        
        # For mock collections, just return the results
        if isinstance(users_collection, MockCollection):
            return {
                "success": True,
                "message": "Resume uploaded and analyzed successfully (Mock Mode)",
                "filename": file.filename,
                "extracted_skills": extracted_skills,
                "skills_count": len(extracted_skills),
                "job_recommendations": job_recommendations[:10],
                "total_matches": len(job_recommendations)
            }
        
        # Save resume data to database for real MongoDB
        resume_data = {
            "user_id": str(user["_id"]),
            "filename": file.filename,
            "skills": extracted_skills,
            "resume_text": extracted_text[:1000],  # Store first 1000 chars
            "uploaded_at": datetime.now(),
            "job_matches": job_recommendations[:5]  # Store top 5 matches
        }
        
        # Update or insert resume
        resumes_collection.update_one(
            {"user_id": str(user["_id"])},
            {"$set": resume_data},
            upsert=True
        )
        
        return {
            "success": True,
            "message": "Resume uploaded and analyzed successfully",
            "filename": file.filename,
            "extracted_skills": extracted_skills,
            "skills_count": len(extracted_skills),
            "job_recommendations": job_recommendations[:10],  # Return top 10 matches
            "total_matches": len(job_recommendations)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing resume: {str(e)}")

# ==================== NEW ENDPOINT FOR SKILL EXTRACTION ====================
@app.post("/api/extract-resume-skills")
async def extract_resume_skills(file: UploadFile = File(...)):
    """Extract skills from uploaded resume file"""
    try:
        content = await file.read()
        extracted_text = ""
        
        # Parse based on file type
        if file.filename.endswith('.pdf'):
            import io
            from PyPDF2 import PdfReader
            pdf_file = io.BytesIO(content)
            pdf_reader = PdfReader(pdf_file)
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    extracted_text += page_text + "\n"
        elif file.filename.endswith('.docx'):
            import io
            import docx2txt
            extracted_text = docx2txt.process(io.BytesIO(content))
        else:
            extracted_text = content.decode('utf-8', errors='ignore')
        
        # Skills database
        skills_list = [
            "Python", "Java", "JavaScript", "TypeScript", "React", "Angular", "Vue", "Node.js",
            "Django", "Flask", "Spring Boot", "Express", "SQL", "MySQL", "PostgreSQL", "MongoDB",
            "HTML", "CSS", "SASS", "Tailwind", "Bootstrap", "Git", "GitHub", "Docker", "Kubernetes",
            "AWS", "Azure", "GCP", "TensorFlow", "PyTorch", "Machine Learning", "Deep Learning",
            "Data Science", "Pandas", "NumPy", "C++", "C#", "PHP", "Ruby", "Swift", "Kotlin",
            "REST API", "GraphQL", "Firebase", "Redis", "Data Structures", "Algorithms"
        ]
        
        # Extract skills from text
        text_lower = extracted_text.lower()
        found_skills = []
        for skill in skills_list:
            if skill.lower() in text_lower:
                found_skills.append(skill)
        
        return {
            "success": True,
            "skills": found_skills,
            "skills_count": len(found_skills),
            "text_preview": extracted_text[:500] if extracted_text else "No text extracted"
        }
    except Exception as e:
        print(f"Error extracting skills: {e}")
        return {
            "success": False,
            "error": str(e),
            "skills": []
        }
# ==========================================================================

# Initialize demo data
def init_demo_data():
    try:
        # Check if demo data already exists
        if not isinstance(users_collection, MockCollection) and users_collection.count_documents({}) == 0:
            print("📊 Initializing demo data...")
            
            # Demo Job Seeker
            job_seeker = {
                "email": "jobseeker@demo.com",
                "password": get_password_hash("demo123"),
                "first_name": "Alex",
                "last_name": "Johnson",
                "user_type": "job_seeker",
                "created_at": datetime.now(),
                "profile_complete": True
            }
            users_collection.insert_one(job_seeker)
            
            # Demo Employer
            employer = {
                "email": "employer@demo.com",
                "password": get_password_hash("demo123"),
                "first_name": "Sarah",
                "last_name": "Smith",
                "user_type": "employer",
                "created_at": datetime.now(),
                "profile_complete": True
            }
            users_collection.insert_one(employer)
            
            # Get employer ID
            employer_doc = users_collection.find_one({"email": "employer@demo.com"})
            
            # Demo Jobs
            job1 = {
                "employer_id": str(employer_doc["_id"]),
                "title": "Senior AI Engineer",
                "description": "Looking for experienced AI Engineer with Python and Machine Learning skills. Must have strong background in neural networks and deep learning.",
                "job_type": "full_time",
                "experience_level": "senior",
                "location": "Remote",
                "salary_range": "$120,000 - $160,000",
                "skills_required": ["Python", "Machine Learning", "AI", "TensorFlow", "Deep Learning", "PyTorch"],
                "is_active": True,
                "created_at": datetime.now(),
                "views_count": 0,
                "applications_count": 0
            }
            
            job2 = {
                "employer_id": str(employer_doc["_id"]),
                "title": "Full Stack Developer",
                "description": "Need full stack developer with React and Node.js experience. Should be comfortable with MongoDB and Express.",
                "job_type": "full_time",
                "experience_level": "mid",
                "location": "New York, NY",
                "salary_range": "$90,000 - $120,000",
                "skills_required": ["JavaScript", "React", "Node.js", "MongoDB", "Express", "HTML", "CSS"],
                "is_active": True,
                "created_at": datetime.now(),
                "views_count": 0,
                "applications_count": 0
            }
            
            job3 = {
                "employer_id": str(employer_doc["_id"]),
                "title": "Data Scientist",
                "description": "Looking for Data Scientist with statistical analysis and Python skills. Experience with pandas and scikit-learn required.",
                "job_type": "full_time",
                "experience_level": "mid",
                "location": "San Francisco, CA",
                "salary_range": "$110,000 - $140,000",
                "skills_required": ["Python", "Statistics", "Machine Learning", "SQL", "Pandas", "scikit-learn"],
                "is_active": True,
                "created_at": datetime.now(),
                "views_count": 0,
                "applications_count": 0
            }
            
            jobs_result = jobs_collection.insert_many([job1, job2, job3])
            
            # Get job seeker ID
            job_seeker_doc = users_collection.find_one({"email": "jobseeker@demo.com"})
            
            # Demo Resume
            resume = {
                "user_id": str(job_seeker_doc["_id"]),
                "skills": ["Python", "Machine Learning", "AI", "TensorFlow", "Deep Learning", "Statistics", "Pandas", "scikit-learn", "Computer Vision"],
                "resume_text": "Experienced AI Engineer with 5+ years in Python and Machine Learning. Proficient in TensorFlow and PyTorch. Strong background in neural networks, computer vision, and data science. Developed multiple production-ready ML models.",
                "ai_score": 8.7,
                "experience": [
                    {
                        "title": "Senior AI Engineer",
                        "company": "Tech Corp",
                        "duration": "2021 - Present",
                        "description": "Leading AI initiatives, developing computer vision models for object detection and classification. Improved model accuracy by 25%."
                    },
                    {
                        "title": "Machine Learning Engineer",
                        "company": "DataStartup",
                        "duration": "2019 - 2021",
                        "description": "Developed and deployed ML models for predictive analytics. Worked with NLP and time series data."
                    },
                    {
                        "title": "Software Developer",
                        "company": "Innovate Inc",
                        "duration": "2017 - 2019",
                        "description": "Full stack development with Python and JavaScript. Built REST APIs and web applications."
                    }
                ],
                "education": [
                    {
                        "degree": "MSc in Computer Science",
                        "university": "Stanford University",
                        "year": "2019",
                        "gpa": "3.8"
                    },
                    {
                        "degree": "BSc in Computer Science",
                        "university": "UC Berkeley",
                        "year": "2017",
                        "gpa": "3.6"
                    }
                ],
                "certifications": ["Deep Learning Specialization", "AWS Certified Machine Learning"],
                "languages": ["English", "Spanish"],
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }
            
            resumes_collection.insert_one(resume)
            
            # Demo Application
            application = {
                "user_id": str(job_seeker_doc["_id"]),
                "job_posting_id": str(job1["_id"]),
                "resume_id": str(resume["_id"]),
                "cover_letter": "I am very interested in this AI Engineer position. My experience in computer vision and deep learning makes me an excellent candidate.",
                "status": "submitted",
                "match_score": 0.89,
                "applied_at": datetime.now(),
                "last_updated": datetime.now(),
                "notes": ""
            }
            
            applications_collection.insert_one(application)
            
            # Update job applications count
            jobs_collection.update_one(
                {"_id": job1["_id"]},
                {"$inc": {"applications_count": 1}}
            )
            
            print("✅ Demo data initialized successfully!")
            print(f"   👨‍💼 Job Seeker: jobseeker@demo.com / demo123")
            print(f"   👩‍💼 Employer: employer@demo.com / demo123")
        else:
            print("📊 Database already contains data, skipping demo initialization")
            
    except Exception as e:
        print(f"⚠️  Warning: Could not initialize demo data: {e}")

# Initialize data on startup
init_demo_data()

# Serve HTML files
@app.get("/", response_class=HTMLResponse)
async def serve_index():
    try:
        with open("../static/index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="""
        <!DOCTYPE html>
        <html>
        <head>
            <title>SmartJob Portal</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }
                h1 { color: #2563eb; }
                .container { max-width: 800px; margin: 0 auto; }
                .card { border: 1px solid #e5e7eb; border-radius: 8px; padding: 20px; margin: 20px 0; }
                .success { color: #059669; }
                .endpoint { background: #f3f4f6; padding: 10px; border-radius: 4px; margin: 5px 0; }
                .nav-links { margin-bottom: 30px; }
                .nav-links a { 
                    margin-right: 20px; 
                    text-decoration: none; 
                    color: #2563eb;
                    font-weight: 500;
                }
                .nav-links a:hover { text-decoration: underline; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="nav-links">
                    <a href="/">Home</a>
                    <a href="/api/docs">API Docs</a>
                    <a href="/resume.html">My Resume</a>
                    <a href="/jobs.html">Find Jobs</a>
                </div>
                
                <h1>🚀 SmartJob Portal Backend</h1>
                <div class="card">
                    <h2 class="success">✅ Server is Running!</h2>
                    <p><strong>MongoDB Atlas:</strong> Connected successfully</p>
                    <p><strong>Database:</strong> smartjob_portal</p>
                    <p><strong>API Base URL:</strong> http://localhost:8000</p>
                </div>
                
                <div class="card">
                    <h3>📋 Available Endpoints:</h3>
                    <div class="endpoint">POST /api/register - Register new user</div>
                    <div class="endpoint">POST /api/login - Login user</div>
                    <div class="endpoint">GET /api/profile - Get user profile</div>
                    <div class="endpoint">GET/POST /api/jobseeker/dashboard - Job seeker dashboard</div>
                    <div class="endpoint">GET/POST /api/employer/dashboard - Employer dashboard</div>
                    <div class="endpoint">GET /api/jobs - Get all jobs</div>
                    <div class="endpoint">POST /api/jobs - Post new job (employer only)</div>
                    <div class="endpoint">POST /api/jobs/{id}/apply - Apply for job</div>
                    <div class="endpoint">GET/POST /api/resume - Manage resume</div>
                    <div class="endpoint">POST /api/resume/upload - Upload resume for matching</div>
                    <div class="endpoint">GET /api/health - Health check</div>
                </div>
                
                <div class="card">
                    <h3>🔑 Demo Credentials:</h3>
                    <p><strong>Job Seeker:</strong> jobseeker@demo.com / demo123</p>
                    <p><strong>Employer:</strong> employer@demo.com / demo123</p>
                </div>
            </div>
        </body>
        </html>
        """)

@app.get("/{page}", response_class=HTMLResponse)
async def serve_page(page: str):
    if "." not in page:
        page = f"{page}.html"
    
    file_path = f"../static/{page}"
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content=f"<h1>Page {page} not found</h1><p>Try accessing the root endpoint (/) instead.</p>", status_code=404)

# API Endpoints
@app.post("/api/register")
async def register(
    email: str = Form(...),
    password: str = Form(...),
    first_name: str = Form(...),
    last_name: str = Form(...),
    user_type: str = Form(...)
):
    # Check if user exists
    existing_user = users_collection.find_one({"email": email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create new user
    new_user = {
        "email": email,
        "password": get_password_hash(password),
        "first_name": first_name,
        "last_name": last_name,
        "user_type": user_type,
        "created_at": datetime.now(),
        "profile_complete": False
    }
    
    result = users_collection.insert_one(new_user)
    user_id = str(result.inserted_id) if hasattr(result, 'inserted_id') else "mock_id"
    
    token = generate_token(email)
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user_id,
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "user_type": user_type
        }
    }

@app.post("/api/login")
async def login(
    email: str = Form(...),
    password: str = Form(...)
):
    user = users_collection.find_one({"email": email})
    
    # For mock collections, accept demo credentials
    if isinstance(users_collection, MockCollection):
        if email == "jobseeker@demo.com" and password == "demo123":
            token = generate_token(email)
            return {
                "access_token": token,
                "token_type": "bearer",
                "user": {
                    "id": "mock_id",
                    "email": email,
                    "first_name": "Alex",
                    "last_name": "Johnson",
                    "user_type": "job_seeker"
                }
            }
    
    if not user or not verify_password(password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = generate_token(email)
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": str(user["_id"]),
            "email": email,
            "first_name": user["first_name"],
            "last_name": user["last_name"],
            "user_type": user["user_type"]
        }
    }

# Continue with all your other endpoints (profile, dashboard, jobs, etc.)
# ... (rest of your endpoints remain the same) ...

if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print("🚀 SmartJob Portal Backend Starting...")
    print("=" * 60)
    print(f"🗄️  Database: MongoDB Atlas")
    print(f"📁 Database Name: {MONGODB_DATABASE}")
    print(f"👤 MongoDB User: {MONGODB_USERNAME}")
    print(f"📁 Static files directory: ../static")
    print(f"🌐 Open http://localhost:8000 in your browser")
    print(f"📚 API Documentation: http://localhost:8000/docs")
    print("-" * 60)
    print("🔑 Demo credentials:")
    print("   👨‍💼 Job Seeker: jobseeker@demo.com / demo123")
    print("   👩‍💼 Employer: employer@demo.com / demo123")
    print("=" * 60)
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)