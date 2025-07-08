# SMS Reader & Analyzer App

A Flutter Android application that can read SMS messages from the user's device and send them to another program for analysis.

## Features

- ✅ Request and manage SMS reading permissions
- ✅ Read all SMS messages (inbox and sent)
- ✅ Display SMS messages in a clean, modern UI
- ✅ **🧠 Advanced NLP Analysis (NEW!)** - Sentiment analysis, categorization, entity extraction, keyword analysis
- ✅ **🔬 spaCy Integration** - Professional-grade ML-powered text analysis
- ✅ Send SMS data to external analysis server via HTTP API
- ✅ Configurable server URL
- ✅ Batch sending support for large datasets
- ✅ Real-time status updates and error handling
- ✅ **📊 Beautiful Analysis UI** - Interactive tabs with charts and visualizations

## Prerequisites

- Flutter SDK (3.8.1 or higher)
- Android SDK with API level 21+ (Android 5.0+)
- Android device or emulator for testing

## Setup Instructions

### 1. Clone and Setup

```bash
# Navigate to your project directory
cd sms_reader_app

# Install dependencies
flutter pub get
```

### 2. Android Configuration

The app requires specific Android permissions and configurations:

#### Permissions (Already configured in AndroidManifest.xml)
- `READ_SMS` - To read SMS messages
- `RECEIVE_SMS` - To receive SMS messages  
- `READ_PHONE_STATE` - To read phone state
- `INTERNET` - To send data to external server

#### Known Build Issues

Due to the telephony package being discontinued, you may encounter build issues. Here are the solutions:

**NDK Version Issue:**
If you get an NDK version error, add this to `android/app/build.gradle`:

```gradle
android {
    ndkVersion = "27.0.12077973"
    // ... rest of android configuration
}
```

**Namespace Issue:**
The telephony package may have namespace issues. Alternative solutions:
1. Use a different SMS reading approach
2. Fork and fix the telephony package
3. Use platform channels to read SMS directly

### 3. Alternative SMS Reading Implementation

If the telephony package doesn't work, you can implement SMS reading using platform channels:

Create `android/app/src/main/kotlin/MainActivity.kt`:

```kotlin
import android.Manifest
import android.content.pm.PackageManager
import android.database.Cursor
import android.net.Uri
import androidx.core.app.ActivityCompat
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

class MainActivity: FlutterActivity() {
    private val CHANNEL = "com.example.sms_reader/sms"

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, CHANNEL).setMethodCallHandler { call, result ->
            if (call.method == "getSmsMessages") {
                val messages = getSmsMessages()
                result.success(messages)
            } else {
                result.notImplemented()
            }
        }
    }

    private fun getSmsMessages(): List<Map<String, Any?>> {
        val messages = mutableListOf<Map<String, Any?>>()
        
        if (ActivityCompat.checkSelfPermission(this, Manifest.permission.READ_SMS) == PackageManager.PERMISSION_GRANTED) {
            val cursor: Cursor? = contentResolver.query(
                Uri.parse("content://sms"),
                null, null, null, "date DESC"
            )
            
            cursor?.use {
                while (it.moveToNext()) {
                    val message = mapOf(
                        "id" to it.getLong(it.getColumnIndex("_id")),
                        "address" to it.getString(it.getColumnIndex("address")),
                        "body" to it.getString(it.getColumnIndex("body")),
                        "date" to it.getLong(it.getColumnIndex("date")),
                        "type" to it.getInt(it.getColumnIndex("type"))
                    )
                    messages.add(message)
                }
            }
        }
        
        return messages
    }
}
```

## Usage

### 1. Launch the App

```bash
flutter run
```

### 2. Grant Permissions

1. Tap "Request Permission" to grant SMS reading permissions
2. Accept the permission dialog when prompted

### 3. Load SMS Messages

1. Tap "Load SMS" to read messages from your device
2. Messages will appear in the list below

### 4. Configure Server URL

1. Tap the settings icon (⚙️) in the app bar
2. Enter your analysis server URL (e.g., `http://your-server.com/api/sms`)
3. Tap "Save"

### 5. Send Data to Analyzer

1. After loading SMS messages, tap "Send to Analyzer"
2. The app will send all SMS data to your configured server

## API Endpoint Format

Your analysis server should accept POST requests with the following JSON format:

```json
{
  "timestamp": "2024-01-01T12:00:00.000Z",
  "device_info": {
    "platform": "android",
    "platform_version": "14",
    "app_version": "1.0.0"
  },
  "sms_count": 150,
  "sms_messages": [
    {
      "id": 1,
      "address": "+1234567890",
      "body": "Hello world",
      "date": 1641024000000,
      "type": "SmsType.MESSAGE_TYPE_INBOX",
      "read": true,
      "threadId": 1,
      "formattedDate": "2 days ago"
    }
  ]
}
```

## Project Structure

```
lib/
├── main.dart                      # Main app entry point
├── models/
│   └── sms_message_model.dart     # SMS message data model
└── services/
    ├── sms_service.dart           # SMS reading functionality
    └── data_sender_service.dart   # HTTP API communication
```

## Troubleshooting

### Build Issues

1. **Telephony package errors**: The package is discontinued. Consider using platform channels instead.
2. **NDK version conflicts**: Update `android/app/build.gradle` with the correct NDK version.
3. **Namespace errors**: Some packages may need namespace fixes in their build.gradle files.

### Permission Issues

1. Ensure all required permissions are in `AndroidManifest.xml`
2. Test on a physical device (emulator may have limitations)
3. Check Android settings to ensure SMS permission is granted

### Network Issues

1. Verify your server URL is correct and accessible
2. Check if your server accepts the expected JSON format
3. Test with a simple HTTP server or webhook.site for debugging

## Development Notes

- The app is designed for Android only (SMS reading is not available on iOS due to platform restrictions)
- The telephony package is discontinued but still functional for basic SMS reading
- Consider implementing platform channels for better control and future compatibility
- The app handles both inbox and sent messages
- All HTTP requests include device information and proper error handling

## License

This project is for educational and development purposes. Ensure you comply with local privacy laws when reading and transmitting SMS data.
