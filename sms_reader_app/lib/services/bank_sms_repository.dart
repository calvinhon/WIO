import 'package:sqflite/sqflite.dart';
import '../models/bank_sms_model.dart';
import 'database_helper.dart';

class BankSmsRepository {
  final DatabaseHelper _databaseHelper = DatabaseHelper();

  // Insert a bank SMS message
  Future<int> insertBankSms(BankSms bankSms) async {
    final db = await _databaseHelper.database;
    
    try {
      return await db.insert(
        DatabaseHelper.bankSmsTable,
        bankSms.toMap(),
        conflictAlgorithm: ConflictAlgorithm.replace,
      );
    } catch (e) {
      print('Error inserting bank SMS: $e');
      rethrow;
    }
  }

  // Insert multiple bank SMS messages in a transaction
  Future<List<int>> insertMultipleBankSms(List<BankSms> bankSmsList) async {
    final db = await _databaseHelper.database;
    final List<int> ids = [];
    
    await db.transaction((txn) async {
      for (BankSms bankSms in bankSmsList) {
        try {
          final id = await txn.insert(
            DatabaseHelper.bankSmsTable,
            bankSms.toMap(),
            conflictAlgorithm: ConflictAlgorithm.replace,
          );
          ids.add(id);
        } catch (e) {
          print('Error inserting bank SMS in batch: $e');
          // Continue with other insertions
        }
      }
    });
    
    return ids;
  }

  // Get all bank SMS messages
  Future<List<BankSms>> getAllBankSms() async {
    final db = await _databaseHelper.database;
    
    try {
      final List<Map<String, dynamic>> maps = await db.query(
        DatabaseHelper.bankSmsTable,
        orderBy: '${DatabaseHelper.columnDateTime} DESC',
      );
      
      return List.generate(maps.length, (i) {
        return BankSms.fromMap(maps[i]);
      });
    } catch (e) {
      print('Error fetching all bank SMS: $e');
      return [];
    }
  }

  // Get bank SMS by ID
  Future<BankSms?> getBankSmsById(int id) async {
    final db = await _databaseHelper.database;
    
    try {
      final List<Map<String, dynamic>> maps = await db.query(
        DatabaseHelper.bankSmsTable,
        where: '${DatabaseHelper.columnId} = ?',
        whereArgs: [id],
      );
      
      if (maps.isNotEmpty) {
        return BankSms.fromMap(maps.first);
      }
      return null;
    } catch (e) {
      print('Error fetching bank SMS by ID: $e');
      return null;
    }
  }

  // Get bank SMS messages by date range
  Future<List<BankSms>> getBankSmsByDateRange(DateTime startDate, DateTime endDate) async {
    final db = await _databaseHelper.database;
    
    try {
      final List<Map<String, dynamic>> maps = await db.query(
        DatabaseHelper.bankSmsTable,
        where: '${DatabaseHelper.columnDateTime} BETWEEN ? AND ?',
        whereArgs: [startDate.millisecondsSinceEpoch, endDate.millisecondsSinceEpoch],
        orderBy: '${DatabaseHelper.columnDateTime} DESC',
      );
      
      return List.generate(maps.length, (i) {
        return BankSms.fromMap(maps[i]);
      });
    } catch (e) {
      print('Error fetching bank SMS by date range: $e');
      return [];
    }
  }

  // Get bank SMS messages by sender address
  Future<List<BankSms>> getBankSmsBySender(String address) async {
    final db = await _databaseHelper.database;
    
    try {
      final List<Map<String, dynamic>> maps = await db.query(
        DatabaseHelper.bankSmsTable,
        where: '${DatabaseHelper.columnAddress} LIKE ?',
        whereArgs: ['%$address%'],
        orderBy: '${DatabaseHelper.columnDateTime} DESC',
      );
      
      return List.generate(maps.length, (i) {
        return BankSms.fromMap(maps[i]);
      });
    } catch (e) {
      print('Error fetching bank SMS by sender: $e');
      return [];
    }
  }

  // Search bank SMS messages by content
  Future<List<BankSms>> searchBankSms(String searchTerm) async {
    final db = await _databaseHelper.database;
    
    try {
      final List<Map<String, dynamic>> maps = await db.query(
        DatabaseHelper.bankSmsTable,
        where: '${DatabaseHelper.columnBody} LIKE ? OR ${DatabaseHelper.columnAddress} LIKE ?',
        whereArgs: ['%$searchTerm%', '%$searchTerm%'],
        orderBy: '${DatabaseHelper.columnDateTime} DESC',
      );
      
      return List.generate(maps.length, (i) {
        return BankSms.fromMap(maps[i]);
      });
    } catch (e) {
      print('Error searching bank SMS: $e');
      return [];
    }
  }

