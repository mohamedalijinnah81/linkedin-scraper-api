# LinkedIn Scraper API

A comprehensive RESTful API for scraping LinkedIn profiles, companies, and job postings built with FastAPI and Selenium. This API provides endpoints to extract structured data from LinkedIn with automatic login handling and containerized deployment.

## Features

- 🚀 **Fast and Async**: Built with FastAPI for high performance
- 🔐 **Automatic Login**: Uses environment variables for LinkedIn authentication
- 🏢 **Multiple Scrapers**: Support for Person, Company, and Job scraping
- 🐳 **Containerized**: Docker-ready with Chrome/ChromeDriver included
- 📊 **Structured Data**: Returns clean, structured JSON responses
- 🔄 **Connection Pooling**: Efficient WebDriver management
- 📋 **Comprehensive Logging**: Detailed logging for debugging
- 🛡️ **Error Handling**: Robust error handling and validation

## Quick Start

### Using Docker (Recommended)

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/linkedin-scraper-api.git
   cd linkedin-scraper-api
   ```

2. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your LinkedIn credentials
   ```

3. **Run with Docker Compose**
   ```bash
   docker-compose up --build
   ```

4. **Access the API**
   - API: http://localhost:8000
   - Documentation: http://localhost:8000/docs
   - Health Check: http://localhost:8000/health

### Using Docker Hub Image

```bash
# Pull the latest image
docker pull ghcr.io/yourusername/linkedin-scraper-api:latest

# Run the container
docker run -p 8000:8000 \
  -e LINKEDIN_EMAIL=your-email@example.com \
  -e LINKEDIN_PASSWORD=your-password \
  ghcr.io/yourusername/linkedin-scraper-api:latest
```

## API Endpoints

### Base URL
```
http://localhost:8000
```

### Authentication
The API handles LinkedIn authentication internally using environment variables. No API key required.

### Endpoints Overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Root endpoint with API information |
| GET | `/health` | Health check endpoint |
| POST | `/scrape/person` | Scrape a LinkedIn person profile |
| POST | `/scrape/company` | Scrape a LinkedIn company profile |
| POST | `/scrape/job` | Scrape a LinkedIn job posting |
| POST | `/scrape/job-search` | Search for jobs (coming soon) |

---

## Person Scraping

### Endpoint
```http
POST /scrape/person
```

### Request Body
```json
{
  "linkedin_url": "https://www.linkedin.com/in/john-doe"
}
```

### Response
```json
{
  "linkedin_url": "https://www.linkedin.com/in/john-doe",
  "name": "John Doe",
  "about": "Software Engineer with 5+ years experience...",
  "experiences": [
    {
      "title": "Senior Software Engineer",
      "company": "Tech Corp",
      "duration": "2021 - Present",
      "location": "San Francisco, CA",
      "description": "Leading development of..."
    }
  ],
  "educations": [
    {
      "institution": "University of California",
      "degree": "Bachelor of Science in Computer Science",
      "duration": "2015 - 2019",
      "description": "Graduated Magna Cum Laude"
    }
  ],
  "interests": [
    {
      "name": "Artificial Intelligence",
      "followers": "1.2M followers"
    }
  ],
  "accomplishments": [
    {
      "category": "Publications",
      "title": "Machine Learning in Production",
      "description": "Published research paper on..."
    }
  ],
  "company": "Tech Corp",
  "job_title": "Senior Software Engineer",
  "scraped_at": "2024-01-15T10:30:00Z"
}
```

### cURL Example
```bash
curl -X POST "http://localhost:8000/scrape/job" \
  -H "Content-Type: application/json" \
  -d '{
    "linkedin_url": "https://www.linkedin.com/jobs/view/1234567890"
  }'
```

---

## Job Search

### Endpoint
```http
POST /scrape/job-search
```

### Request Body
```json
{
  "query": "Software Engineer",
  "location": "San Francisco, CA",
  "limit": 10
}
```

### Response
```json
{
  "query": "Software Engineer",
  "location": "San Francisco, CA", 
  "limit": 10,
  "message": "Job search functionality coming soon",
  "scraped_at": "2024-01-15T10:30:00Z"
}
```

