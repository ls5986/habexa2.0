#!/bin/bash

# Habexa Stripe Products & Prices Setup Script
# This script creates all products and prices, then outputs the .env format

echo "🚀 Creating Habexa Stripe Products & Prices..."
echo ""

# Check if jq is installed (needed for JSON parsing)
if ! command -v jq &> /dev/null; then
    echo "⚠️  jq is not installed. Installing via brew..."
    brew install jq
fi

# Check if stripe CLI is installed
if ! command -v stripe &> /dev/null; then
    echo "❌ Stripe CLI is not installed!"
    echo "Install it with: brew install stripe/stripe-cli/stripe"
    exit 1
fi

echo "Creating Starter Product..."
STARTER_PROD=$(stripe products create \
  --name="Habexa Starter" \
  --description="3 Telegram channels, 100 analyses/month, 10 suppliers" 2>/dev/null | jq -r '.id')

if [ -z "$STARTER_PROD" ] || [ "$STARTER_PROD" == "null" ]; then
    echo "❌ Failed to create Starter product"
    exit 1
fi

echo "✅ Starter Product: $STARTER_PROD"

STARTER_MONTHLY=$(stripe prices create \
  --product="$STARTER_PROD" \
  --unit-amount=2900 \
  --currency=usd \
  --recurring.interval=month \
  --lookup-key=starter_monthly 2>/dev/null | jq -r '.id')

STARTER_YEARLY=$(stripe prices create \
  --product="$STARTER_PROD" \
  --unit-amount=29000 \
  --currency=usd \
  --recurring.interval=year \
  --lookup-key=starter_yearly 2>/dev/null | jq -r '.id')

echo "✅ Starter Monthly: $STARTER_MONTHLY"
echo "✅ Starter Yearly: $STARTER_YEARLY"
echo ""

echo "Creating Pro Product..."
PRO_PROD=$(stripe products create \
  --name="Habexa Pro" \
  --description="10 Telegram channels, 500 analyses/month, 50 suppliers" 2>/dev/null | jq -r '.id')

if [ -z "$PRO_PROD" ] || [ "$PRO_PROD" == "null" ]; then
    echo "❌ Failed to create Pro product"
    exit 1
fi

echo "✅ Pro Product: $PRO_PROD"

PRO_MONTHLY=$(stripe prices create \
  --product="$PRO_PROD" \
  --unit-amount=7900 \
  --currency=usd \
  --recurring.interval=month \
  --lookup-key=pro_monthly 2>/dev/null | jq -r '.id')

PRO_YEARLY=$(stripe prices create \
  --product="$PRO_PROD" \
  --unit-amount=79000 \
  --currency=usd \
  --recurring.interval=year \
  --lookup-key=pro_yearly 2>/dev/null | jq -r '.id')

echo "✅ Pro Monthly: $PRO_MONTHLY"
echo "✅ Pro Yearly: $PRO_YEARLY"
echo ""

echo "Creating Agency Product..."
AGENCY_PROD=$(stripe products create \
  --name="Habexa Agency" \
  --description="Unlimited channels, analyses, and suppliers" 2>/dev/null | jq -r '.id')

if [ -z "$AGENCY_PROD" ] || [ "$AGENCY_PROD" == "null" ]; then
    echo "❌ Failed to create Agency product"
    exit 1
fi

echo "✅ Agency Product: $AGENCY_PROD"

AGENCY_MONTHLY=$(stripe prices create \
  --product="$AGENCY_PROD" \
  --unit-amount=19900 \
  --currency=usd \
  --recurring.interval=month \
  --lookup-key=agency_monthly 2>/dev/null | jq -r '.id')

AGENCY_YEARLY=$(stripe prices create \
  --product="$AGENCY_PROD" \
  --unit-amount=199000 \
  --currency=usd \
  --recurring.interval=year \
  --lookup-key=agency_yearly 2>/dev/null | jq -r '.id')

echo "✅ Agency Monthly: $AGENCY_MONTHLY"
echo "✅ Agency Yearly: $AGENCY_YEARLY"
echo ""

echo "============================================"
echo "✅ All products and prices created!"
echo "============================================"
echo ""
echo "Copy these to your .env file:"
echo ""
echo "# Stripe Price IDs"
echo "STRIPE_PRICE_STARTER_MONTHLY=$STARTER_MONTHLY"
echo "STRIPE_PRICE_STARTER_YEARLY=$STARTER_YEARLY"
echo "STRIPE_PRICE_PRO_MONTHLY=$PRO_MONTHLY"
echo "STRIPE_PRICE_PRO_YEARLY=$PRO_YEARLY"
echo "STRIPE_PRICE_AGENCY_MONTHLY=$AGENCY_MONTHLY"
echo "STRIPE_PRICE_AGENCY_YEARLY=$AGENCY_YEARLY"
echo ""
echo "============================================"

