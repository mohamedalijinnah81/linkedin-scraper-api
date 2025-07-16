from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from typing import List, Optional, Dict, Any
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import os
import asyncio
from contextlib import asynccontextmanager
import logging
from datetime import datetime
import json

# Import the linkedin_scraper library
from linkedin_scraper import Person, Company, Job, JobSearch, actions

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global driver pool
driver_pool = []
MAX_DRIVERS = 3

def create_driver():
    """Create a new Chrome driver with optimized settings"""
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        return driver
    except Exception as e:
        logger.error(f"Failed to create driver: {e}")
        raise

def initialize_driver_pool():
    """Initialize the driver pool"""
    global driver_pool
    for _ in range(MAX_DRIVERS):
        try:
            driver = create_driver()
            driver_pool.append(driver)
        except Exception as e:
            logger.error(f"Failed to create driver for pool: {e}")

def get_driver():
    """Get an available driver from the pool"""
    if driver_pool:
        return driver_pool.pop()
    else:
        return create_driver()

def return_driver(driver):
    """Return driver to the pool"""
    if len(driver_pool) < MAX_DRIVERS:
        driver_pool.append(driver)
    else:
        try:
            driver.quit()
        except:
            pass

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up LinkedIn Scraper API...")
    initialize_driver_pool()
    yield
    # Shutdown
    logger.info("Shutting down LinkedIn Scraper API...")
    for driver in driver_pool:
        try:
            driver.quit()
        except:
            pass

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

# Pydantic models
class PersonRequest(BaseModel):
    linkedin_url: HttpUrl
    login_email: Optional[str] = None
    login_password: Optional[str] = None

class CompanyRequest(BaseModel):
    linkedin_url: HttpUrl
    get_employees: bool = False
    login_email: Optional[str] = None
    login_password: Optional[str] = None

class JobRequest(BaseModel):
    linkedin_url: HttpUrl
    login_email: str
    login_password: str

class JobSearchRequest(BaseModel):
    query: str
    login_email: str
    login_password: str
    max_results: int = 10

class LoginRequest(BaseModel):
    email: str
    password: str

# Response models
class PersonResponse(BaseModel):
    name: Optional[str]
    about: Optional[str]
    company: Optional[str]
    job_title: Optional[str]
    linkedin_url: Optional[str]
    experiences: List[Dict[str, Any]]
    educations: List[Dict[str, Any]]
    interests: List[Dict[str, Any]]
    accomplishments: List[Dict[str, Any]]
    scraped_at: datetime

class CompanyResponse(BaseModel):
    name: Optional[str]
    about_us: Optional[str]
    website: Optional[str]
    headquarters: Optional[str]
    founded: Optional[str]
    company_type: Optional[str]
    company_size: Optional[str]
    specialties: List[str]
    linkedin_url: Optional[str]
    employees: Optional[List[Dict[str, Any]]]
    scraped_at: datetime

class JobResponse(BaseModel):
    title: Optional[str]
    company: Optional[str]
    location: Optional[str]
    description: Optional[str]
    linkedin_url: Optional[str]
    scraped_at: datetime

# Utility functions
def serialize_object(obj):
    """Convert object attributes to dictionary"""
    if hasattr(obj, '__dict__'):
        return {key: value for key, value in obj.__dict__.items() if not key.startswith('_')}
    return str(obj)

def login_if_needed(driver, email=None, password=None):
    """Login to LinkedIn if credentials are provided"""
    if email and password:
        try:
            actions.login(driver, email, password)
            logger.info("Successfully logged in to LinkedIn")
        except Exception as e:
            logger.error(f"Failed to login: {e}")
            raise HTTPException(status_code=401, detail="Failed to login to LinkedIn")

# API Endpoints
@app.get("/")
async def root():
    return {
        "message": "LinkedIn Scraper API",
        "version": "1.0.0",
        "endpoints": {
            "person": "/person",
            "company": "/company",
            "job": "/job",
            "job_search": "/job-search",
            "health": "/health"
        }
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now(),
        "active_drivers": len(driver_pool)
    }

@app.post("/person", response_model=PersonResponse)
async def scrape_person(request: PersonRequest):
    """Scrape a LinkedIn person profile"""
    driver = None
    try:
        driver = get_driver()
        
        # Login if credentials provided
        login_if_needed(driver, request.login_email, request.login_password)
        
        # Create person object and scrape
        person = Person(
            linkedin_url=str(request.linkedin_url),
            driver=driver,
            scrape=True
        )
        
        # Convert experiences, educations, interests, accomplishments to dictionaries
        experiences = [serialize_object(exp) for exp in (person.experiences or [])]
        educations = [serialize_object(edu) for edu in (person.educations or [])]
        interests = [serialize_object(interest) for interest in (person.interests or [])]
        accomplishments = [serialize_object(acc) for acc in (person.accomplishments or [])]
        
        return PersonResponse(
            name=person.name,
            about=person.about,
            company=person.company,
            job_title=person.job_title,
            linkedin_url=person.linkedin_url,
            experiences=experiences,
            educations=educations,
            interests=interests,
            accomplishments=accomplishments,
            scraped_at=datetime.now()
        )
        
    except Exception as e:
        logger.error(f"Error scraping person: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to scrape person profile: {str(e)}")
    finally:
        if driver:
            return_driver(driver)

