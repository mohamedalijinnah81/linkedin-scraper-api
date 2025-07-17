from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from typing import List, Optional, Dict, Any
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
import os
import asyncio
from contextlib import asynccontextmanager
import logging
from datetime import datetime
import json
import time
import random

# Import the linkedin_scraper library
from linkedin_scraper import Person, Company, Job, JobSearch, actions

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global driver pool
driver_pool = []
MAX_DRIVERS = int(os.getenv("MAX_DRIVERS", "2"))  # Reduced for cloud environment

def create_driver():
    """Create a new Chrome driver with cloud-optimized settings"""
    chrome_options = Options()
    
    # Essential headless options
    chrome_options.add_argument('--headless=new')  # Use new headless mode
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-software-rasterizer')
    
    # Memory and performance optimization
    chrome_options.add_argument('--memory-pressure-off')
    chrome_options.add_argument('--max_old_space_size=4096')
    chrome_options.add_argument('--disable-background-timer-throttling')
    chrome_options.add_argument('--disable-backgrounding-occluded-windows')
    chrome_options.add_argument('--disable-renderer-backgrounding')
    
    # Network and security options
    chrome_options.add_argument('--disable-web-security')
    chrome_options.add_argument('--disable-features=TranslateUI')
    chrome_options.add_argument('--disable-ipc-flooding-protection')
    chrome_options.add_argument('--disable-background-networking')
    chrome_options.add_argument('--disable-sync')
    chrome_options.add_argument('--disable-default-apps')
    chrome_options.add_argument('--disable-extensions')
    
    # Anti-detection measures
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--start-maximized')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    # Disable logging and debugging
    chrome_options.add_argument('--log-level=3')
    chrome_options.add_argument('--silent')
    chrome_options.add_argument('--disable-logging')
    chrome_options.add_argument('--disable-dev-tools')
    
    # Cloud environment specific
    chrome_options.add_argument('--no-first-run')
    chrome_options.add_argument('--no-default-browser-check')
    chrome_options.add_argument('--disable-crash-reporter')
    chrome_options.add_argument('--disable-in-process-stack-traces')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--single-process')  # Important for container environments
    
    # Remove remote debugging (this might be causing the localhost connection issue)
    chrome_options.add_argument('--remote-debugging-port=0')
    
    # Set timeouts
    chrome_options.add_argument('--timeout=60000')
    chrome_options.add_argument('--page-load-strategy=eager')
    
    # Additional stability options
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
    
    # Prefs to disable images and other resources for faster loading
    prefs = {
        'profile.default_content_setting_values.notifications': 2,
        'profile.default_content_settings.popups': 0,
        'profile.managed_default_content_settings.images': 2,
        'profile.default_content_setting_values.media_stream': 2,
    }
    chrome_options.add_experimental_option('prefs', prefs)
    
    try:
        # Create driver with extended timeout
        driver = webdriver.Chrome(options=chrome_options)
        
        # Set timeouts
        driver.set_page_load_timeout(60)
        driver.implicitly_wait(10)
        
        # Test basic functionality
        driver.get("https://www.google.com")
        
        logger.info("Chrome driver created successfully")
        return driver
        
    except Exception as e:
        logger.error(f"Failed to create driver: {e}")
        raise

def initialize_driver_pool():
    """Initialize the driver pool with retry logic"""
    global driver_pool
    successful_drivers = 0
    max_retries = 3
    
    for i in range(MAX_DRIVERS):
        for retry in range(max_retries):
            try:
                driver = create_driver()
                driver_pool.append(driver)
                successful_drivers += 1
                logger.info(f"Successfully created driver {i+1}/{MAX_DRIVERS}")
                break
            except Exception as e:
                logger.error(f"Failed to create driver {i+1}, attempt {retry+1}/{max_retries}: {e}")
                if retry == max_retries - 1:
                    logger.error(f"Failed to create driver {i+1} after {max_retries} attempts")
                time.sleep(2)  # Wait before retry
    
    logger.info(f"Driver pool initialized with {successful_drivers}/{MAX_DRIVERS} drivers")