### cURL Example
```bash
curl -X POST "http://localhost:8000/scrape/job-search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Software Engineer",
    "location": "San Francisco, CA",
    "limit": 10
  }'
```

---

## Error Handling

The API returns standard HTTP status codes and detailed error messages:

### Success Responses
- `200 OK`: Request successful
- `201 Created`: Resource created successfully

### Error Responses
- `400 Bad Request`: Invalid request format or missing required fields
- `422 Unprocessable Entity`: Validation error
- `500 Internal Server Error`: Server error during scraping

### Error Response Format
```json
{
  "detail": "Failed to scrape person: LinkedIn profile not found"
}
```

### Common Error Scenarios
1. **Invalid LinkedIn URL**: Make sure the URL is a valid LinkedIn profile/company/job URL
2. **Profile Not Found**: The LinkedIn profile may be private or deleted
3. **Rate Limiting**: LinkedIn may temporarily block requests
4. **Login Issues**: Check your LinkedIn credentials in environment variables

---

## Deployment

### Environment Variables

Create a `.env` file with the following variables:

```bash
# Required
LINKEDIN_EMAIL=your-email@example.com
LINKEDIN_PASSWORD=your-password

# Optional
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO
```

### Local Development

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Install ChromeDriver**
   ```bash
   # On macOS
   brew install chromedriver
   
   # On Ubuntu/Debian
   sudo apt-get install chromium-chromedriver
   
   # Set environment variable
   export CHROMEDRIVER=/usr/local/bin/chromedriver
   ```

3. **Run the application**
   ```bash
   uvicorn main:app --reload
   ```

### Docker Deployment

#### Build locally
```bash
docker build -t linkedin-scraper-api .
docker run -p 8000:8000 --env-file .env linkedin-scraper-api
```

#### Using Docker Compose
```bash
docker-compose up --build
```

### Render Deployment

1. **Fork this repository**

