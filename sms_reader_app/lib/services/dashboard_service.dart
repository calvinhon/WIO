import 'database_helper.dart';

class DashboardService {
  final DatabaseHelper _databaseHelper = DatabaseHelper();

  // Get all cards data
  Future<List<Map<String, dynamic>>> getCards() async {
    try {
      final db = await _databaseHelper.database;
      final result = await db.query('cards', orderBy: 'card_id');
      return result;
    } catch (e) {
      print('Error fetching cards: $e');
      return [];
    }
  }

  // Get all payments data
  Future<List<Map<String, dynamic>>> getPayments() async {
    try {
      final db = await _databaseHelper.database;
      final result = await db.query('payments', orderBy: 'payment_date DESC');
      return result;
    } catch (e) {
      print('Error fetching payments: $e');
      return [];
    }
  }

  // Get payments for a specific card
  Future<List<Map<String, dynamic>>> getPaymentsForCard(String cardId) async {
    try {
      final db = await _databaseHelper.database;
      final result = await db.query(
        'payments',
        where: 'card_id = ?',
        whereArgs: [cardId],
        orderBy: 'payment_date DESC',
      );
      return result;
    } catch (e) {
      print('Error fetching payments for card $cardId: $e');
      return [];
    }
  }

  // Get cards with their payment counts and totals
  Future<List<Map<String, dynamic>>> getCardsWithPaymentSummary() async {
    try {
      final db = await _databaseHelper.database;
      final result = await db.rawQuery('''
        SELECT 
          c.card_id,
          c.latest_due_date,
          c.latest_total_amount,
          c.latest_min_amount,
          c.total_payments_made,
          c.updated_at,
          COUNT(p.payment_id) as payment_count,
          COALESCE(SUM(p.amount), 0) as total_paid,
          COALESCE(MAX(p.payment_date), '') as last_payment_date
        FROM cards c
        LEFT JOIN payments p ON c.card_id = p.card_id
        GROUP BY c.card_id, c.latest_due_date, c.latest_total_amount, c.latest_min_amount, c.total_payments_made, c.updated_at
        ORDER BY c.card_id
      ''');
      return result;
    } catch (e) {
      print('Error fetching cards with payment summary: $e');
      return [];
    }
  }

  // Get monthly payment totals
  Future<List<Map<String, dynamic>>> getMonthlyPaymentTotals() async {
    try {
      final db = await _databaseHelper.database;
      final result = await db.rawQuery('''
        SELECT 
          substr(payment_date, 4, 2) || '/' || substr(payment_date, 7, 2) as month_year,
          SUM(amount) as total_amount,
          COUNT(*) as payment_count
        FROM payments
        WHERE payment_date IS NOT NULL AND payment_date != ''
        GROUP BY substr(payment_date, 4, 2), substr(payment_date, 7, 2)
        ORDER BY substr(payment_date, 7, 2), substr(payment_date, 4, 2)
      ''');
      return result;
    } catch (e) {
      print('Error fetching monthly payment totals: $e');
      return [];
    }
  }

  // Get payment amounts by card
  Future<List<Map<String, dynamic>>> getPaymentsByCard() async {
    try {
      final db = await _databaseHelper.database;
      final result = await db.rawQuery('''
        SELECT 
          card_id,
          SUM(amount) as total_amount,
          COUNT(*) as payment_count,
          AVG(amount) as avg_amount,
          MIN(amount) as min_amount,
          MAX(amount) as max_amount
        FROM payments
        GROUP BY card_id
        ORDER BY total_amount DESC
      ''');
      return result;
    } catch (e) {
      print('Error fetching payments by card: $e');
      return [];
    }
  }

  // Get recent payments (last 10)
  Future<List<Map<String, dynamic>>> getRecentPayments({int limit = 10}) async {
    try {
      final db = await _databaseHelper.database;
      final result = await db.rawQuery('''
        SELECT 
          p.payment_id,
          p.card_id,
          p.amount,
          p.payment_date,
          p.description,
          p.created_at
        FROM payments p
        ORDER BY p.created_at DESC
        LIMIT ?
      ''', [limit]);
      return result;
    } catch (e) {
      print('Error fetching recent payments: $e');
      return [];
    }
  }

  // Get dashboard statistics
  Future<Map<String, dynamic>> getDashboardStats() async {
    try {
      final db = await _databaseHelper.database;
      
      // Get total cards
      final cardsResult = await db.rawQuery('SELECT COUNT(*) as count FROM cards');
      final totalCards = cardsResult.first['count'] as int;
      
      // Get total payments
      final paymentsResult = await db.rawQuery('SELECT COUNT(*) as count FROM payments');
      final totalPayments = paymentsResult.first['count'] as int;
      
      // Get total amount due
      final totalDueResult = await db.rawQuery('SELECT SUM(latest_total_amount) as total FROM cards');
      final totalDue = (totalDueResult.first['total'] as double?) ?? 0.0;
      
      // Get total amount paid
      final totalPaidResult = await db.rawQuery('SELECT SUM(amount) as total FROM payments');
      final totalPaid = (totalPaidResult.first['total'] as double?) ?? 0.0;
      
      // Get average payment amount
      final avgPaymentResult = await db.rawQuery('SELECT AVG(amount) as avg FROM payments');
      final avgPayment = (avgPaymentResult.first['avg'] as double?) ?? 0.0;
      
      // Get cards with overdue payments (assuming due date format is DD.MM.YY)
      final overdueResult = await db.rawQuery('''
        SELECT COUNT(*) as count FROM cards 
        WHERE latest_due_date IS NOT NULL 
        AND latest_due_date != ''
        AND latest_total_amount > total_payments_made
      ''');
      final overdueCards = overdueResult.first['count'] as int;
      
      return {
        'totalCards': totalCards,
        'totalPayments': totalPayments,
        'totalDue': totalDue,
        'totalPaid': totalPaid,
        'avgPayment': avgPayment,
        'overdueCards': overdueCards,
        'remainingBalance': totalDue - totalPaid,
      };
    } catch (e) {
      print('Error fetching dashboard stats: $e');
      return {
        'totalCards': 0,
        'totalPayments': 0,
        'totalDue': 0.0,
        'totalPaid': 0.0,
        'avgPayment': 0.0,
        'overdueCards': 0,
        'remainingBalance': 0.0,
      };
    }
  }

  // Check if cards and payments tables exist
  Future<bool> areTablesAvailable() async {
    try {
      final db = await _databaseHelper.database;
      
      // Check if cards table exists
      final cardsTableResult = await db.rawQuery('''
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='cards'
      ''');
      
      // Check if payments table exists
      final paymentsTableResult = await db.rawQuery('''
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='payments'
      ''');
      
      return cardsTableResult.isNotEmpty && paymentsTableResult.isNotEmpty;
    } catch (e) {
      print('Error checking table availability: $e');
      return false;
    }
  }
} 