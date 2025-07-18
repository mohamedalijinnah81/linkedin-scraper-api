from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from typing import Optional, List, Dict, Any
import os
import logging
from contextlib import asynccontextmanager
import asyncio
from concurrent.futures import ThreadPoolExecutor
import threading
from datetime import datetime

# LinkedIn scraper imports
from linkedin_scraper import Person, Company, Job, JobSearch, actions
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables for driver management
driver_pool = []
driver_lock = threading.Lock()
MAX_DRIVERS = 5

# Pydantic models for request/response
class PersonRequest(BaseModel):
    linkedin_url: HttpUrl
    
class CompanyRequest(BaseModel):
    linkedin_url: HttpUrl
    get_employees: bool = True
    
class JobRequest(BaseModel):
    linkedin_url: HttpUrl
    
class JobSearchRequest(BaseModel):
    query: str
    location: Optional[str] = None
    limit: Optional[int] = 10

class PersonResponse(BaseModel):
    linkedin_url: str
    name: Optional[str] = None
    about: Optional[str] = None
    experiences: List[Dict[str, Any]] = []
    educations: List[Dict[str, Any]] = []
    interests: List[Dict[str, Any]] = []
    accomplishments: List[Dict[str, Any]] = []
    company: Optional[str] = None
    job_title: Optional[str] = None
    scraped_at: datetime

class CompanyResponse(BaseModel):
    linkedin_url: str
    name: Optional[str] = None
    about_us: Optional[str] = None
    website: Optional[str] = None
    headquarters: Optional[str] = None
    founded: Optional[str] = None
    company_type: Optional[str] = None
    company_size: Optional[str] = None
    specialties: List[str] = []
    showcase_pages: List[str] = []
    affiliated_companies: List[str] = []
    employees: List[Dict[str, Any]] = []
    scraped_at: datetime

class JobResponse(BaseModel):
    linkedin_url: str
    job_title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    posted_date: Optional[str] = None
    scraped_at: datetime

