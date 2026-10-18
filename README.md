
# Food Bridge — Food Waste Management System

Food Bridge is a food donation management system that helps food donors share surplus food with NGOs and track donation requests, approvals, and collections.

## Technology Stack

- **Backend:** Python, FastAPI
- **Relational database:** MySQL
- **Document database:** MongoDB
- **API testing:** Swagger UI

## Features

- View available food listings
- Create food listings
- Submit donation requests
- Approve or reject requests
- Record food collections
- Store and retrieve food reviews
- Use MySQL for structured data and MongoDB for review documents

## Project Structure

```text
Food_Bridge/
├── main.py
├── database.py
├── mongodb.py
├── food.py
├── users.py
├── requests_api.py
├── reports.py
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

The files listed above reflect the intended structure. Keep any additional Python modules required by the actual application.

## Prerequisites

- Python 3.11 or a compatible version
- MySQL Server and MySQL Workbench
- MongoDB Community Server
- MongoDB Compass

## Setup Instructions

### 1. Clone the repository

```bash
git clone https://github.com/saivedant09-gif/FoodBridge.git
cd FoodBridge
```

### 2. Install Python dependencies

```bash
python -m pip install -r requirements.txt
```

### 3. Configure environment variables

Create a local `.env` file based on `.env.example`.

Add the MySQL connection settings expected by `database.py`. Never commit your actual `.env` file or database password.

### 4. Configure MySQL

Create the `food_bridge` database and its required tables using the project's SQL schema/setup script.

### 5. Configure MongoDB

Start MongoDB Community Server and create the database and collection expected by `mongodb.py`.

The local MongoDB connection commonly uses:

```text
mongodb://localhost:27017
```

### 6. Start the API

```bash
python -m uvicorn main:app --reload
```

### 7. Open the API documentation

- Swagger UI: http://127.0.0.1:8000/docs
- API root: http://127.0.0.1:8000/

## API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/` | API status |
| GET | `/food` | List food donations |
| POST | `/food` | Create a food listing |
| POST | `/requests` | Create a donation request |
| PUT | `/requests/{request_id}/approve` | Approve a request |
| PUT | `/requests/{request_id}/reject` | Reject a request |
| POST | `/requests/{request_id}/collect` | Record a collection |
| GET | `/reviews` | Retrieve food reviews |
| POST | `/reviews` | Create a food review |
| GET | `/reviews/{food_id}` | Retrieve reviews for a food item |

Confirm the endpoint list against `main.py` before treating it as exhaustive.

## Frontend Integration

The frontend can use the FastAPI backend during local development at:

```text
http://127.0.0.1:8000
```

Refer to `/docs` for request fields, response formats, and available endpoints.

## Security Notes

- Do not commit `.env` or real credentials.
- Use environment variables for database configuration.
- Configure appropriate CORS rules before connecting a browser-based frontend.
- Use test data during development.

## Project Status

Backend development and initial API testing are complete. Frontend integration and further testing can be carried out next.
