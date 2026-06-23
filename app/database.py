from databases import Database
from app.config import settings

# Small, bounded pool. Supabase's pooler caps total clients, and on a
# redeploy the old instance still holds its connections during the swap,
# so each instance must stay well under that cap.
#
# IMPORTANT: DATABASE_URL must point at the TRANSACTION-mode pooler
# (port 6543), not session mode (5432). statement_cache_size=0 is required
# because pgbouncer transaction mode can't reuse asyncpg prepared statements.
db = Database(
    settings.database_url,
    min_size=1,
    max_size=5,
    statement_cache_size=0,
)

async def connect():
    await db.connect()

async def disconnect():
    await db.disconnect()
