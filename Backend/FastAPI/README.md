# FastAPI Application Template

This repository contains a basic **FastAPI** application template designed with clean architecture principles to promote scalability, maintainability, and ease of understanding for developers. It separates concerns into **Controllers**, **Services**, and **Repositories**, following best practices in software development.

## Table of Contents

- [Project Structure](#project-structure)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Application](#running-the-application)
- [API Endpoints](#api-endpoints)
- [Testing](#testing)
- [Scaling and Future Development](#scaling-and-future-development)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

---

## Project Structure

```plaintext
backend/
├── fastapi_app/
    ├── .env
    ├── .gitignore
    ├── README.md
    ├── requirements.txt
    ├── app/
    │   ├── __init__.py
    │   ├── config.py
    │   ├── database.py
    │   ├── main.py
    │   ├── controllers/
    │   │   ├── __init__.py
    │   │   └── sample_controller.py
    │   ├── models/
    │   │   ├── __init__.py
    │   │   └── sample_models.py
    │   ├── repositories/
    │   │   ├── __init__.py
    │   │   └── sample_repositories.py
    │   └── services/
    │       ├── __init__.py
    │       └── sample_service.py
    └── tests/
        ├── __init__.py
        └── test_sample.py
```

---

## Features

- **Clean Architecture**: Separation of concerns into Controllers, Services, and Repositories.
- **FastAPI**: High-performance web framework for building APIs.
- **SQLAlchemy**: ORM for interacting with the PostgreSQL database.
- **Pydantic**: Data validation and settings management.
- **Testing**: Set up with `pytest` for writing unit tests.
- **Environment Variables**: Configuration via `.env` file.

---

## Prerequisites

- **Python 3.10 or higher**: Ensure Python is installed on your system.
- **PostgreSQL**: Install PostgreSQL and ensure it's running.

---

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/your-repo.git
```

### 2. Navigate to the Project Directory

```bash
cd backend/fastapi_app
```

### 3. Create a Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows, use venv\Scripts\activate
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Configuration

### 1. Create a `.env` File

Create a `.env` file in the project root:

```bash
touch .env
```

### 2. Add Database Configuration

```dotenv
DATABASE_URL=postgresql://your_username:your_password@localhost:5432/your_database
```

Replace `your_username`, `your_password`, and `your_database` with your actual PostgreSQL credentials.

---

## Running the Application

### 1. Start the PostgreSQL Server

Ensure that PostgreSQL is running on your system.

- **MacOS**:

  ```bash
  brew services start postgresql
  ```

### 2. Create the Database and User

Connect to PostgreSQL using the `psql` command-line tool:

```bash
psql postgres
```

Create a new user and database:

```sql
CREATE USER your_username WITH PASSWORD 'your_password';
CREATE DATABASE your_database OWNER your_username;
GRANT ALL PRIVILEGES ON DATABASE your_database TO your_username;
\q
```

### 3. Start the FastAPI Application

```bash
uvicorn app.main:app --reload
```

### 4. Access the API Documentation

Open your browser and navigate to [http://localhost:8000/docs](http://localhost:8000/docs) to access the Swagger UI.

---

## API Endpoints

- **`POST /items/`**: Create a new item.
- **`GET /items/`**: Retrieve all items.
- **`GET /items/{item_id}`**: Retrieve an item by ID.

---

## Testing

Tests are located in the `tests/` directory and use `pytest`.

### Running Tests

```bash
pytest
```

---

## Scaling and Future Development

### 1. Extending Models

Add new models in the `models` directory following the existing patterns.

### 2. Adding Business Logic

Implement additional logic in the `services` layer to handle complex operations.

### 3. Implementing Repositories

For each new model, create corresponding repository functions for database interactions.

### 4. Creating Controllers

Develop new API endpoints in the `controllers` directory to expose functionalities.

### 5. Clean Architecture Principles

- **Controllers**: Handle HTTP requests and responses.
- **Services**: Contain business logic and interact with repositories.
- **Repositories**: Interact with the database.

---

## Troubleshooting

### Common Issues

- **Database Connection Errors**: Ensure PostgreSQL is running and the credentials in your `.env` file are correct.
- **Module Import Errors**: Verify that all import statements are correct and use absolute imports where necessary.
- **Dependency Issues**: Ensure all dependencies are installed by running `pip install -r requirements.txt`.

### Logs and Debugging

- Use logging statements to debug issues.
- Check console output for error messages during application startup.

---

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

---

## License

This project is licensed under the MIT License.

---

# Additional Information

## Database Setup Details

### 1. Install PostgreSQL (if not already installed)

- **MacOS**:

  ```bash
  brew install postgresql
  ```

- **Windows** and **Linux**: Download and install from [PostgreSQL Official Website](https://www.postgresql.org/download/).

### 2. Initialize the Database Cluster (if necessary)

If you're installing PostgreSQL for the first time, you might need to initialize the database cluster.

```bash
initdb /usr/local/var/postgres
```

### 3. Starting and Stopping PostgreSQL Server

- **Start Server**:

  ```bash
  pg_ctl -D /usr/local/var/postgres start
  ```

- **Stop Server**:

  ```bash
  pg_ctl -D /usr/local/var/postgres stop
  ```

---

## Project Structure Details

- **`app/`**: Main application package.
  - **`main.py`**: Entry point of the application.
  - **`config.py`**: Handles application configuration and settings.
  - **`database.py`**: Database connection and session management.
  - **`controllers/`**: Handles incoming HTTP requests.
  - **`services/`**: Contains business logic.
  - **`repositories/`**: Interacts with the database.
  - **`models/`**: Defines data models and schemas.
- **`tests/`**: Contains test cases for the application.

---

## Dependencies

### `requirements.txt`

```plaintext
fastapi
uvicorn
SQLAlchemy
psycopg2-binary
python-dotenv
pydantic
pytest
```

---

## Environment Variables

- **`DATABASE_URL`**: Connection string for the PostgreSQL database.

---

## Best Practices

- **Use Virtual Environments**: Isolate project dependencies.
- **Environment Variables**: Keep sensitive data out of source control.
- **Code Formatting**: Use tools like `black` or `flake8` for consistent code style.
- **Logging**: Implement logging for better debugging and monitoring.
- **Documentation**: Keep the code and API endpoints well-documented.

---

## Further Reading

- **FastAPI Documentation**: [https://fastapi.tiangolo.com/](https://fastapi.tiangolo.com/)
- **SQLAlchemy Documentation**: [https://docs.sqlalchemy.org/](https://docs.sqlalchemy.org/)
- **Pydantic Documentation**: [https://pydantic-docs.helpmanual.io/](https://pydantic-docs.helpmanual.io/)
- **Clean Architecture Concepts**: [The Clean Architecture](https://8thlight.com/blog/uncle-bob/2012/08/13/the-clean-architecture.html)

---