def get_driver():
    """Get an available driver from the pool"""
    if driver_pool:
        return driver_pool.pop()
    else:
        logger.warning("No drivers available in pool, creating new one")
        return create_driver()

def return_driver(driver):
    """Return driver to the pool"""
    if len(driver_pool) < MAX_DRIVERS:
        try:
            # Test if driver is still functional
            driver.get("https://www.google.com")
            driver_pool.append(driver)
            logger.info("Driver returned to pool")
        except:
            logger.warning("Driver not functional, closing it")
            try:
                driver.quit()
            except:
                pass
    else:
        try:
            driver.quit()
        except:
            pass

def enhanced_login(driver, email, password):
    """Enhanced login function with better error handling"""
    try:
        logger.info("Starting LinkedIn login process")
        
        # Navigate to LinkedIn login page
        driver.get("https://www.linkedin.com/login")
        
        # Wait for page to load
        wait = WebDriverWait(driver, 20)
        
        # Wait for email field and enter email
        email_field = wait.until(EC.presence_of_element_located((By.ID, "username")))
        email_field.clear()
        email_field.send_keys(email)
        
        # Enter password
        password_field = driver.find_element(By.ID, "password")
        password_field.clear()
        password_field.send_keys(password)
        
        # Click login button
        login_button = driver.find_element(By.XPATH, "//button[@type='submit']")
        login_button.click()
        
        # Wait for login to complete
        time.sleep(3)
        
        # Check if login was successful
        current_url = driver.current_url
        if "challenge" in current_url or "checkpoint" in current_url:
            raise Exception("LinkedIn security challenge encountered")
        elif "login" in current_url:
            raise Exception("Login failed - credentials may be incorrect")
        
        logger.info("LinkedIn login successful")
        return True
        
    except TimeoutException:
        logger.error("Login timeout - page elements not found")
        raise Exception("Login timeout")
    except Exception as e:
        logger.error(f"Login failed: {str(e)}")
        raise Exception(f"Login failed: {str(e)}")

def login_if_needed(driver, email=None, password=None):
    """Login to LinkedIn if credentials are provided"""
    if email and password:
        try:
            # Use enhanced login instead of actions.login
            enhanced_login(driver, email, password)
            logger.info("Successfully logged in to LinkedIn")
        except Exception as e:
            logger.error(f"Failed to login: {e}")
            raise HTTPException(status_code=401, detail=f"Failed to login to LinkedIn: {str(e)}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up LinkedIn Scraper API...")
    try:
        initialize_driver_pool()
        logger.info("Driver pool initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize driver pool: {e}")
    
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

# Pydantic models (keep existing models)
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

# Response models (keep existing models)
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
        "active_drivers": len(driver_pool),
        "max_drivers": MAX_DRIVERS
    }

@app.post("/person", response_model=PersonResponse)
async def scrape_person(request: PersonRequest):
    """Scrape a LinkedIn person profile"""
    driver = None
    try:
        driver = get_driver()
        
        # Login if credentials provided
        login_if_needed(driver, request.login_email, request.login_password)
        
        # Add random delay to avoid detection
        time.sleep(random.uniform(2, 5))
        
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
        
    except HTTPException:
        raise
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
        
        # Add random delay
        time.sleep(random.uniform(2, 5))
        
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
        
    except HTTPException:
        raise
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
        
        # Add random delay
        time.sleep(random.uniform(2, 5))
        
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
        
    except HTTPException:
        raise
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
        
        # Add random delay
        time.sleep(random.uniform(2, 5))
        
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
        
    except HTTPException:
        raise
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
                # Add random delay between requests
                time.sleep(random.uniform(3, 7))
                
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
                logger.error(f"Error scraping URL {url}: {e}")
                results.append({
                    "url": str(url),
                    "success": False,
                    "error": str(e)
                })
                
    except HTTPException:
        raise
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
