#!/bin/bash
# Create LIVE mode Stripe products and prices
# This script uses your LIVE API key from .env

set -e

# Load .env file
cd "$(dirname "$0")"
export $(grep -v '^#' .env | xargs)

# Check if Stripe CLI is installed
if ! command -v stripe &> /dev/null; then
    echo "❌ Stripe CLI not found. Install it:"
    echo "   brew install stripe/stripe-cli/stripe"
    exit 1
fi

# Check if we have a live key
if [[ ! "$STRIPE_SECRET_KEY" =~ ^sk_live_ ]]; then
    echo "❌ STRIPE_SECRET_KEY is not a LIVE key (should start with sk_live_)"
    exit 1
fi

echo "✅ Using LIVE Stripe key: ${STRIPE_SECRET_KEY:0:20}..."
echo ""

# Set the API key for this session
export STRIPE_API_KEY="$STRIPE_SECRET_KEY"

# Create products
echo "📦 Creating products..."

# Starter Product
echo "Creating Starter product..."
STARTER_PRODUCT_JSON=$(stripe products create \
  --name="Starter" \
  --description="Starter plan for Habexa" \
  --idempotency-key="starter-$(date +%s)" \
  --api-key="$STRIPE_SECRET_KEY" 2>&1)

STARTER_PRODUCT=$(echo "$STARTER_PRODUCT_JSON" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])" 2>/dev/null || echo "$STARTER_PRODUCT_JSON" | grep -oP '"id":\s*"\K[^"]+' | head -1)

echo "  ✅ Starter product: $STARTER_PRODUCT"

# Pro Product
echo "Creating Pro product..."
PRO_PRODUCT=$(stripe products create \
  --name="Pro" \
  --description="Pro plan for Habexa" \
  --idempotency-key="pro-$(date +%s)" \
  --api-key="$STRIPE_SECRET_KEY" \
  | grep -o '"id": "[^"]*' | cut -d'"' -f4)

echo "  ✅ Pro product: $PRO_PRODUCT"

# Agency Product
echo "Creating Agency product..."
AGENCY_PRODUCT=$(stripe products create \
  --name="Agency" \
  --description="Agency plan for Habexa" \
  --idempotency-key="agency-$(date +%s)" \
  --api-key="$STRIPE_SECRET_KEY" \
  | grep -o '"id": "[^"]*' | cut -d'"' -f4)

echo "  ✅ Agency product: $AGENCY_PRODUCT"

echo ""
echo "💰 Creating prices..."

# Starter Monthly - $29/month
echo "Creating Starter Monthly ($29/month)..."
STARTER_MONTHLY=$(stripe prices create \
  --product="$STARTER_PRODUCT" \
  --unit-amount=2900 \
  --currency=usd \
  --recurring[interval]=month \
  --idempotency-key="starter-monthly-$(date +%s)" \
  --api-key="$STRIPE_SECRET_KEY" \
  | grep -o '"id": "[^"]*' | cut -d'"' -f4)

echo "  ✅ Starter Monthly: $STARTER_MONTHLY"

# Starter Yearly - $290/year (save 17%)
echo "Creating Starter Yearly ($290/year)..."
STARTER_YEARLY=$(stripe prices create \
  --product="$STARTER_PRODUCT" \
  --unit-amount=29000 \
  --currency=usd \
  --recurring[interval]=year \
  --idempotency-key="starter-yearly-$(date +%s)" \
  --api-key="$STRIPE_SECRET_KEY" \
  | grep -o '"id": "[^"]*' | cut -d'"' -f4)

echo "  ✅ Starter Yearly: $STARTER_YEARLY"

# Pro Monthly - $79/month
echo "Creating Pro Monthly ($79/month)..."
PRO_MONTHLY=$(stripe prices create \
  --product="$PRO_PRODUCT" \
  --unit-amount=7900 \
  --currency=usd \
  --recurring[interval]=month \
  --idempotency-key="pro-monthly-$(date +%s)" \
  --api-key="$STRIPE_SECRET_KEY" \
  | grep -o '"id": "[^"]*' | cut -d'"' -f4)

echo "  ✅ Pro Monthly: $PRO_MONTHLY"

# Pro Yearly - $790/year (save 17%)
echo "Creating Pro Yearly ($790/year)..."
PRO_YEARLY=$(stripe prices create \
  --product="$PRO_PRODUCT" \
  --unit-amount=79000 \
  --currency=usd \
  --recurring[interval]=year \
  --idempotency-key="pro-yearly-$(date +%s)" \
  --api-key="$STRIPE_SECRET_KEY" \
  | grep -o '"id": "[^"]*' | cut -d'"' -f4)

echo "  ✅ Pro Yearly: $PRO_YEARLY"

# Agency Monthly - $199/month
echo "Creating Agency Monthly ($199/month)..."
AGENCY_MONTHLY=$(stripe prices create \
  --product="$AGENCY_PRODUCT" \
  --unit-amount=19900 \
  --currency=usd \
  --recurring[interval]=month \
  --idempotency-key="agency-monthly-$(date +%s)" \
  --api-key="$STRIPE_SECRET_KEY" \
  | grep -o '"id": "[^"]*' | cut -d'"' -f4)

echo "  ✅ Agency Monthly: $AGENCY_MONTHLY"

# Agency Yearly - $1990/year (save 17%)
echo "Creating Agency Yearly ($1990/year)..."
AGENCY_YEARLY=$(stripe prices create \
  --product="$AGENCY_PRODUCT" \
  --unit-amount=199000 \
  --currency=usd \
  --recurring[interval]=year \
  --idempotency-key="agency-yearly-$(date +%s)" \
  --api-key="$STRIPE_SECRET_KEY" \
  | grep -o '"id": "[^"]*' | cut -d'"' -f4)

echo "  ✅ Agency Yearly: $AGENCY_YEARLY"

echo ""
echo "=========================================="
echo "✅ All prices created in LIVE mode!"
echo "=========================================="
echo ""
echo "Update your .env file with these price IDs:"
echo ""
echo "STRIPE_PRICE_STARTER_MONTHLY=$STARTER_MONTHLY"
echo "STRIPE_PRICE_STARTER_YEARLY=$STARTER_YEARLY"
echo "STRIPE_PRICE_PRO_MONTHLY=$PRO_MONTHLY"
echo "STRIPE_PRICE_PRO_YEARLY=$PRO_YEARLY"
echo "STRIPE_PRICE_AGENCY_MONTHLY=$AGENCY_MONTHLY"
echo "STRIPE_PRICE_AGENCY_YEARLY=$AGENCY_YEARLY"
echo ""

