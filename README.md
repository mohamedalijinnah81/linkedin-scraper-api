# LinkedIn Scraper API

A comprehensive REST API for scraping LinkedIn profiles, companies, and job postings using the `linkedin-scraper` library. This API provides endpoints for extracting structured data from LinkedIn with support for batch processing and automated login.

## Features

- **Person Profile Scraping**: Extract detailed information from LinkedIn profiles including experience, education, skills, and accomplishments
- **Company Profile Scraping**: Get comprehensive company data including about section, employees, and company details
- **Job Scraping**: Extract job posting details and requirements
- **Job Search**: Search for jobs with specific queries and get structured results
- **Batch Processing**: Process multiple profiles simultaneously
- **Driver Pool Management**: Efficient resource management with connection pooling
- **Health Monitoring**: Built-in health checks and monitoring endpoints
- **CORS Support**: Cross-origin resource sharing for web applications
- **Comprehensive Error Handling**: Detailed error responses and logging

## Quick Start

### Prerequisites

- Python 3.11+
- Chrome/Chromium browser
- ChromeDriver

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd linkedin-scraper-api
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. Run the application:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

## Docker Deployment

### Build and run with Docker:

```bash
docker build -t linkedin-scraper-api .
docker run -p 8000:8000 linkedin-scraper-api
```

### Using Docker Compose:

```yaml
version: '3.8'
services:
  linkedin-scraper-api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - CHROMEDRIVER=/usr/local/bin/chromedriver
      - MAX_DRIVERS=3
    volumes:
      - ./data:/app/data
```

## Render Deployment

This API is configured for easy deployment on Render.com:

1. Connect your GitHub repository to Render
2. Use the provided `render.yaml` configuration
3. Set environment variables in Render dashboard
4. Deploy!

The `render.yaml` file includes:
- Automatic dependency installation
- Chrome and ChromeDriver setup
- Health check configuration
- Environment variable management

## API Endpoints

### Health Check

```http
GET /health
```

Returns API health status and active driver count.

### Person Profile Scraping

```http
POST /person
Content-Type: application/json

{
  "linkedin_url": "https://www.linkedin.com/in/username",
  "login_email": "your-email@example.com",
  "login_password": "your-password"
}
```

**Response:**
```json
{
  "name": "John Doe",
  "about": "Software Engineer with 5+ years experience...",
  "company": "Tech Corp",
  "job_title": "Senior Software Engineer",
  "linkedin_url": "https://www.linkedin.com/in/username",
  "experiences": [...],
  "educations": [...],
  "interests": [...],
  "accomplishments": [...],
  "scraped_at": "2024-01-15T10:30:00Z"
}
```

### Company Profile Scraping

```http
POST /company
Content-Type: application/json

{
  "linkedin_url": "https://www.linkedin.com/company/company-name",
  "get_employees": true,
  "login_email": "your-email@example.com",
  "login_password": "your-password"
}
```

**Response:**
```json
{
  "name": "Tech Corp",
  "about_us": "Leading technology company...",
  "website": "https://techcorp.com",
  "headquarters": "San Francisco, CA",
  "founded": "2010",
  "company_type": "Public Company",
  "company_size": "10,001+ employees",
  "specialties": ["Software Development", "AI", "Cloud Computing"],
  "linkedin_url": "https://www.linkedin.com/company/company-name",
  "employees": [...],
  "scraped_at": "2024-01-15T10:30:00Z"
}
```

### Job Scraping

```http
POST /job
Content-Type: application/json

{
  "linkedin_url": "https://www.linkedin.com/jobs/view/job-id",
  "login_email": "your-email@example.com",
  "login_password": "your-password"
}
```

### Job Search

```http
POST /job-search
Content-Type: application/json

{
  "query": "Software Engineer",
  "login_email": "your-email@example.com",
  "login_password": "your-password",
  "max_results": 10
}
```

### Batch Person Scraping

