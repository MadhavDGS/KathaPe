import os
import requests

SUPABASE_URL = 'https://ghbmfgomnqmffixfkdyp.supabase.co'
SERVICE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdoYm1mZ29tbnFtZmZpeGZrZHlwIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0NzE0MDE1NywiZXhwIjoyMDYyNzE2MTU3fQ.RnbSqdIM5A67NuKHDOTdpqpu6G2zKJfhMeQapGUI2kw'

headers = {
    'apikey': SERVICE_KEY,
    'Authorization': f'Bearer {SERVICE_KEY}',
    'Content-Type': 'application/json'
}

with open('rls_fix.sql', 'r') as f:
    sql = f.read()

# Execute the SQL directly (not using the RPC endpoint)
response = requests.post(
    f'{SUPABASE_URL}/sql',
    headers=headers,
    data=sql
)

print(f'Response: {response.status_code}')
print(response.text)

print("RLS policy update completed!") 