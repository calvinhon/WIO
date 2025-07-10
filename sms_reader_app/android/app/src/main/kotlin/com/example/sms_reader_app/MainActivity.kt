package com.example.sms_reader_app

import android.Manifest
import android.content.pm.PackageManager
import android.database.Cursor
import android.net.Uri
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel
import kotlinx.coroutines.*

class MainActivity: FlutterActivity() {
    private val SMS_CHANNEL = "com.example.sms_reader/sms"
    private val NLP_CHANNEL = "com.example.sms_reader/nlp"
    private val SMS_PERMISSION_REQUEST = 100
    
    private lateinit var nlpProcessor: NlpProcessor

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        
        nlpProcessor = NlpProcessor(this)
        
        // SMS Channel
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, SMS_CHANNEL).setMethodCallHandler { call, result ->
            when (call.method) {
                "getSmsMessages" -> {
                    if (checkSmsPermission()) {
                        val messages = getSmsMessages()
                        result.success(messages)
                    } else {
                        result.error("PERMISSION_DENIED", "SMS permission not granted", null)
                    }
                }
                "requestSmsPermission" -> {
                    requestSmsPermission()
                    result.success(checkSmsPermission())
                }
                "checkSmsPermission" -> {
                    result.success(checkSmsPermission())
                }
                else -> {
                    result.notImplemented()
                }
            }
        }
        
        // NLP Channel
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, NLP_CHANNEL).setMethodCallHandler { call, result ->
            when (call.method) {
                "processWithSpacy" -> {
                    try {
                        val messages = call.argument<List<Map<String, Any?>>>("messages")
                        if (messages != null) {
                            GlobalScope.launch(Dispatchers.IO) {
                                try {
                                    val nlpResult = nlpProcessor.processWithSpacy(messages)
                                    withContext(Dispatchers.Main) {
                                        result.success(nlpResult)
                                    }
                                } catch (e: Exception) {
                                    withContext(Dispatchers.Main) {
                                        result.error("NLP_ERROR", "Failed to process with spaCy: ${e.message}", null)
                                    }
                                }
                            }
                        } else {
                            result.error("INVALID_ARGUMENTS", "Messages list is required", null)
                        }
                    } catch (e: Exception) {
                        result.error("NLP_ERROR", "NLP processing failed: ${e.message}", null)
                    }
                }
                else -> {
                    result.notImplemented()
                }
            }
        }
    }

    private fun checkSmsPermission(): Boolean {
        return ContextCompat.checkSelfPermission(this, Manifest.permission.READ_SMS) == PackageManager.PERMISSION_GRANTED
    }

    private fun requestSmsPermission() {
        ActivityCompat.requestPermissions(
            this,
            arrayOf(Manifest.permission.READ_SMS, Manifest.permission.READ_PHONE_STATE),
            SMS_PERMISSION_REQUEST
        )
    }

    private fun getSmsMessages(): List<Map<String, Any?>> {
        val messages = mutableListOf<Map<String, Any?>>()
        
        if (!checkSmsPermission()) {
            return messages
        }

        try {
            // Get inbox messages
            val inboxCursor: Cursor? = contentResolver.query(
                Uri.parse("content://sms/inbox"),
                arrayOf("_id", "address", "body", "date", "type", "read", "thread_id"),
                null, null, "date DESC LIMIT 500"
            )
            
            inboxCursor?.use { cursor ->
                while (cursor.moveToNext()) {
                    val message = createMessageMap(cursor, "inbox")
                    messages.add(message)
                }
            }

            // Get sent messages
            val sentCursor: Cursor? = contentResolver.query(
                Uri.parse("content://sms/sent"),
                arrayOf("_id", "address", "body", "date", "type", "read", "thread_id"),
                null, null, "date DESC LIMIT 500"
            )
            
            sentCursor?.use { cursor ->
                while (cursor.moveToNext()) {
                    val message = createMessageMap(cursor, "sent")
                    messages.add(message)
                }
            }

            // Sort all messages by date (newest first)
            messages.sortByDescending { it["date"] as? Long ?: 0L }
            
        } catch (e: Exception) {
            // Log error but don't crash
            e.printStackTrace()
        }
        
        return messages.take(1000) // Limit to 1000 most recent messages
    }

    private fun createMessageMap(cursor: Cursor, messageType: String): Map<String, Any?> {
        return mapOf(
            "id" to cursor.getLong(cursor.getColumnIndexOrThrow("_id")),
            "address" to cursor.getString(cursor.getColumnIndexOrThrow("address")),
            "body" to cursor.getString(cursor.getColumnIndexOrThrow("body")),
            "date" to cursor.getLong(cursor.getColumnIndexOrThrow("date")),
            "type" to messageType,
            "read" to (cursor.getInt(cursor.getColumnIndexOrThrow("read")) == 1),
            "threadId" to cursor.getLong(cursor.getColumnIndexOrThrow("thread_id"))
        )
    }
}
