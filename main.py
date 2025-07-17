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
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global driver pool
driver_pool = []
MAX_DRIVERS = int(os.getenv("MAX_DRIVERS", "2"))  # Reduced for cloud environment

def create_driver():
    """Create a new Chrome driver with cloud-optimized settings"""
    chrome_options = Options()
    
    # Essential headless options - use old headless mode for better stability
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-software-rasterizer')
    
    # Stability and crash prevention
    chrome_options.add_argument('--disable-crash-reporter')
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_argument('--disable-in-process-stack-traces')
    chrome_options.add_argument('--disable-logging')
    chrome_options.add_argument('--disable-dev-tools')
    chrome_options.add_argument('--log-level=3')
    chrome_options.add_argument('--silent')
    
    # Memory management - critical for preventing crashes
    chrome_options.add_argument('--max_old_space_size=2048')
    chrome_options.add_argument('--memory-pressure-off')
    chrome_options.add_argument('--disable-background-timer-throttling')
    chrome_options.add_argument('--disable-backgrounding-occluded-windows')
    chrome_options.add_argument('--disable-renderer-backgrounding')
    chrome_options.add_argument('--disable-background-networking')
    
    # Window and display settings
    chrome_options.add_argument('--window-size=1366,768')  # Smaller window size
    chrome_options.add_argument('--disable-web-security')
    chrome_options.add_argument('--disable-features=TranslateUI,BlinkGenPropertyTrees')
    chrome_options.add_argument('--disable-ipc-flooding-protection')
    
    # User agent and anti-detection
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    # Additional stability options
    chrome_options.add_argument('--no-first-run')
    chrome_options.add_argument('--no-default-browser-check')
    chrome_options.add_argument('--disable-default-apps')
    chrome_options.add_argument('--disable-sync')
    chrome_options.add_argument('--disable-plugins')
    chrome_options.add_argument('--disable-plugins-discovery')
    chrome_options.add_argument('--disable-preconnect')
    
    # Process management - avoid single process to prevent crashes
    chrome_options.add_argument('--disable-zygote')
    chrome_options.add_argument('--no-zygote')
    
    # Remove problematic options
    chrome_options.add_argument('--remote-debugging-port=0')
    chrome_options.add_argument('--disable-remote-debugging')
    
    # Service and automation options
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging', 'enable-automation'])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # Prefs for resource optimization
    prefs = {
        'profile.default_content_setting_values.notifications': 2,
        'profile.default_content_settings.popups': 0,
        'profile.managed_default_content_settings.images': 2,
        'profile.default_content_setting_values.media_stream': 2,
        'profile.managed_default_content_settings.javascript': 1,
        'profile.managed_default_content_settings.plugins': 2,
        'profile.managed_default_content_settings.geolocation': 2,
    }
    chrome_options.add_experimental_option('prefs', prefs)
    
    # Add service args for better stability
    service_args = [
        '--verbose',
        '--log-path=/tmp/chromedriver.log',
        '--enable-chrome-logs'
    ]
    
    # Explicitly set Chrome binary location for cloud environments
    chrome_bin = os.getenv("CHROME_BIN", "/usr/bin/google-chrome")
    chrome_options.binary_location = chrome_bin

    try:
        # Use webdriver-manager to get the correct ChromeDriver
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Set conservative timeouts
        driver.set_page_load_timeout(30)
        driver.implicitly_wait(5)
        
        # Test basic functionality with retry
        max_retries = 3
        for attempt in range(max_retries):
            try:
                driver.get("https://www.google.com")
                logger.info(f"Chrome driver created and tested successfully on attempt {attempt + 1}")
                return driver
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                logger.warning(f"Driver test failed on attempt {attempt + 1}: {e}")
                time.sleep(2)
        
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
    """Return driver to the pool with health check"""
    if not driver:
        return
        
    if len(driver_pool) < MAX_DRIVERS:
        try:
            # Test if driver is still functional
            driver.get("https://www.google.com")
            WebDriverWait(driver, 5).until(EC.title_contains("Google"))
            driver_pool.append(driver)
            logger.info("Driver returned to pool successfully")
        except Exception as e:
            logger.warning(f"Driver not functional, closing it: {e}")
            try:
                driver.quit()
            except:
                pass
    else:
        try:
            driver.quit()
            logger.info("Driver closed (pool full)")
        except:
            pass

