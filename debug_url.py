import os
import sys
from urllib.parse import urlparse
import socket

# Load from config
try:
    from config import DATABASE_URL
except ImportError:
    print("Could not import DATABASE_URL from config")
    sys.exit(1)

print(f"Original URL: {DATABASE_URL}")

try:
    parsed = urlparse(DATABASE_URL)
    hostname = parsed.hostname
    port = parsed.port
    username = parsed.username
    password = parsed.password
    
    print(f"Parsed Hostname: '{hostname}'")
    print(f"Parsed Port: {port}")
    print(f"Parsed Username: '{username}'")
    # Mask password for security in logs
    if password:
        masked = password[0] + "*" * (len(password)-2) + password[-1] if len(password) > 2 else "***"
        print(f"Parsed Password: '{masked}'")
    
    if not hostname:
        print("ERROR: Could not extract hostname from URL!")
        sys.exit(1)
        
    print(f"\nAttempting to resolve IP for: {hostname}")
    try:
        ip = socket.gethostbyname(hostname)
        print(f"SUCCESS! IP Address: {ip}")
    except socket.gaierror as e:
        print(f"DNS RESOLUTION FAILED: {e}")
        print("This means the domain name does not exist or cannot be reached from this computer.")
        print("Possible causes:")
        print("1. Typos in the project ID (the 'cnjsflffoywmzhebospy' part).")
        print("2. The Supabase project is Paused (check your Supabase dashboard).")
        print("3. Local DNS issues.")
        
except Exception as e:
    print(f"Error parsing URL: {e}")