2. **Connect to Render**
   - Go to [Render](https://render.com)
   - Create a new Web Service
   - Connect your GitHub repository

3. **Configure Environment Variables**
   - Add `LINKEDIN_EMAIL` and `LINKEDIN_PASSWORD`
   - Set `PYTHON_VERSION` to `3.11`

4. **Deploy**
   - Render will automatically build and deploy your API
   - Access your API at `https://your-service.onrender.com`

### GitHub Container Registry

The project includes GitHub Actions workflow for automatic Docker image building and publishing.

#### Setup
1. Enable GitHub Actions in your repository
2. The workflow will automatically build and push images to `ghcr.io/yourusername/linkedin-scraper-api`

#### Pull and run the image
```bash
docker pull ghcr.io/yourusername/linkedin-scraper-api:latest
docker run -p 8000:8000 \
  -e LINKEDIN_EMAIL=your-email@example.com \
  -e LINKEDIN_PASSWORD=your-password \
  ghcr.io/yourusername/linkedin-scraper-api:latest
```

---

## Rate Limiting & Best Practices

### LinkedIn Rate Limits
- LinkedIn has strict rate limiting policies
- Recommended: 1-2 requests per minute
- Use delays between requests to avoid blocking

### Best Practices
1. **Respect robots.txt**: Always check LinkedIn's robots.txt
2. **Use delays**: Implement delays between requests
3. **Handle errors gracefully**: Retry failed requests with exponential backoff
4. **Monitor usage**: Keep track of your scraping volume
5. **Use authentic headers**: The API uses realistic browser headers

### Monitoring
- Check logs for rate limiting warnings
- Monitor response times
- Track success/failure rates

---

## API Documentation

### Interactive Documentation
Once the API is running, visit:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

### OpenAPI Schema
Get the OpenAPI schema at: `http://localhost:8000/openapi.json`

---

## Development

### Project Structure
```
├── main.py                 # FastAPI application
├── requirements.txt        # Python dependencies
├── Dockerfile             # Docker configuration
├── docker-compose.yml     # Docker Compose configuration
├── .env.example          # Environment variables template
├── .dockerignore         # Docker ignore file
├── .github/
│   └── workflows/
│       └── docker-publish.yml  # GitHub Actions workflow
└── README.md             # This file
```

### Adding New Features

1. **Add new endpoints** in `main.py`
2. **Create request/response models** using Pydantic
3. **Implement scraping logic** following existing patterns
4. **Add tests** (recommended)
5. **Update documentation**

### Testing

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run tests
pytest
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

---

## Troubleshooting

### Common Issues

#### ChromeDriver Issues
```bash
# Check ChromeDriver version
chromedriver --version

# Update ChromeDriver
# Download from: https://chromedriver.chromium.org/
```

#### LinkedIn Login Issues
- Ensure your LinkedIn account language is set to English
- Check if your account requires 2FA (not supported)
- Verify credentials are correct

#### Memory Issues
- Increase Docker memory allocation
- Reduce concurrent scraping operations
- Monitor system resources

#### Rate Limiting
- Implement delays between requests
- Use different LinkedIn accounts (not recommended)
- Monitor LinkedIn's rate limiting messages

### Logs and Debugging

```bash
# View application logs
docker-compose logs -f linkedin-scraper-api

# Enable debug logging
export LOG_LEVEL=DEBUG
```

---

## Legal Considerations

⚠️ **Important**: 
- Review LinkedIn's Terms of Service before using
- Ensure compliance with local data protection laws
- Use responsibly and respect rate limits
- Consider LinkedIn's official APIs for commercial use

---

## License

MIT License - see LICENSE file for details

---

## Support

For issues and questions:
1. Check the [Issues](https://github.com/yourusername/linkedin-scraper-api/issues) page
2. Create a new issue with detailed information
3. Include logs and error messages

---

## Changelog

### v1.0.0
- Initial release
- Person, Company, and Job scraping
- Docker containerization
- FastAPI implementation
- GitHub Actions CI/CD

---

## Roadmap

- [ ] Job search functionality
- [ ] Batch scraping endpoints
- [ ] Rate limiting middleware
- [ ] Caching layer
- [ ] Database integration
- [ ] Authentication system
- [ ] Webhook notifications
- [ ] Data export formats (CSV, Excel)

---

**Made with ❤️ and FastAPI**bash
curl -X POST "http://localhost:8000/scrape/person" \
  -H "Content-Type: application/json" \
  -d '{
    "linkedin_url": "https://www.linkedin.com/in/john-doe"
  }'
```

---

## Company Scraping

### Endpoint
```http
POST /scrape/company
```

### Request Body
```json
{
  "linkedin_url": "https://www.linkedin.com/company/google",
  "get_employees": true
}
```

### Response
```json
{
  "linkedin_url": "https://www.linkedin.com/company/google",
  "name": "Google",
  "about_us": "Google's mission is to organize the world's information...",
  "website": "https://www.google.com",
  "headquarters": "Mountain View, CA",
  "founded": "1998",
  "company_type": "Public Company",
  "company_size": "100,000+ employees",
  "specialties": [
    "Search Technology",
    "Cloud Computing",
    "Artificial Intelligence"
  ],
  "showcase_pages": [
    "Google Cloud",
    "Google AI"
  ],
  "affiliated_companies": [
    "Alphabet Inc.",
    "YouTube"
  ],
  "employees": [
    {
      "name": "Jane Smith",
      "title": "Software Engineer",
      "linkedin_url": "https://www.linkedin.com/in/jane-smith"
    }
  ],
  "scraped_at": "2024-01-15T10:30:00Z"
}
```

### cURL Example
```bash
curl -X POST "http://localhost:8000/scrape/company" \
  -H "Content-Type: application/json" \
  -d '{
    "linkedin_url": "https://www.linkedin.com/company/google",
    "get_employees": true
  }'
```

---

## Job Scraping

### Endpoint
```http
POST /scrape/job
```

### Request Body
```json
{
  "linkedin_url": "https://www.linkedin.com/jobs/view/1234567890"
}
```

### Response
```json
{
  "linkedin_url": "https://www.linkedin.com/jobs/view/1234567890",
  "job_title": "Senior Software Engineer",
  "company": "Tech Corp",
  "location": "San Francisco, CA",
  "description": "We are looking for a Senior Software Engineer...",
  "posted_date": "2024-01-10",
  "scraped_at": "2024-01-15T10:30:00Z"
}
```

### cURL Example
```