```http
POST /batch-persons
Content-Type: application/json

{
  "urls": [
    "https://www.linkedin.com/in/person1",
    "https://www.linkedin.com/in/person2"
  ],
  "login_email": "your-email@example.com",
  "login_password": "your-password"
}
```

## Authentication

LinkedIn credentials can be provided in two ways:

1. **Per-request**: Include `login_email` and `login_password` in each API request
2. **Environment variables**: Set `LINKEDIN_EMAIL` and `LINKEDIN_PASSWORD` in your environment

**Note**: LinkedIn may detect automated access. Use credentials from accounts that have appropriate permissions and be mindful of rate limits.

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `CHROMEDRIVER` | Path to ChromeDriver executable | `/usr/local/bin/chromedriver` |
| `API_HOST` | API host address | `0.0.0.0` |
| `API_PORT` | API port number | `8000` |
| `MAX_DRIVERS` | Maximum number of Chrome drivers in pool | `3` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `LINKEDIN_EMAIL` | Default LinkedIn email | None |
| `LINKEDIN_PASSWORD` | Default LinkedIn password | None |

### Driver Pool Management

The API uses a connection pool to manage Chrome drivers efficiently:

- **Pool Size**: Configurable via `MAX_DRIVERS`
- **Resource Reuse**: Drivers are reused across requests
- **Automatic Cleanup**: Drivers are properly closed on shutdown
- **Error Recovery**: Failed drivers are automatically replaced

## Error Handling

The API provides comprehensive error handling:

- **400 Bad Request**: Invalid input parameters
- **401 Unauthorized**: LinkedIn login failed
- **404 Not Found**: LinkedIn profile/company not found
- **429 Too Many Requests**: Rate limit exceeded
- **500 Internal Server Error**: Scraping or server errors

Example error response:
```json
{
  "detail": "Failed to scrape person profile: Profile not found"
}
```

## Performance Optimization

### Best Practices

1. **Reuse Connections**: Use batch endpoints for multiple profiles
2. **Rate Limiting**: Implement client-side rate limiting
3. **Caching**: Cache results to avoid repeated scraping
4. **Concurrent Requests**: API supports concurrent requests up to driver pool size
5. **Resource Monitoring**: Monitor `/health` endpoint for system status

### Scaling Considerations

- **Horizontal Scaling**: Deploy multiple instances behind a load balancer
- **Database Integration**: Add database storage for scraped data
- **Queue System**: Implement job queues for large batch operations
- **Caching Layer**: Add Redis for response caching

## Security

### Production Security Measures

1. **Authentication**: Implement API key authentication
2. **Rate Limiting**: Add request rate limiting
3. **Input Validation**: Validate all LinkedIn URLs
4. **HTTPS**: Use HTTPS in production
5. **Secrets Management**: Use proper secret management for credentials

### Example Security Enhancement

```python
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    if credentials.credentials != "your-api-key":
        raise HTTPException(status_code=401, detail="Invalid API key")
    return credentials.credentials
```

## Monitoring and Logging

### Health Monitoring

The `/health` endpoint provides:
- API status
- Active driver count
- Timestamp
- System resources

### Logging

Comprehensive logging includes:
- Request/response logs
- Error tracking
- Performance metrics
- Driver pool status

## Legal Considerations

⚠️ **Important**: Web scraping may violate LinkedIn's Terms of Service. This tool is for educational purposes only. Users are responsible for:

1. Complying with LinkedIn's robots.txt and Terms of Service
2. Respecting rate limits and being considerate of LinkedIn's servers
3. Ensuring compliance with applicable laws and regulations
4. Obtaining necessary permissions for data use

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:
1. Check the GitHub issues
2. Review the documentation
3. Create a new issue with detailed information

## Changelog

### v1.0.0
- Initial release
- Person, company, and job scraping
- Batch processing support
- Docker and Render deployment
- Health monitoring
- Error handling and logging