def enhanced_login(driver, email, password):
    """Enhanced login function with better error handling and stability"""
    max_retries = 2
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Starting LinkedIn login process (attempt {attempt + 1}/{max_retries})")
            
            # Check if driver is still valid
            try:
                driver.current_url
            except Exception:
                raise Exception("Driver session is invalid")
            
            # Navigate to LinkedIn login page with error handling
            try:
                driver.get("https://www.linkedin.com/login")
                time.sleep(2)  # Let page settle
            except Exception as e:
                logger.error(f"Failed to navigate to login page: {e}")
                if attempt == max_retries - 1:
                    raise Exception(f"Failed to navigate to login page: {e}")
                continue
            
            # Wait for page to load completely
            wait = WebDriverWait(driver, 15)
            
            try:
                # Wait for email field and enter email
                email_field = wait.until(EC.element_to_be_clickable((By.ID, "username")))
                email_field.clear()
                time.sleep(0.5)
                email_field.send_keys(email)
                
                # Wait for password field and enter password
                password_field = wait.until(EC.element_to_be_clickable((By.ID, "password")))
                password_field.clear()
                time.sleep(0.5)
                password_field.send_keys(password)
                
                # Wait for login button and click
                login_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']")))
                time.sleep(1)
                login_button.click()
                
                # Wait for login to complete
                time.sleep(5)
                
                # Check if we're still on the login page
                current_url = driver.current_url
                logger.info(f"Current URL after login: {current_url}")
                
                if "challenge" in current_url or "checkpoint" in current_url:
                    raise Exception("LinkedIn security challenge encountered")
                elif "login" in current_url:
                    # Check for error messages
                    try:
                        error_elements = driver.find_elements(By.CSS_SELECTOR, ".alert--error, .form__label--error")
                        if error_elements:
                            error_text = error_elements[0].text
                            raise Exception(f"Login failed with error: {error_text}")
                    except:
                        pass
                    raise Exception("Login failed - credentials may be incorrect or session expired")
                
                # Verify we're logged in by checking for common post-login elements
                try:
                    # Look for LinkedIn navigation or user profile elements
                    wait.until(EC.any_of(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "nav.global-nav")),
                        EC.presence_of_element_located((By.CSS_SELECTOR, "[data-test-id='nav-menu']")),
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".global-nav__primary-link"))
                    ))
                    logger.info("LinkedIn login successful - found navigation elements")
                    return True
                except TimeoutException:
                    logger.warning("Login may have succeeded but navigation elements not found")
                    # Continue anyway as the URL check passed
                    return True
                    
            except TimeoutException as e:
                logger.error(f"Login timeout on attempt {attempt + 1}: {e}")
                if attempt == max_retries - 1:
                    raise Exception("Login timeout - page elements not found")
                continue
                
            except Exception as e:
                logger.error(f"Login error on attempt {attempt + 1}: {e}")
                if attempt == max_retries - 1:
                    raise Exception(f"Login failed: {str(e)}")
                continue
                
        except Exception as e:
            if attempt == max_retries - 1:
                logger.error(f"All login attempts failed: {e}")
                raise Exception(f"Login failed after {max_retries} attempts: {str(e)}")
            else:
                logger.warning(f"Login attempt {attempt + 1} failed, retrying: {e}")
                time.sleep(3)  # Wait before retry
                continue

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
        logger.info(f"Starting person scraping for: {request.linkedin_url}")
        driver = get_driver()
        
        # Login if credentials provided
        if request.login_email and request.login_password:
            login_if_needed(driver, request.login_email, request.login_password)
        
        # Add random delay to avoid detection
        time.sleep(random.uniform(2, 4))
        
        # Verify driver is still working before scraping
        try:
            driver.current_url
        except Exception:
            logger.error("Driver session invalid, creating new one")
            return_driver(driver)
            driver = get_driver()
            if request.login_email and request.login_password:
                login_if_needed(driver, request.login_email, request.login_password)
        
        # Create person object and scrape
        try:
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
            
            logger.info(f"Successfully scraped person: {person.name}")
            
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
            logger.error(f"Error during person scraping: {e}")
            # Try to recover by creating a new driver
            return_driver(driver)
            driver = None
            raise e
        
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
