import asyncio
import sys

# psycopg's async mode (the LangGraph checkpointer) can't run on Windows' default Proactor loop;
# asyncpg runs on either. Linux (Docker, ECS) is unaffected.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
