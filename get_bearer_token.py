#!/usr/bin/env python3
"""
Get Bearer Token for Render API
Uses Supabase to authenticate and get JWT token
"""
import os
import sys
from pathlib import Path
import json

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

SUPABASE_URL = os.getenv("VITE_SUPABASE_URL") or os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("VITE_SUPABASE_ANON_KEY") or os.getenv("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    print("❌ Error: SUPABASE_URL and SUPABASE_ANON_KEY must be set in .env")
    print("\nLooking for:")
    print("  - VITE_SUPABASE_URL or SUPABASE_URL")
    print("  - VITE_SUPABASE_ANON_KEY or SUPABASE_ANON_KEY")
    sys.exit(1)

try:
    from supabase import create_client, Client
except ImportError:
    print("❌ Error: supabase-py not installed")
    print("Install it with: pip install supabase")
    sys.exit(1)

def get_token(email: str, password: str):
    """Get JWT token from Supabase"""
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    
    print(f"🔐 Logging in as: {email}")
    
    try:
        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        
        if response.user and response.session:
            token = response.session.access_token
            print(f"\n✅ SUCCESS! Token obtained")
            print(f"\n📋 Your Bearer Token:")
            print("-" * 80)
            print(token)
            print("-" * 80)
            
            print(f"\n📝 Use it in curl like this:")
            print(f"curl -H 'Authorization: Bearer {token[:50]}...' \\")
            print(f"     https://habexa-backend-w5u5.onrender.com/api/v1/auth/me")
            
            # Save to file
            token_file = Path(".bearer_token.txt")
            token_file.write_text(token)
            print(f"\n💾 Token saved to: {token_file}")
            print(f"   Use: export BEARER_TOKEN=$(cat .bearer_token.txt)")
            
            return token
        else:
            print("❌ Error: No token in response")
            return None
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        if "Invalid login credentials" in str(e):
            print("\n💡 Check your email and password")
        return None

if __name__ == "__main__":
    import getpass
    
    if len(sys.argv) > 1:
        email = sys.argv[1]
    else:
        email = input("Email: ")
    
    password = getpass.getpass("Password: ")
    
    token = get_token(email, password)
    
    if token:
        print("\n✅ Ready to use!")
        print(f"\nExample curl command:")
        print(f"curl -X GET 'https://habexa-backend-w5u5.onrender.com/api/v1/auth/me' \\")
        print(f"     -H 'Authorization: Bearer {token[:50]}...'")
    else:
        sys.exit(1)

