import 'package:flutter/services.dart';
import '../models/sms_message_model.dart';

class SmsService {
  static const MethodChannel _channel = MethodChannel('com.example.sms_reader/sms');

  /// Check if SMS permission is granted
  Future<bool> checkSmsPermission() async {
    try {
      final bool hasPermission = await _channel.invokeMethod('checkSmsPermission');
      return hasPermission;
    } catch (e) {
      print('Error checking SMS permission: $e');
      return false;
    }
  }

  /// Request SMS permission
  Future<bool> requestSmsPermission() async {
    try {
      final bool hasPermission = await _channel.invokeMethod('requestSmsPermission');
      return hasPermission;
    } catch (e) {
      print('Error requesting SMS permission: $e');
      return false;
    }
  }

  /// Get all SMS messages from the device
  Future<List<SmsMessageModel>> getAllSmsMessages({int? limit}) async {
    try {
      final List<dynamic> messagesData = await _channel.invokeMethod('getSmsMessages');
      
      List<SmsMessageModel> messages = messagesData.map((data) {
        return SmsMessageModel.fromPlatformMap(Map<String, dynamic>.from(data));
      }).toList();

      // Apply limit if specified
      if (limit != null && limit > 0) {
        messages = messages.take(limit).toList();
      }

      return messages;
    } catch (e) {
      throw Exception('Failed to read SMS messages: $e');
    }
  }

  /// Get SMS messages from a specific contact
  Future<List<SmsMessageModel>> getSmsFromContact(String address) async {
    try {
      final allMessages = await getAllSmsMessages();
      return allMessages.where((msg) => msg.address == address).toList();
    } catch (e) {
      throw Exception('Failed to read SMS messages from $address: $e');
    }
  }

  /// Get SMS messages from the last N days
  Future<List<SmsMessageModel>> getRecentSmsMessages(int days) async {
    try {
      final DateTime cutoffDate = DateTime.now().subtract(Duration(days: days));
      final cutoffTimestamp = cutoffDate.millisecondsSinceEpoch;

      final allMessages = await getAllSmsMessages();
      return allMessages.where((msg) {
        return msg.date != null && msg.date!.millisecondsSinceEpoch >= cutoffTimestamp;
      }).toList();
    } catch (e) {
      throw Exception('Failed to read recent SMS messages: $e');
    }
  }

  /// Get SMS statistics
  Future<Map<String, dynamic>> getSmsStatistics() async {
    try {
      final messages = await getAllSmsMessages();
      
      final Map<String, int> contactCounts = {};
      int totalInbox = 0;
      int totalSent = 0;
      
      for (final message in messages) {
        // Count by contact
        final address = message.address ?? 'Unknown';
        contactCounts[address] = (contactCounts[address] ?? 0) + 1;
        
        // Count by type
        if (message.type == 'inbox') {
          totalInbox++;
        } else if (message.type == 'sent') {
          totalSent++;
        }
      }

      return {
        'totalMessages': messages.length,
        'inboxMessages': totalInbox,
        'sentMessages': totalSent,
        'uniqueContacts': contactCounts.length,
        'topContacts': _getTopContacts(contactCounts, 5),
      };
    } catch (e) {
      throw Exception('Failed to get SMS statistics: $e');
    }
  }

  List<Map<String, dynamic>> _getTopContacts(Map<String, int> contactCounts, int limit) {
    final sortedContacts = contactCounts.entries.toList()
      ..sort((a, b) => b.value.compareTo(a.value));
    
    return sortedContacts
        .take(limit)
        .map((entry) => {
              'address': entry.key,
              'count': entry.value,
            })
        .toList();
  }
} 