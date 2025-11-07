<!-- PROJECT BANNER -->
<p align="center">
  <a href="https://github.com/SheriffMudasir/IntentLink">
    <img src="assets/banner.png" width="100%" alt="IntentLink Banner">
  </a>
</p>

<br />

<h1 align="center">🚀 IntentLink</h1>
<h3 align="center">Your AI Copilot for Secure, Multi-Chain DeFi on BlockDAG</h3>

<p align="center">
  <!-- GitHub Badges -->
  <a href="https://github.com/SheriffMudasir/IntentLink/stargazers">
    <img src="https://img.shields.io/github/stars/SheriffMudasir/IntentLink?style=for-the-badge&logo=github" />
  </a>
  <a href="https://github.com/SheriffMudasir/IntentLink/blob/main/LICENSE">
    <img src="https://img.shields.io/github/license/SheriffMudasir/IntentLink?style=for-the-badge" />
  </a>
  <!-- Project Badges -->
  <a href="https://blockdag.network/hackathon">
    <img src="https://img.shields.io/badge/Track-DeFi%20Speedway-purple?style=for-the-badge" />
  </a>
  <img src="https://img.shields.io/badge/Status-Phase%201%20(Ideation)-orange?style=for-the-badge" />
</p>

---

This directory contains the core backend service for IntentLink. It is a Django project built with Django-Ninja that exposes a RESTful API for parsing, planning, simulating, and executing user intents on-chain.

## Table of Contents

- [Features](#-features)
- [Tech Stack & Architecture](#-tech-stack--architecture)
- [Local Development Setup](#-local-development-setup)
- [Project Structure](#-project-structure)
- [API Endpoints](#-api-endpoints)
- [Environment Variables](#-environment-variables)
- [Running Tests](#-running-tests)

---

## ✨ Features

- **Typed API:** Leverages Django-Ninja and Pydantic for a fully typed, self-documenting API.
- **Intent Processing Pipeline:** A secure, deterministic pipeline from natural language to transaction.
- **Multi-Chain Architecture:** Designed to be chain-agnostic, supporting BlockDAG, Polygon, and other EVM networks.
- **Asynchronous Task Execution:** Uses Celery and Redis for handling long-running tasks like simulation and transaction relaying without blocking the API.
- **Containerized:** Fully containerized with Docker and Docker Compose for consistent development and production environments.

---

## 🏗️ Tech Stack & Architecture

- **Framework:** Django 4.x
- **API Layer:** Django-Ninja
- **Database:** PostgreSQL
- **Cache & Message Broker:** Redis
- **Async Task Queue:** Celery
- **Web Server:** Gunicorn
- **HTTP Client:** `httpx`

The backend consists of four primary services orchestrated by `docker-compose`:

1.  `web`: The Gunicorn server running the Django application and serving the API.
2.  `db`: The PostgreSQL database for storing intents, plans, and executions.
3.  `cache`: The Redis instance for caching (e.g., DAGScanner results) and as a Celery message broker.
4.  `worker`: A Celery worker that processes background jobs from the queue (e.g., `simulation_queue`, `relayer_queue`).

---

## 🚀 Local Development Setup

### Prerequisites

- Docker
- Docker Compose
- Python 3.10+ (for local tooling, though the app runs in a container)

### Step-by-Step Guide

1.  **Clone the Repository:**
    If you are in the root directory:

    ```bash
    # (You are already here)
    ```

2.  **Navigate to the Backend Directory:**

    ```bash
    cd intentlink-backend
    ```

3.  **Create the Environment File:**
    Copy the example environment file. This file is ignored by Git and will hold your local secrets and configuration.

    ```bash
    cp .env.example .env
    ```

4.  **Configure Your `.env` File:**
    Open the newly created `.env` file and:

    - Generate and add a `SECRET_KEY` (see Django docs for generating one).
    - Add a test wallet private key for the `RELAYER_PRIVATE_KEY`.
    - Review other variables and adjust if necessary.

5.  **Build and Run the Docker Containers:**
    This command will build the Docker images and start all the services (`web`, `db`, `cache`, `worker`) in the background.

    ```bash
    docker-compose up --build -d
    ```

6.  **Run Database Migrations:**
    The first time you start the application, you need to create the database schema.

    ```bash
    docker-compose exec web python manage.py migrate
    ```

7.  **Create a Superuser (Optional):**
    This allows you to access the Django Admin interface.

    ```bash
    docker-compose exec web python manage.py createsuperuser
    ```

8.  **Access the API:**
    - The API is now running at `http://localhost:8000/api/`.
    - Interactive API documentation (Swagger UI) is available at `http://localhost:8000/api/v1/docs`.
    - The Django Admin is at `http://localhost:8000/admin/`.

---

## 📂 Project Structure

.
├── api_v1/ # Django app for Version 1 of the API
│ ├── migrations/ # Database migrations
│ ├── models.py # Database models (Intent, Plan, Execution)
│ ├── schemas.py # Pydantic schemas for API I/O
│ └── api.py # API endpoint definitions (views)
├── intentlink_project/ # Main Django project configuration
│ ├── settings.py # Core settings, configured via .env
│ ├── urls.py # Root URL configuration
│ ├── celery.py # Celery application instance
│ └── ...
├── .env.example # Template for environment variables
├── docker-compose.yml # Defines and orchestrates the services
├── Dockerfile # Defines the application container image
└── requirements.txt # Python dependencies

---

## 🔌 API Endpoints

All endpoints are prefixed with `/api/v1/`. See the live docs at `/api/v1/docs` for detailed request/response models.

- `POST /parse-intent/`: Parses natural language input into a structured intent.
- `POST /plan/`: Generates an execution plan based on a parsed intent.
- `POST /simulate/`: Runs a dry-run simulation of a plan on a forked network.
- `POST /prepare-signature/`: Creates the EIP-712 typed data for a user to sign.
- `POST /submit-intent/`: Verifies a signature and queues a plan for execution.
- `GET /execution/{execution_id}/status/`: Retrieves the status of an execution.

---

## 🔑 Environment Variables

The application is configured entirely through environment variables. See `.env.example` for a complete list. Key variables include:

| Variable              | Description                                                                  |
| :-------------------- | :--------------------------------------------------------------------------- |
| `SECRET_KEY`          | **Required.** Django's secret key for cryptographic signing.                 |
| `DEBUG`               | Set to `True` for development, `False` for production.                       |
| `POSTGRES_DB`         | Name of the PostgreSQL database.                                             |
| `POSTGRES_USER`       | Username for the PostgreSQL database.                                        |
| `POSTGRES_PASSWORD`   | Password for the PostgreSQL database.                                        |
| `REDIS_URL`           | Connection URL for the Redis instance.                                       |
| `BLOCKDAG_RPC_URL`    | RPC endpoint for the BlockDAG "Awakening" Testnet.                           |
| `RELAYER_PRIVATE_KEY` | **Required for dev.** Private key of the wallet used to submit transactions. |

---

## 🧪 Running Tests

We will build a comprehensive testing suite

```

```