def create_driver():
    """Create a new Chrome driver instance"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    
    driver = webdriver.Chrome(options=chrome_options)
    return driver

def get_driver():
    """Get a driver from the pool or create a new one"""
    with driver_lock:
        if driver_pool:
            return driver_pool.pop()
        else:
            return create_driver()

def return_driver(driver):
    """Return a driver to the pool"""
    with driver_lock:
        if len(driver_pool) < MAX_DRIVERS:
            driver_pool.append(driver)
        else:
            try:
                driver.quit()
            except:
                pass

def login_driver(driver):
    """Login to LinkedIn using environment variables"""
    try:
        email = os.getenv("LINKEDIN_EMAIL")
        password = os.getenv("LINKEDIN_PASSWORD")
        
        if not email or not password:
            raise ValueError("LinkedIn credentials not found in environment variables")
        
        actions.login(driver, email, password)
        logger.info("Successfully logged in to LinkedIn")
        return True
    except Exception as e:
        logger.error(f"Failed to login to LinkedIn: {str(e)}")
        return False

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    logger.info("Starting LinkedIn Scraper API...")
    
    # Pre-create some drivers and login
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = []
        for _ in range(3):
            future = executor.submit(create_and_login_driver)
            futures.append(future)
        
        for future in futures:
            try:
                driver = future.result(timeout=30)
                if driver:
                    return_driver(driver)
            except Exception as e:
                logger.error(f"Failed to initialize driver: {str(e)}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down LinkedIn Scraper API...")
    with driver_lock:
        for driver in driver_pool:
            try:
                driver.quit()
            except:
                pass
        driver_pool.clear()

def create_and_login_driver():
    """Create a driver and login"""
    driver = create_driver()
    if login_driver(driver):
        return driver
    else:
        driver.quit()
        return None

# Initialize FastAPI app
app = FastAPI(
    title="LinkedIn Scraper API",
    description="A comprehensive API for scraping LinkedIn profiles, companies, and jobs",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Thread pool for handling scraping tasks
executor = ThreadPoolExecutor(max_workers=10)

def scrape_person_sync(linkedin_url: str) -> PersonResponse:
    """Synchronous person scraping function"""
    driver = get_driver()
    try:
        if not login_driver(driver):
            raise Exception("Failed to login to LinkedIn")
        
        person = Person(linkedin_url, driver=driver, scrape=True)
        
        # Convert experiences to dict
        experiences = []
        if hasattr(person, 'experiences') and person.experiences:
            for exp in person.experiences:
                experiences.append({
                    'title': getattr(exp, 'position_title', ''),
                    'company': getattr(exp, 'institution_name', ''),
                    'duration': getattr(exp, 'duration', ''),
                    'location': getattr(exp, 'location', ''),
                    'description': getattr(exp, 'description', '')
                })
        
        # Convert educations to dict
        educations = []
        if hasattr(person, 'educations') and person.educations:
            for edu in person.educations:
                educations.append({
                    'institution': getattr(edu, 'institution_name', ''),
                    'degree': getattr(edu, 'degree', ''),
                    'duration': getattr(edu, 'duration', ''),
                    'description': getattr(edu, 'description', '')
                })
        
        # Convert interests to dict
        interests = []
        if hasattr(person, 'interests') and person.interests:
            for interest in person.interests:
                interests.append({
                    'name': getattr(interest, 'name', ''),
                    'followers': getattr(interest, 'followers', '')
                })
        
        # Convert accomplishments to dict
        accomplishments = []
        if hasattr(person, 'accomplishments') and person.accomplishments:
            for acc in person.accomplishments:
                accomplishments.append({
                    'category': getattr(acc, 'category', ''),
                    'title': getattr(acc, 'title', ''),
                    'description': getattr(acc, 'description', '')
                })
        
        return PersonResponse(
            linkedin_url=linkedin_url,
            name=person.name,
            about=person.about,
            experiences=experiences,
            educations=educations,
            interests=interests,
            accomplishments=accomplishments,
            company=person.company,
            job_title=person.job_title,
            scraped_at=datetime.now()
        )
    
    finally:
        return_driver(driver)

def scrape_company_sync(linkedin_url: str, get_employees: bool = True) -> CompanyResponse:
    """Synchronous company scraping function"""
    driver = get_driver()
    try:
        if not login_driver(driver):
            raise Exception("Failed to login to LinkedIn")
        
        company = Company(linkedin_url, driver=driver, scrape=True, get_employees=get_employees)
        
        # Convert employees to dict if available
        employees = []
        if hasattr(company, 'employees') and company.employees:
            for emp in company.employees:
                employees.append({
                    'name': getattr(emp, 'name', ''),
                    'title': getattr(emp, 'title', ''),
                    'linkedin_url': getattr(emp, 'linkedin_url', '')
                })
        
        return CompanyResponse(
            linkedin_url=linkedin_url,
            name=company.name,
            about_us=company.about_us,
            website=company.website,
            headquarters=company.headquarters,
            founded=company.founded,
            company_type=company.company_type,
            company_size=company.company_size,
            specialties=company.specialties if hasattr(company, 'specialties') else [],
            showcase_pages=company.showcase_pages if hasattr(company, 'showcase_pages') else [],
            affiliated_companies=company.affiliated_companies if hasattr(company, 'affiliated_companies') else [],
            employees=employees,
            scraped_at=datetime.now()
        )
    
    finally:
        return_driver(driver)

def scrape_job_sync(linkedin_url: str) -> JobResponse:
    """Synchronous job scraping function"""
    driver = get_driver()
    try:
        if not login_driver(driver):
            raise Exception("Failed to login to LinkedIn")
        
        job = Job(linkedin_url, driver=driver, scrape=True)
        
        return JobResponse(
            linkedin_url=linkedin_url,
            job_title=getattr(job, 'job_title', None),
            company=getattr(job, 'company', None),
            location=getattr(job, 'location', None),
            description=getattr(job, 'description', None),
            posted_date=getattr(job, 'posted_date', None),
            scraped_at=datetime.now()
        )
    
    finally:
        return_driver(driver)

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "LinkedIn Scraper API",
        "version": "1.0.0",
        "endpoints": {
            "person": "/scrape/person",
            "company": "/scrape/company",
            "job": "/scrape/job",
            "job_search": "/scrape/job-search",
            "health": "/health"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now()}

@app.post("/scrape/person", response_model=PersonResponse)
async def scrape_person(request: PersonRequest):
    """Scrape a LinkedIn person profile"""
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor, 
            scrape_person_sync, 
            str(request.linkedin_url)
        )
        return result
    except Exception as e:
        logger.error(f"Error scraping person: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to scrape person: {str(e)}")

@app.post("/scrape/company", response_model=CompanyResponse)
async def scrape_company(request: CompanyRequest):
    """Scrape a LinkedIn company profile"""
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor, 
            scrape_company_sync, 
            str(request.linkedin_url),
            request.get_employees
        )
        return result
    except Exception as e:
        logger.error(f"Error scraping company: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to scrape company: {str(e)}")

@app.post("/scrape/job", response_model=JobResponse)
async def scrape_job(request: JobRequest):
    """Scrape a LinkedIn job posting"""
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor, 
            scrape_job_sync, 
            str(request.linkedin_url)
        )
        return result
    except Exception as e:
        logger.error(f"Error scraping job: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to scrape job: {str(e)}")

@app.post("/scrape/job-search")
async def search_jobs(request: JobSearchRequest):
    """Search for jobs on LinkedIn"""
    try:
        # This is a placeholder - actual implementation would depend on JobSearch class
        return {
            "query": request.query,
            "location": request.location,
            "limit": request.limit,
            "message": "Job search functionality coming soon",
            "scraped_at": datetime.now()
        }
    except Exception as e:
        logger.error(f"Error searching jobs: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to search jobs: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
