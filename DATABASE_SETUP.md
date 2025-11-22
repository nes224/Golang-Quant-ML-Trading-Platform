# Setup Instructions for PostgreSQL Database

## Step 1: Copy Environment File
```bash
cp .env.example .env
```

Then edit `.env` and set your database password:
```
DB_PASSWORD=your_strong_password_here
```

## Step 2: Start PostgreSQL with Docker
```bash
docker-compose up -d
```

This will:
- Download PostgreSQL 15 Alpine image
- Create a container named `trading_bot_db`
- Initialize the database with schema from `db_schema.sql`
- Create persistent volume for data

## Step 3: Verify Database is Running
```bash
docker ps
```

You should see `trading_bot_db` container running.

## Step 4: Install Python Dependencies
```bash
cd Trading_Api
pip install -r requirements.txt
```

## Step 5: Test Database Connection
```python
from db_manager import get_db_manager

# Get database manager
db = get_db_manager()

# Test connection
stats = db.get_overall_stats()
print(stats)
```

## Step 6: (Optional) Access PostgreSQL CLI
```bash
docker exec -it trading_bot_db psql -U trading_user -d trading_bot
```

Common commands:
- `\dt` - List all tables
- `\d trades` - Describe trades table
- `SELECT * FROM trades LIMIT 10;` - Query trades
- `\q` - Quit

## Troubleshooting

### Port Already in Use
If port 5432 is already in use, change it in `.env`:
```
DB_PORT=5433
```

Then restart:
```bash
docker-compose down
docker-compose up -d
```

### Reset Database
```bash
docker-compose down -v  # Remove volumes
docker-compose up -d    # Recreate
```

### View Logs
```bash
docker logs trading_bot_db
```
