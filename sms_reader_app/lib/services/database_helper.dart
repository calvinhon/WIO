import 'dart:async';
import 'package:sqflite/sqflite.dart';
import 'package:path/path.dart';

class DatabaseHelper {
  static final DatabaseHelper _instance = DatabaseHelper._internal();
  factory DatabaseHelper() => _instance;
  DatabaseHelper._internal();

  static Database? _database;

  // Database configuration
  static const String _databaseName = 'sms_reader.db';
  static const int _databaseVersion = 1;

  // Table names
  static const String bankSmsTable = 'bank_sms';

  // Bank SMS table columns
  static const String columnId = 'id';
  static const String columnAddress = 'address';
  static const String columnBody = 'body';
  static const String columnDateTime = 'dateTime';
  static const String columnCategory = 'category';
  static const String columnConfidence = 'confidence';
  static const String columnIndicators = 'indicators';
  static const String columnCreatedAt = 'createdAt';

  // Get database instance
  Future<Database> get database async {
    if (_database != null) return _database!;
    _database = await _initDatabase();
    return _database!;
  }

  // Initialize database
  Future<Database> _initDatabase() async {
    String path = join(await getDatabasesPath(), _databaseName);
    
    return await openDatabase(
      path,
      version: _databaseVersion,
      onCreate: _onCreate,
      onUpgrade: _onUpgrade,
    );
  }

  // Create tables
  Future<void> _onCreate(Database db, int version) async {
    await db.execute('''
      CREATE TABLE $bankSmsTable (
        $columnId INTEGER PRIMARY KEY AUTOINCREMENT,
        $columnAddress TEXT NOT NULL,
        $columnBody TEXT NOT NULL,
        $columnDateTime INTEGER NOT NULL,
        $columnCategory TEXT NOT NULL,
        $columnConfidence REAL NOT NULL,
        $columnIndicators TEXT,
        $columnCreatedAt INTEGER NOT NULL,
        UNIQUE($columnAddress, $columnBody, $columnDateTime)
      )
    ''');

    // Create indices for better query performance
    await db.execute('''
      CREATE INDEX idx_bank_sms_date ON $bankSmsTable($columnDateTime)
    ''');
    
    await db.execute('''
      CREATE INDEX idx_bank_sms_address ON $bankSmsTable($columnAddress)
    ''');
    
    await db.execute('''
      CREATE INDEX idx_bank_sms_category ON $bankSmsTable($columnCategory)
    ''');
  }

  // Handle database upgrades
  Future<void> _onUpgrade(Database db, int oldVersion, int newVersion) async {
    // Handle database schema migrations here when version changes
    if (oldVersion < newVersion) {
      // Example migration logic
      // if (oldVersion == 1 && newVersion == 2) {
      //   await db.execute('ALTER TABLE $bankSmsTable ADD COLUMN new_column TEXT');
      // }
    }
  }

  // Close database
  Future<void> close() async {
    final db = await database;
    await db.close();
    _database = null;
  }

  // Delete database (for testing/reset purposes)
  Future<void> deleteDatabase() async {
    String path = join(await getDatabasesPath(), _databaseName);
    await databaseFactory.deleteDatabase(path);
    _database = null;
  }

  // Get database information
  Future<Map<String, dynamic>> getDatabaseInfo() async {
    final db = await database;
    final result = await db.rawQuery('PRAGMA database_list');
    final tableCount = await db.rawQuery(
      "SELECT COUNT(*) as count FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    );
    final bankSmsCount = await db.rawQuery('SELECT COUNT(*) as count FROM $bankSmsTable');
    
    // Get count for other tables if they exist
    final Map<String, int> tableCounts = {};
    final tablesResult = await db.rawQuery(
      "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    );
    
    for (final table in tablesResult) {
      final tableName = table['name'] as String;
      final countResult = await db.rawQuery('SELECT COUNT(*) as count FROM $tableName');
      tableCounts[tableName] = countResult.first['count'] as int;
    }
    
    return {
      'path': result.first['file'],
      'version': _databaseVersion,
      'tables': tableCount.first['count'],
      'bankSmsCount': bankSmsCount.first['count'],
      'tableCounts': tableCounts,
    };
  }

  // Get all table names
  Future<List<String>> getAllTableNames() async {
    final db = await database;
    final tablesResult = await db.rawQuery(
      "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    );
    return tablesResult.map((row) => row['name'] as String).toList();
  }

  // Get table schema
  Future<List<Map<String, dynamic>>> getTableSchema(String tableName) async {
    final db = await database;
    return await db.rawQuery("PRAGMA table_info($tableName)");
  }

  // Get table data with limit
  Future<List<Map<String, dynamic>>> getTableData(String tableName, {int limit = 100}) async {
    final db = await database;
    return await db.rawQuery("SELECT * FROM $tableName LIMIT $limit");
  }

  // Get table row count
  Future<int> getTableRowCount(String tableName) async {
    final db = await database;
    final result = await db.rawQuery("SELECT COUNT(*) as count FROM $tableName");
    return result.first['count'] as int;
  }
} 