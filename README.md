# AI Agent API

A FastAPI backend for AI agent-related APIs, designed with industry best practices for code quality, maintainability, and scalability.

## Features

- Modular design with well-defined components
- Comprehensive error handling and logging
- Robust input validation and sanitization
- Secure API endpoints with JWT authentication
- Asynchronous programming for maximum performance
- RESTful API design
- Monitoring and logging of API usage and performance metrics

## Tech Stack

- FastAPI: Modern, fast web framework for building APIs
- SQLAlchemy: SQL toolkit and ORM
- Pydantic: Data validation and settings management
- Alembic: Database migration tool
- OpenAI: AI model integration
- JWT: Authentication mechanism
- Docker: Containerization
- PostgreSQL: Database

## Getting Started

### Prerequisites

- Python 3.9+
- Docker and Docker Compose (optional)

### Installation

1. Clone the repository:

\`\`\`bash
git clone https://github.com/yourusername/ai-agent-api.git
cd ai-agent-api
\`\`\`

2. Create a virtual environment and install dependencies:

\`\`\`bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
\`\`\`

3. Create a `.env` file with your configuration:

\`\`\`
DATABASE_URL=sqlite+aiosqlite:///./app.db
SECRET_KEY=your-secret-key
OPENAI_API_KEY=your-openai-api-key
\`\`\`

4. Run database migrations:

\`\`\`bash
alembic upgrade head
\`\`\`

5. Start the server:

\`\`\`bash
uvicorn main:app --reload
\`\`\`

### Using Docker

1. Build and start the containers:

\`\`\`bash
docker-compose up -d
\`\`\`

2. The API will be available at http://localhost:8000

## API Documentation

Once the server is running, you can access the API documentation at:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Project Structure

\`\`\`
ai-agent-api/
├── alembic/                  # Database migrations
├── app/
│   ├── api/                  # API endpoints
│   │   └── routes/           # Route definitions
│   ├── core/                 # Core functionality
│   │   ├── config.py         # Application configuration
│   │   ├── logging_config.py # Logging configuration
│   │   └── security.py       # Authentication and security
│   ├── db/                   # Database
│   │   └── database.py       # Database connection
│   ├── models/               # SQLAlchemy models
│   ├── schemas/              # Pydantic schemas
│   └── services/             # Business logic
├── tests/                    # Tests
├── main.py                   # Application entry point
├── requirements.txt          # Dependencies
├── Dockerfile                # Docker configuration
└── docker-compose.yml        # Docker Compose configuration
\`\`\`

## Testing

Run tests with pytest:

\`\`\`bash
pytest
\`\`\`

## License

This project is licensed under the MIT License - see the LICENSE file for details.
