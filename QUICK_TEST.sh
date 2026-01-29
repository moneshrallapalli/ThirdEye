#!/bin/bash

# Quick test script to monitor your surveillance system
# Run this in a separate terminal while testing

echo "═══════════════════════════════════════════════════════════════"
echo "  🧪 SURVEILLANCE SYSTEM TEST MONITOR"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "✅ Backend running: $(curl -s http://localhost:8000/health | grep -q healthy && echo 'YES ✓' || echo 'NO ✗')"
echo "✅ Frontend running: $(curl -s http://localhost:3000 > /dev/null 2>&1 && echo 'YES ✓' || echo 'NO ✗')"
echo ""
echo "🧠 Claude Reasoning Agent:"
grep "Reasoning Agent" /tmp/sentintinel_backend.log | tail -1
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  📊 LIVE MONITORING - Press Ctrl+C to stop"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "Legend:"
echo "  🎯 = Baseline operations"
echo "  🚨 = Emergency/Alert events"
echo "  🧠 = Claude reasoning"
echo "  📸 = Camera operations"
echo "  ⚡ = Force/Override actions"
echo ""
echo "Watching logs..."
echo ""

# Monitor key events
tail -f /tmp/sentintinel_backend.log | grep --line-buffered -E "BASELINE|EMERGENCY|CLAUDE|query_confidence|FORCE|Camera.*started|query_match|person_present|ALERT TRIGGERED" | while read line; do
    # Color code different types of messages
    if echo "$line" | grep -q "BASELINE ESTABLISHED"; then
        echo "🎯 $line"
    elif echo "$line" | grep -q "EMERGENCY"; then
        echo "🚨 $line"
    elif echo "$line" | grep -q "CLAUDE"; then
        echo "🧠 $line"
    elif echo "$line" | grep -q "Camera.*started"; then
        echo "📸 $line"
    elif echo "$line" | grep -q "FORCE"; then
        echo "⚡ $line"
    elif echo "$line" | grep -q "ALERT TRIGGERED"; then
        echo "🚨 $line"
    else
        echo "$line"
    fi
done

