#!/bin/bash
# Create LIVE mode Stripe products and prices
# Simpler version that outputs JSON for manual extraction

set -e

cd "$(dirname "$0")"
export $(grep -v '^#' .env | xargs)

if [[ ! "$STRIPE_SECRET_KEY" =~ ^sk_live_ ]]; then
    echo "❌ STRIPE_SECRET_KEY is not a LIVE key"
    exit 1
fi

export STRIPE_API_KEY="$STRIPE_SECRET_KEY"

echo "✅ Using LIVE Stripe key"
echo ""

# Create products and prices, output full JSON
echo "📦 Creating Starter product and prices..."
echo ""
stripe products create \
  --name="Starter" \
  --description="Starter plan - $29/month, $290/year" \
  --api-key="$STRIPE_SECRET_KEY"

echo ""
echo "💰 Creating Starter prices..."
echo ""

echo "Starter Monthly ($29/month):"
stripe prices create \
  --product="Starter" \
  --unit-amount=2900 \
  --currency=usd \
  --recurring[interval]=month \
  --api-key="$STRIPE_SECRET_KEY"

echo ""
echo "Starter Yearly ($290/year):"
stripe prices create \
  --product="Starter" \
  --unit-amount=29000 \
  --currency=usd \
  --recurring[interval]=year \
  --api-key="$STRIPE_SECRET_KEY"

echo ""
echo "📦 Creating Pro product and prices..."
echo ""
stripe products create \
  --name="Pro" \
  --description="Pro plan - $79/month, $790/year" \
  --api-key="$STRIPE_SECRET_KEY"

echo ""
echo "💰 Creating Pro prices..."
echo ""

echo "Pro Monthly ($79/month):"
stripe prices create \
  --product="Pro" \
  --unit-amount=7900 \
  --currency=usd \
  --recurring[interval]=month \
  --api-key="$STRIPE_SECRET_KEY"

echo ""
echo "Pro Yearly ($790/year):"
stripe prices create \
  --product="Pro" \
  --unit-amount=79000 \
  --currency=usd \
  --recurring[interval]=year \
  --api-key="$STRIPE_SECRET_KEY"

echo ""
echo "📦 Creating Agency product and prices..."
echo ""
stripe products create \
  --name="Agency" \
  --description="Agency plan - $199/month, $1990/year" \
  --api-key="$STRIPE_SECRET_KEY"

echo ""
echo "💰 Creating Agency prices..."
echo ""

echo "Agency Monthly ($199/month):"
stripe prices create \
  --product="Agency" \
  --unit-amount=19900 \
  --currency=usd \
  --recurring[interval]=month \
  --api-key="$STRIPE_SECRET_KEY"

echo ""
echo "Agency Yearly ($1990/year):"
stripe prices create \
  --product="Agency" \
  --unit-amount=199000 \
  --currency=usd \
  --recurring[interval]=year \
  --api-key="$STRIPE_SECRET_KEY"

echo ""
echo "=========================================="
echo "✅ Done! Look for 'id' fields in the JSON above"
echo "Copy the price IDs and update your .env file"
echo "=========================================="

