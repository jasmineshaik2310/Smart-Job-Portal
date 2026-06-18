import re
from typing import List, Dict
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
import json

# Download NLTK data
try:
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('punkt')
    nltk.download('stopwords')

class JobMatcher:
    def __init__(self):
        self.stop_words = set(stopwords.words('english'))
        self.skill_keywords = self.load_skill_keywords()
    
    def load_skill_keywords(self):
        # Common tech skills dictionary
        return {
            "python": ["python", "django", "flask"],
            "javascript": ["javascript", "react", "vue", "angular", "node", "typescript"],
            "java": ["java", "spring", "hibernate"],
            "ai_ml": ["machine learning", "ai", "artificial intelligence", "deep learning", "tensorflow", "pytorch"],
            "data_science": ["data science", "data analysis", "pandas", "numpy"],
            "cloud": ["aws", "azure", "gcp", "cloud", "docker", "kubernetes"],
            "databases": ["sql", "mysql", "postgresql", "mongodb", "redis"],
            "devops": ["devops", "ci/cd", "jenkins", "git", "github", "gitlab"],
        }
    
    def extract_skills(self, text: str) -> List[str]:
        """Extract skills from text using keyword matching"""
        text = text.lower()
        found_skills = []
        
        for skill_category, keywords in self.skill_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    found_skills.append(skill_category)
                    break
        
        return list(set(found_skills))
    
    def calculate_match_score(self, job_description: str, resume_text: str) -> float:
        """Calculate match score between job description and resume"""
        # Text preprocessing
        job_desc_clean = self.preprocess_text(job_description)
        resume_clean = self.preprocess_text(resume_text)
        
        # TF-IDF Vectorization
        vectorizer = TfidfVectorizer()
        tfidf_matrix = vectorizer.fit_transform([job_desc_clean, resume_clean])
        
        # Cosine similarity
        cosine_sim = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
        
        # Extract skills and calculate skill match
        job_skills = self.extract_skills(job_description)
        resume_skills = self.extract_skills(resume_text)
        
        if not job_skills:
            skill_score = 0.5  # Default if no skills found
        else:
            matched_skills = set(job_skills) & set(resume_skills)
            skill_score = len(matched_skills) / len(job_skills)
        
        # Combined score (70% text similarity, 30% skill match)
        final_score = (cosine_sim * 0.7) + (skill_score * 0.3)
        
        return min(1.0, max(0.0, final_score))
    
    def preprocess_text(self, text: str) -> str:
        """Clean and preprocess text"""
        # Convert to lowercase
        text = text.lower()
        
        # Remove special characters and digits
        text = re.sub(r'[^a-zA-Z\s]', '', text)
        
        # Tokenize and remove stopwords
        tokens = word_tokenize(text)
        filtered_tokens = [word for word in tokens if word not in self.stop_words]
        
        return ' '.join(filtered_tokens)
    
    def get_match_breakdown(self, job_description: str, resume_text: str) -> Dict:
        """Get detailed breakdown of the match"""
        job_skills = self.extract_skills(job_description)
        resume_skills = self.extract_skills(resume_text)
        
        matched_skills = list(set(job_skills) & set(resume_skills))
        missing_skills = list(set(job_skills) - set(resume_skills))
        
        return {
            "matched_skills": matched_skills,
            "missing_skills": missing_skills,
            "resume_skills": resume_skills,
            "job_skills": job_skills
        }

# Global instance
job_matcher = JobMatcher()