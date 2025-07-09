#!/bin/bash

# SMS Reader App Database Sync Script
# This script copies the latest SQLite database from your Android device to your MacBook

echo "🔄 SMS Reader Database Sync"
echo "=============================="

# Set ADB path
export PATH="/Users/aserebry/Library/Android/sdk/platform-tools:$PATH"

# Check if device is connected
if ! adb devices | grep -q "device$"; then
    echo "❌ No Android device/emulator connected"
    echo "   Please ensure your emulator is running and connected"
    exit 1
fi

echo "✅ Android device connected"

# Get the script directory (project root)
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_root="$script_dir"

# Create backup directory in project
backup_dir="$project_root/database_backups"
mkdir -p "$backup_dir"

# Create timestamped filename
timestamp=$(date "+%Y%m%d_%H%M%S")
db_file="$backup_dir/sms_reader_$timestamp.db"
latest_file="$project_root/sms_reader_latest.db"

echo "📱 Copying database from Android device..."

# Method 1: Try direct copy
if adb shell run-as com.example.sms_reader_app cat /data/data/com.example.sms_reader_app/databases/sms_reader.db > "$db_file" 2>/dev/null; then
    echo "✅ Database copied successfully"
    
    # Also create a 'latest' version for easy access
    cp "$db_file" "$latest_file"
    
    # Check if the database has content
    count=$(sqlite3 "$db_file" "SELECT COUNT(*) FROM bank_sms;" 2>/dev/null)
    
    if [ "$count" -gt 0 ]; then
        echo "📊 Found $count bank SMS messages in database"
        echo "📁 Files created:"
        echo "   - Timestamped: $db_file"
        echo "   - Latest: $latest_file"
        
        echo ""
        echo "🔍 Quick database stats:"
        sqlite3 "$db_file" "
        SELECT 
            'Total Messages: ' || COUNT(*) as info
        FROM bank_sms
        UNION ALL
        SELECT 
            'Unique Senders: ' || COUNT(DISTINCT address)
        FROM bank_sms
        UNION ALL
        SELECT 
            'Avg Confidence: ' || ROUND(AVG(confidence * 100), 1) || '%'
        FROM bank_sms;"
        
        echo ""
        echo "📝 Recent messages:"
        sqlite3 "$db_file" "
        SELECT 
            address || ' | ' || ROUND(confidence * 100) || '% | ' || 
            datetime(dateTime/1000, 'unixepoch', 'localtime') || ' | ' ||
            substr(body, 1, 50) || '...' as message_info
        FROM bank_sms 
        ORDER BY dateTime DESC 
        LIMIT 3;"
        
    else
        echo "⚠️  Database is empty (0 messages)"
        echo "   This might mean:"
        echo "   1. No bank SMS have been categorized yet"
        echo "   2. The database was reset"
        echo "   3. There's an issue with database persistence"
    fi
    
    echo ""
    echo "🎯 To open the database:"
    echo "   - Double-click: $latest_file"
    echo "   - Command line: sqlite3 '$latest_file'"
    echo "   - DB Browser: Open '$latest_file'"
    
else
    echo "❌ Failed to copy database"
    echo "   The app might not be installed or the database doesn't exist yet"
    exit 1
fi

echo ""
echo "✨ Database sync complete!" 