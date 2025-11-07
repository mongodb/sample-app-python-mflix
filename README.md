# Python FastAPI MongoDB Sample MFlix Application

This is a full-stack movie browsing application built with Python FastAPI and Next.js, demonstrating MongoDB operations using the `sample_mflix` dataset. The application showcases CRUD operations, aggregations, and MongoDB Search using the PyMongo driver.

## Project Structure

```
├── README.md
├── client/                 # Next.js frontend (TypeScript)
└── server/  # Python FastAPI backend
    ├── src/
    ├── tests/
    ├── .env.example
    ├── main.py
    ├── pytest.ini
    ├── requirements.in
    └── requirements.txt
```

## Prerequisites

- **Python 3.10** to **Python 3.13**
- **Node.js 20** or higher
- **MongoDB Atlas cluster or local deployment** with the `sample_mflix` dataset loaded
  - [Load sample data](https://www.mongodb.com/docs/atlas/sample-data/)
- **pip** for Python package management
- **Voyage AI API key** (For MongoDB Vector Search)
  - [Get a Voyage AI API key](https://www.voyageai.com/)

## Getting Started

### 1. Configure the Backend

Navigate to the Python FastAPI server directory:

```bash
cd server/
```

Create a `.env` file from the example:

```bash
cp .env.example .env
```

Edit the `.env` file and set your MongoDB connection string:

```env
# MongoDB Configuration
MONGO_URI=mongodb+srv://<username>:<password>@<cluster>.mongodb.net/sample_mflix?retryWrites=true&w=majority
MONGO_DB=sample_mflix

# Voyage AI Configuration
# API key for Voyage AI embedding model (required for Vector Search)
VOYAGE_API_KEY=your_voyage_api_key

# CORS Configuration
# Comma-separated list of allowed origins for CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:3001
```

**Note:** Replace `username`, `password`, and `cluster` with your actual MongoDB Atlas
credentials.

Make a virtual environment:

```bash
python -m venv .venv
```

Activate the virtual environment:

```bash
source .venv/bin/activate
```

Install Python dependencies:

```bash
pip install -r requirements.txt
```

### 2. Start the Backend Server

From the `server/` directory, run:

```bash
uvicorn main:app --reload --port 3001
```

The server will start on `http://localhost:3001`. You can verify it's running by visiting:
- API root: http://localhost:3001/api/movies
- API documentation (Swagger UI): http://localhost:3001/docs
- Interactive API documentation (ReDoc): http://localhost:3001/redoc

### 3. Configure and Start the Frontend

Open a new terminal and navigate to the client directory:

```bash
cd client
```

Install dependencies:

```bash
npm install
```

Start the development server:

```bash
npm run dev
```

The Next.js application will start on `http://localhost:3000`.

### 4. Access the Application

Open your browser and navigate to:
- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:3001
- **API Documentation:** http://localhost:3001/docs

## Features

- **Browse Movies:** View a paginated list of movies from the sample_mflix dataset
- **Search:** Full-text search using MongoDB Search
- **Vector Search:** Semantic search using MongoDB Vector Search with Voyage AI embeddings
- **Filter:** Filter movies by genre, year, rating, and more
- **Movie Details:** View detailed information about each movie
- **Aggregations:** Complex data aggregations and analytics

## Development

### Backend Development

The Python FastAPI backend uses:
- **FastAPI** for REST API framework
- **PyMongo** for database operations
- **Voyage AI** for vector embeddings
- **fastapi** for ASGI server

To run all tests:

```bash
cd server/
source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows
pytest tests/ -v
```

### Frontend Development

The Next.js frontend uses:
- **React 19** with TypeScript
- **Next.js 16** with App Router
- **Turbopack** for fast development builds

#### Development Mode

For active development with hot reloading and fast refresh:

```bash
cd client
npm run dev
```

This starts the development server on `http://localhost:3000` with Turbopack for fast rebuilds.

#### Production Build

To create an optimized production build and run it:

```bash
cd client
npm run build  # Creates optimized production build
npm start      # Starts production server
```

The production build:
- Minifies and optimizes JavaScript and CSS
- Optimizes images and assets
- Generates static pages where possible
- Provides better performance for end users

#### Linting

To check code quality:

```bash
cd client
npm run lint
```

## Issues

If you have problems running the sample app, please check the following:

- [ ] Verify that you have set your MongoDB connection string in the `.env` file.
- [ ] Verify that you have created and activated a Python `.venv` on Python v3.10 through v3.13.
- [ ] Verify that you have started the Python FastAPI server.
- [ ] Verify that you have started the Next.js client.
- [ ] Verify that you have no firewalls blocking access to the server or client ports.

If you have verified the above and still have issues, please
[open an issue](https://github.com/mongodb/docs-sample-apps/issues/new/choose)
on the source repository `mongodb/docs-sample-apps`.
