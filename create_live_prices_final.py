#!/usr/bin/env python3
"""
Create LIVE mode Stripe products and prices using Stripe CLI.
This script properly formats the commands and extracts the IDs.
"""

import os
import json
import subprocess
from dotenv import load_dotenv

# Load .env
load_dotenv('.env')

stripe_key = os.getenv('STRIPE_SECRET_KEY')
if not stripe_key or not stripe_key.startswith('sk_live_'):
    print("❌ STRIPE_SECRET_KEY must be a LIVE key (starts with sk_live_)")
    exit(1)

os.environ['STRIPE_API_KEY'] = stripe_key

def run_stripe_cmd(cmd):
    """Run a Stripe CLI command and return parsed JSON."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            env=os.environ
        )
        if result.returncode != 0:
            print(f"❌ Error: {result.stderr}")
            return None
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        print(f"❌ Failed to parse JSON: {result.stdout}")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

print("✅ Creating LIVE mode products and prices...\n")

# Create products
print("📦 Creating products...")
starter_product = run_stripe_cmd(
    f'stripe products create --name="Starter" --description="Starter plan - $29/month, $290/year"'
)
pro_product = run_stripe_cmd(
    f'stripe products create --name="Pro" --description="Pro plan - $79/month, $790/year"'
)
agency_product = run_stripe_cmd(
    f'stripe products create --name="Agency" --description="Agency plan - $199/month, $1990/year"'
)

if not all([starter_product, pro_product, agency_product]):
    print("❌ Failed to create products")
    exit(1)

starter_id = starter_product['id']
pro_id = pro_product['id']
agency_id = agency_product['id']

print(f"  ✅ Starter: {starter_id}")
print(f"  ✅ Pro: {pro_id}")
print(f"  ✅ Agency: {agency_id}\n")

# Create prices
print("💰 Creating prices...\n")

prices = {}

# Starter prices
print("Creating Starter prices...")
prices['starter_monthly'] = run_stripe_cmd(
    f'stripe prices create --product="{starter_id}" --unit-amount=2900 --currency=usd --recurring.interval=month'
)
prices['starter_yearly'] = run_stripe_cmd(
    f'stripe prices create --product="{starter_id}" --unit-amount=29000 --currency=usd --recurring.interval=year'
)

# Pro prices
print("Creating Pro prices...")
prices['pro_monthly'] = run_stripe_cmd(
    f'stripe prices create --product="{pro_id}" --unit-amount=7900 --currency=usd --recurring.interval=month'
)
prices['pro_yearly'] = run_stripe_cmd(
    f'stripe prices create --product="{pro_id}" --unit-amount=79000 --currency=usd --recurring.interval=year'
)

# Agency prices
print("Creating Agency prices...")
prices['agency_monthly'] = run_stripe_cmd(
    f'stripe prices create --product="{agency_id}" --unit-amount=19900 --currency=usd --recurring.interval=month'
)
prices['agency_yearly'] = run_stripe_cmd(
    f'stripe prices create --product="{agency_id}" --unit-amount=199000 --currency=usd --recurring.interval=year'
)

# Check if all prices were created
failed = [k for k, v in prices.items() if not v]
if failed:
    print(f"\n❌ Failed to create: {', '.join(failed)}")
    exit(1)

print("\n" + "="*50)
print("✅ All prices created successfully in LIVE mode!")
print("="*50)
print("\n📋 Update your .env file with these price IDs:\n")

env_updates = {
    'STRIPE_PRICE_STARTER_MONTHLY': prices['starter_monthly']['id'],
    'STRIPE_PRICE_STARTER_YEARLY': prices['starter_yearly']['id'],
    'STRIPE_PRICE_PRO_MONTHLY': prices['pro_monthly']['id'],
    'STRIPE_PRICE_PRO_YEARLY': prices['pro_yearly']['id'],
    'STRIPE_PRICE_AGENCY_MONTHLY': prices['agency_monthly']['id'],
    'STRIPE_PRICE_AGENCY_YEARLY': prices['agency_yearly']['id'],
}

for key, value in env_updates.items():
    print(f"{key}={value}")

print("\n💡 Copy the lines above and replace them in your .env file")
print("   Then restart your backend!")