  // Get recent bank SMS (last N messages)
  Future<List<BankSms>> getRecentBankSms({int limit = 50}) async {
    final db = await _databaseHelper.database;
    
    try {
      final List<Map<String, dynamic>> maps = await db.query(
        DatabaseHelper.bankSmsTable,
        orderBy: '${DatabaseHelper.columnDateTime} DESC',
        limit: limit,
      );
      
      return List.generate(maps.length, (i) {
        return BankSms.fromMap(maps[i]);
      });
    } catch (e) {
      print('Error fetching recent bank SMS: $e');
      return [];
    }
  }

  // Update a bank SMS message
  Future<int> updateBankSms(BankSms bankSms) async {
    final db = await _databaseHelper.database;
    
    try {
      return await db.update(
        DatabaseHelper.bankSmsTable,
        bankSms.toMap(),
        where: '${DatabaseHelper.columnId} = ?',
        whereArgs: [bankSms.id],
      );
    } catch (e) {
      print('Error updating bank SMS: $e');
      return 0;
    }
  }

  // Delete a bank SMS message
  Future<int> deleteBankSms(int id) async {
    final db = await _databaseHelper.database;
    
    try {
      return await db.delete(
        DatabaseHelper.bankSmsTable,
        where: '${DatabaseHelper.columnId} = ?',
        whereArgs: [id],
      );
    } catch (e) {
      print('Error deleting bank SMS: $e');
      return 0;
    }
  }

  // Delete all bank SMS messages
  Future<int> deleteAllBankSms() async {
    final db = await _databaseHelper.database;
    
    try {
      return await db.delete(DatabaseHelper.bankSmsTable);
    } catch (e) {
      print('Error deleting all bank SMS: $e');
      return 0;
    }
  }

  // Get bank SMS count
  Future<int> getBankSmsCount() async {
    final db = await _databaseHelper.database;
    
    try {
      final result = await db.rawQuery('SELECT COUNT(*) as count FROM ${DatabaseHelper.bankSmsTable}');
      return Sqflite.firstIntValue(result) ?? 0;
    } catch (e) {
      print('Error getting bank SMS count: $e');
      return 0;
    }
  }

  // Get bank SMS statistics
  Future<Map<String, dynamic>> getBankSmsStatistics() async {
    final db = await _databaseHelper.database;
    
    try {
      final totalResult = await db.rawQuery('SELECT COUNT(*) as total FROM ${DatabaseHelper.bankSmsTable}');
      final total = Sqflite.firstIntValue(totalResult) ?? 0;
      
      final senderResult = await db.rawQuery('''
        SELECT COUNT(DISTINCT ${DatabaseHelper.columnAddress}) as unique_senders 
        FROM ${DatabaseHelper.bankSmsTable}
      ''');
      final uniqueSenders = Sqflite.firstIntValue(senderResult) ?? 0;
      
      final avgConfidenceResult = await db.rawQuery('''
        SELECT AVG(${DatabaseHelper.columnConfidence}) as avg_confidence 
        FROM ${DatabaseHelper.bankSmsTable}
      ''');
      final avgConfidence = avgConfidenceResult.first['avg_confidence'] ?? 0.0;
      
      final oldestResult = await db.rawQuery('''
        SELECT MIN(${DatabaseHelper.columnDateTime}) as oldest 
        FROM ${DatabaseHelper.bankSmsTable}
      ''');
      final oldest = oldestResult.first['oldest'];
      
      final newestResult = await db.rawQuery('''
        SELECT MAX(${DatabaseHelper.columnDateTime}) as newest 
        FROM ${DatabaseHelper.bankSmsTable}
      ''');
      final newest = newestResult.first['newest'];
      
      return {
        'total': total,
        'uniqueSenders': uniqueSenders,
        'averageConfidence': avgConfidence,
        'oldestMessage': oldest != null ? DateTime.fromMillisecondsSinceEpoch(oldest as int) : null,
        'newestMessage': newest != null ? DateTime.fromMillisecondsSinceEpoch(newest as int) : null,
      };
    } catch (e) {
      print('Error getting bank SMS statistics: $e');
      return {
        'total': 0,
        'uniqueSenders': 0,
        'averageConfidence': 0.0,
        'oldestMessage': null,
        'newestMessage': null,
      };
    }
  }

  // Check if a bank SMS already exists (to avoid duplicates)
  Future<bool> bankSmsExists(String address, String body, DateTime dateTime) async {
    final db = await _databaseHelper.database;
    
    try {
      final result = await db.query(
        DatabaseHelper.bankSmsTable,
        where: '${DatabaseHelper.columnAddress} = ? AND ${DatabaseHelper.columnBody} = ? AND ${DatabaseHelper.columnDateTime} = ?',
        whereArgs: [address, body, dateTime.millisecondsSinceEpoch],
        limit: 1,
      );
      
      return result.isNotEmpty;
    } catch (e) {
      print('Error checking bank SMS existence: $e');
      return false;
    }
  }
} 