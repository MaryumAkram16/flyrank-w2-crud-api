"""
Initializes a single shared Supabase client from environment variables.
Import `supabase` from this module anywhere you need to call the Auth SDK
(signup, login, logout, token verification) so the whole app shares one
client instance instead of creating a new one per request.
"""
import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError(
        "SUPABASE_URL and SUPABASE_KEY must be set in your .env file. "
        "Copy .env.example to .env and fill in your Supabase Project URL "
        "and anon key from Project Settings -> API."
    )

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
