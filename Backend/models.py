from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    first_name = Column(String)
    last_name = Column(String)
    user_type = Column(String)  # "job_seeker" or "employer"
    phone = Column(String)
    location = Column(String)
    job_title = Column(String)
    profile_picture = Column(String)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    resumes = relationship("Resume", back_populates="user")
    job_postings = relationship("JobPosting", back_populates="employer")
    applications = relationship("Application", back_populates="user")

class Resume(Base):
    __tablename__ = "resumes"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    file_path = Column(String)
    resume_text = Column(Text)
    skills = Column(JSON)  # List of skills
    experience = Column(JSON)  # List of experiences
    education = Column(JSON)  # List of education
    ai_score = Column(Float, default=0.0)
    parsed_data = Column(JSON)  # Parsed resume data
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="resumes")

class JobPosting(Base):
    __tablename__ = "job_postings"
    
    id = Column(Integer, primary_key=True, index=True)
    employer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    requirements = Column(Text)
    job_type = Column(String)  # "full_time", "part_time", "contract", "remote"
    experience_level = Column(String)  # "entry", "mid", "senior", "lead"
    location = Column(String)
    salary_range = Column(String)
    skills_required = Column(JSON)  # List of required skills
    is_active = Column(Boolean, default=True)
    views_count = Column(Integer, default=0)
    applications_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    employer = relationship("User", back_populates="job_postings")
    applications = relationship("Application", back_populates="job_posting")

class Application(Base):
    __tablename__ = "applications"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    job_posting_id = Column(Integer, ForeignKey("job_postings.id"), nullable=False)
    resume_id = Column(Integer, ForeignKey("resumes.id"))
    cover_letter = Column(Text)
    status = Column(String, default="submitted")  # submitted, reviewed, interviewed, rejected, hired
    match_score = Column(Float)
    notes = Column(Text)
    applied_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="applications")
    job_posting = relationship("JobPosting", back_populates="applications")

class AIMatch(Base):
    __tablename__ = "ai_matches"
    
    id = Column(Integer, primary_key=True, index=True)
    job_posting_id = Column(Integer, ForeignKey("job_postings.id"))
    resume_id = Column(Integer, ForeignKey("resumes.id"))
    match_score = Column(Float, nullable=False)
    matched_skills = Column(JSON)
    missing_skills = Column(JSON)
    match_reason = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    job_posting = relationship("JobPosting")
    resume = relationship("Resume")

class Skill(Base):
    __tablename__ = "skills"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    category = Column(String)  # "programming", "soft_skill", "language", etc.
    popularity = Column(Integer, default=0)