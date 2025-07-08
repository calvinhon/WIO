import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import '../models/sms_message_model.dart';

class DataSenderService {
  static const Duration _timeout = Duration(seconds: 30);

  /// Send SMS data to the analyzer server
  Future<bool> sendSmsData(List<SmsMessageModel> smsMessages, String serverUrl) async {
    try {
      // Validate URL
      if (serverUrl.trim().isEmpty) {
        throw Exception('Server URL cannot be empty');
      }

      Uri uri;
      try {
        uri = Uri.parse(serverUrl);
      } catch (e) {
        throw Exception('Invalid server URL format: $e');
      }

      // Prepare the data payload
      final payload = {
        'timestamp': DateTime.now().toIso8601String(),
        'device_info': await _getDeviceInfo(),
        'sms_count': smsMessages.length,
        'sms_messages': smsMessages.map((msg) => msg.toJson()).toList(),
      };

      // Send HTTP POST request
      final response = await http.post(
        uri,
        headers: {
          'Content-Type': 'application/json',
          'User-Agent': 'SMS-Reader-App/1.0',
        },
        body: jsonEncode(payload),
      ).timeout(_timeout);

      // Check response status
      if (response.statusCode >= 200 && response.statusCode < 300) {
        print('Successfully sent ${smsMessages.length} SMS messages to $serverUrl');
        return true;
      } else {
        print('Server responded with status ${response.statusCode}: ${response.body}');
        throw Exception('Server error: ${response.statusCode}');
      }
    } on SocketException catch (e) {
      throw Exception('Network error: Unable to connect to server ($e)');
    } on HttpException catch (e) {
      throw Exception('HTTP error: $e');
    } on FormatException catch (e) {
      throw Exception('Data format error: $e');
    } catch (e) {
      throw Exception('Failed to send SMS data: $e');
    }
  }

  /// Send SMS data in batches (useful for large datasets)
  Future<bool> sendSmsDataInBatches(
    List<SmsMessageModel> smsMessages, 
    String serverUrl, {
    int batchSize = 100,
    Function(int, int)? onProgress,
  }) async {
    try {
      final totalBatches = (smsMessages.length / batchSize).ceil();
      int successfulBatches = 0;

      for (int i = 0; i < smsMessages.length; i += batchSize) {
        final endIndex = (i + batchSize < smsMessages.length) 
            ? i + batchSize 
            : smsMessages.length;
        
        final batch = smsMessages.sublist(i, endIndex);
        final batchNumber = (i / batchSize).floor() + 1;

        try {
          await sendSmsData(batch, serverUrl);
          successfulBatches++;
          
          // Call progress callback if provided
          onProgress?.call(batchNumber, totalBatches);
          
          // Small delay between batches to avoid overwhelming the server
          if (batchNumber < totalBatches) {
            await Future.delayed(const Duration(milliseconds: 500));
          }
        } catch (e) {
          print('Failed to send batch $batchNumber: $e');
          // Continue with next batch even if one fails
        }
      }

      return successfulBatches == totalBatches;
    } catch (e) {
      throw Exception('Failed to send SMS data in batches: $e');
    }
  }

  /// Test server connectivity
  Future<bool> testServerConnection(String serverUrl) async {
    try {
      final uri = Uri.parse(serverUrl);
      final response = await http.head(uri).timeout(const Duration(seconds: 10));
      return response.statusCode < 400;
    } catch (e) {
      return false;
    }
  }

  /// Send a sample/test payload to the server
  Future<bool> sendTestData(String serverUrl) async {
    try {
      final testPayload = {
        'test': true,
        'timestamp': DateTime.now().toIso8601String(),
        'message': 'Test connection from SMS Reader App',
        'device_info': await _getDeviceInfo(),
      };

      final uri = Uri.parse(serverUrl);
      final response = await http.post(
        uri,
        headers: {
          'Content-Type': 'application/json',
          'User-Agent': 'SMS-Reader-App/1.0',
        },
        body: jsonEncode(testPayload),
      ).timeout(const Duration(seconds: 10));

      return response.statusCode >= 200 && response.statusCode < 300;
    } catch (e) {
      return false;
    }
  }

  /// Get basic device information to include in the payload
  Future<Map<String, dynamic>> _getDeviceInfo() async {
    return {
      'platform': Platform.operatingSystem,
      'platform_version': Platform.operatingSystemVersion,
      'app_version': '1.0.0',
      'dart_version': Platform.version,
    };
  }

  /// Create a summary of SMS data without the actual message content
  Map<String, dynamic> createSmsSummary(List<SmsMessageModel> smsMessages) {
    final Map<String, int> contactCounts = {};
    final Map<String, int> typeCounts = {};
    int totalCharacters = 0;

    for (final message in smsMessages) {
      // Count by contact
      final address = message.address ?? 'Unknown';
      contactCounts[address] = (contactCounts[address] ?? 0) + 1;
      
      // Count by type
      final type = message.type?.toString() ?? 'Unknown';
      typeCounts[type] = (typeCounts[type] ?? 0) + 1;
      
      // Count characters
      totalCharacters += message.body?.length ?? 0;
    }

    return {
      'timestamp': DateTime.now().toIso8601String(),
      'total_messages': smsMessages.length,
      'total_characters': totalCharacters,
      'average_message_length': smsMessages.isNotEmpty 
          ? (totalCharacters / smsMessages.length).round() 
          : 0,
      'unique_contacts': contactCounts.length,
      'message_types': typeCounts,
      'date_range': _getDateRange(smsMessages),
    };
  }

  Map<String, String?> _getDateRange(List<SmsMessageModel> smsMessages) {
    if (smsMessages.isEmpty) {
      return {'earliest': null, 'latest': null};
    }

    DateTime? earliest;
    DateTime? latest;

    for (final message in smsMessages) {
      if (message.date != null) {
        if (earliest == null || message.date!.isBefore(earliest)) {
          earliest = message.date;
        }
        if (latest == null || message.date!.isAfter(latest)) {
          latest = message.date;
        }
      }
    }

    return {
      'earliest': earliest?.toIso8601String(),
      'latest': latest?.toIso8601String(),
    };
  }
} 