@app.post("/company", response_model=CompanyResponse)
async def scrape_company(request: CompanyRequest):
    """Scrape a LinkedIn company profile"""
    driver = None
    try:
        driver = get_driver()
        
        # Login if credentials provided
        login_if_needed(driver, request.login_email, request.login_password)
        
        # Create company object and scrape
        company = Company(
            linkedin_url=str(request.linkedin_url),
            driver=driver,
            scrape=True,
            get_employees=request.get_employees
        )
        
        # Serialize employees if available
        employees = []
        if hasattr(company, 'employees') and company.employees:
            employees = [serialize_object(emp) for emp in company.employees]
        
        return CompanyResponse(
            name=company.name,
            about_us=company.about_us,
            website=company.website,
            headquarters=company.headquarters,
            founded=company.founded,
            company_type=company.company_type,
            company_size=company.company_size,
            specialties=company.specialties or [],
            linkedin_url=company.linkedin_url,
            employees=employees if request.get_employees else None,
            scraped_at=datetime.now()
        )
        
    except Exception as e:
        logger.error(f"Error scraping company: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to scrape company profile: {str(e)}")
    finally:
        if driver:
            return_driver(driver)

@app.post("/job", response_model=JobResponse)
async def scrape_job(request: JobRequest):
    """Scrape a specific LinkedIn job posting"""
    driver = None
    try:
        driver = get_driver()
        
        # Login (required for job scraping)
        login_if_needed(driver, request.login_email, request.login_password)
        
        # Create job object and scrape
        job = Job(
            linkedin_url=str(request.linkedin_url),
            driver=driver,
            close_on_complete=False
        )
        
        return JobResponse(
            title=getattr(job, 'title', None),
            company=getattr(job, 'company', None),
            location=getattr(job, 'location', None),
            description=getattr(job, 'description', None),
            linkedin_url=getattr(job, 'linkedin_url', None),
            scraped_at=datetime.now()
        )
        
    except Exception as e:
        logger.error(f"Error scraping job: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to scrape job posting: {str(e)}")
    finally:
        if driver:
            return_driver(driver)

@app.post("/job-search")
async def search_jobs(request: JobSearchRequest):
    """Search for jobs on LinkedIn"""
    driver = None
    try:
        driver = get_driver()
        
        # Login (required for job search)
        login_if_needed(driver, request.login_email, request.login_password)
        
        # Create job search object
        job_search = JobSearch(
            driver=driver,
            close_on_complete=False,
            scrape=False
        )
        
        # Search for jobs
        job_listings = job_search.search(request.query)
        
        # Limit results
        job_listings = job_listings[:request.max_results]
        
        # Serialize job listings
        jobs = []
        for job in job_listings:
            jobs.append({
                "title": getattr(job, 'title', None),
                "company": getattr(job, 'company', None),
                "location": getattr(job, 'location', None),
                "description": getattr(job, 'description', None),
                "linkedin_url": getattr(job, 'linkedin_url', None),
            })
        
        return {
            "query": request.query,
            "total_results": len(jobs),
            "jobs": jobs,
            "scraped_at": datetime.now()
        }
        
    except Exception as e:
        logger.error(f"Error searching jobs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to search jobs: {str(e)}")
    finally:
        if driver:
            return_driver(driver)

@app.post("/batch-persons")
async def scrape_multiple_persons(urls: List[HttpUrl], login_email: Optional[str] = None, login_password: Optional[str] = None):
    """Scrape multiple person profiles in batch"""
    results = []
    driver = None
    
    try:
        driver = get_driver()
        
        # Login if credentials provided
        login_if_needed(driver, login_email, login_password)
        
        for url in urls:
            try:
                person = Person(
                    linkedin_url=str(url),
                    driver=driver,
                    scrape=True
                )
                
                experiences = [serialize_object(exp) for exp in (person.experiences or [])]
                educations = [serialize_object(edu) for edu in (person.educations or [])]
                interests = [serialize_object(interest) for interest in (person.interests or [])]
                accomplishments = [serialize_object(acc) for acc in (person.accomplishments or [])]
                
                results.append({
                    "url": str(url),
                    "success": True,
                    "data": {
                        "name": person.name,
                        "about": person.about,
                        "company": person.company,
                        "job_title": person.job_title,
                        "linkedin_url": person.linkedin_url,
                        "experiences": experiences,
                        "educations": educations,
                        "interests": interests,
                        "accomplishments": accomplishments,
                    }
                })
                
            except Exception as e:
                results.append({
                    "url": str(url),
                    "success": False,
                    "error": str(e)
                })
                
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch scraping failed: {str(e)}")
    finally:
        if driver:
            return_driver(driver)
    
    return {
        "total_processed": len(results),
        "successful": len([r for r in results if r["success"]]),
        "failed": len([r for r in results if not r["success"]]),
        "results": results,
        "scraped_at": datetime.now()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
