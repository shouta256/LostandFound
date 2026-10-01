# Lost and Found

> A searchable app that lets students and campus offices post found items or search for lost ones — so items stop ending up forgotten in a drawer.

## Overview

Lost items (AirPods, IDs, water bottles) end up in a random office drawer nobody checks, and people just give up looking. This web application helps reunite lost items with their owners by providing a centralized platform for reporting and searching for lost and found items on campus.

## Features

- **Post Found Items** - Students and campus offices can create listings for items they have found.
- **Search Lost Items** - Users can search for lost items using information such as item name, category, location, or date.
- **Item Details** - Users can view important information about a lost or found item.
- **Report Lost Items** - Students can provide information about items they have lost.
- **Manage Listings** - Users can update or remove their own lost and found listings.
- **Item Status** - Listings can be updated when an item has been returned to its owner.
- **Campus-Focused Search** - The system is designed specifically to help students and campus offices manage lost and found items.

## Getting Started

> The project is in the environment-setup stage. There is no application code to run yet.

### Tech Stack

- **Backend:** Python, FastAPI, Pydantic
- **Database:** PostgreSQL (run locally with Docker Compose)
- **SQLAlchemy** – database access / ORM (work with tables as Python classes)
- **Alembic** – database schema migrations (a version history of table changes)
- **pytest** – testing, used for TDD
- **Frontend:** not decided yet

### Prerequisites

- Git
- Python 3.11 or newer (`python3 --version`)
- Docker Desktop (must be running before you use `docker compose`)

### 1. Clone the repository

```bash
git clone https://github.com/shouta256/LostandFound.git
cd LostandFound
```

### 2. Install the Python dependencies

Create a virtual environment (an isolated place for this project's packages) and install:

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt
```

Run `source .venv/bin/activate` again each time you open a new terminal.

### 3. Create your `.env` file

```bash
cp .env.example .env             # Windows: copy .env.example .env
```

`.env` holds your local database settings. It is ignored by Git — never commit it.

### 4. Start PostgreSQL

```bash
docker compose up -d
```

This starts PostgreSQL in the background on `localhost:5432`. Check that it is running (STATUS should say `healthy`):

```bash
docker compose ps
```

### 5. Stop PostgreSQL

```bash
docker compose down
```

Your data is kept in a Docker volume. To delete the database data completely, run `docker compose down -v`.

### Usage

1. **Browse Found Items** - Visit the homepage to see all items that have been found
2. **Report a Lost Item** - Click "Report Lost Item" and fill in details about your missing item
3. **Post a Found Item** - Click "Post Found Item" if you've found something and want to help return it
4. **Search for Items** - Use the search bar to filter items by name, category, location, or date
5. **Contact Owner** - View item details and contact information to claim your lost item

## Project Structure

```
.
├── backend/
│   └── requirements.txt   # Python dependencies
├── docker-compose.yml     # Local PostgreSQL (database only)
├── .env.example           # Template for your local .env
├── README.md              # This file
└── GITHUB_GUIDE.md        # Git workflow guide for contributors
```

## Configuration

Local settings live in `.env` (copied from `.env.example`). The defaults are for local development only and work without changes. If port 5432 is already in use on your machine, change `POSTGRES_PORT` in `.env`.

## Contributing

New to GitHub? Read the [GitHub Beginner Guide](GITHUB_GUIDE.md) for the clone, edit, commit, and push workflow.

### Contributing Steps

1. Create a branch for your change (`git switch -c feature-name`)
2. Make and test your changes locally
3. Commit your changes with a clear message (`git commit -m "Description of change"`)
4. Push your branch to GitHub (`git push -u origin feature-name`)
5. Open a pull request with a clear description of your changes
6. Respond to any feedback from code reviewers
7. Once approved, your pull request will be merged into main

For detailed instructions, see the [GitHub Beginner Guide](GITHUB_GUIDE.md).

## License

This project is created for educational purposes as part of the CM 333 course at Washburn University.
