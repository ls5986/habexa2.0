#!/bin/bash
# Poll job results for analysis
# Usage: ./poll_job_results.sh JOB_ID [BEARER_TOKEN]

JOB_ID="${1:-fa52c1db-2ed5-4b3b-ae2c-12aa9c6cb933}"
BEARER_TOKEN="${2:-$BEARER_TOKEN}"

if [ -z "$BEARER_TOKEN" ]; then
    echo "❌ Error: BEARER_TOKEN not set"
    echo "Usage: BEARER_TOKEN=your_token ./poll_job_results.sh [JOB_ID]"
    exit 1
fi

BACKEND_URL="https://habexa-backend-w5u5.onrender.com"

echo "📊 Polling job: $JOB_ID"
echo ""

# Poll until complete (max 60 seconds)
MAX_ATTEMPTS=12
ATTEMPT=0

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    ATTEMPT=$((ATTEMPT + 1))
    
    echo "⏳ Attempt $ATTEMPT/$MAX_ATTEMPTS..."
    
    RESPONSE=$(curl -s -X GET "$BACKEND_URL/api/v1/jobs/$JOB_ID" \
        -H "Authorization: Bearer $BEARER_TOKEN")
    
    STATUS=$(echo "$RESPONSE" | jq -r '.status // "unknown"')
    
    echo "Status: $STATUS"
    
    if [ "$STATUS" = "completed" ]; then
        echo ""
        echo "✅ Job completed!"
        echo ""
        echo "$RESPONSE" | jq '.'
        break
    elif [ "$STATUS" = "failed" ]; then
        echo ""
        echo "❌ Job failed!"
        echo ""
        echo "$RESPONSE" | jq '.'
        break
    fi
    
    # Show progress if available
    PROGRESS=$(echo "$RESPONSE" | jq -r '.progress // 0')
    if [ "$PROGRESS" != "null" ] && [ "$PROGRESS" != "0" ]; then
        echo "Progress: ${PROGRESS}%"
    fi
    
    # Wait 5 seconds before next poll
    if [ $ATTEMPT -lt $MAX_ATTEMPTS ]; then
        sleep 5
    fi
done

if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
    echo ""
    echo "⏰ Timeout: Job still processing after $MAX_ATTEMPTS attempts"
    echo "Check manually: curl -X GET '$BACKEND_URL/api/v1/jobs/$JOB_ID' -H 'Authorization: Bearer $BEARER_TOKEN'"
fi

