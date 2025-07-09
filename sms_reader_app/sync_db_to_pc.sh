#!/bin/bash

# Script to copy the app's SQLite database from an Android device to the local computer
# Usage: ./sync_db_to_pc.sh

PACKAGE_NAME="com.example.sms_reader_app"
DB_NAME="sms_reader.db"
DEVICE_DB_PATH="/data/data/$PACKAGE_NAME/databases/$DB_NAME"
SDCARD_DB_PATH="/sdcard/$DB_NAME"

# Get the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOCAL_DB_PATH="$SCRIPT_DIR/$DB_NAME"

set -e

echo "🔄 Copying database from protected app storage to SD card..."
adb shell run-as $PACKAGE_NAME cp $DEVICE_DB_PATH $SDCARD_DB_PATH

echo "⬇️  Pulling database from device to script directory..."
adb pull $SDCARD_DB_PATH "$LOCAL_DB_PATH"

echo "🧹 Cleaning up: removing database from SD card..."
adb shell rm $SDCARD_DB_PATH

echo "✅ Database sync complete! File saved as $LOCAL_DB_PATH" 