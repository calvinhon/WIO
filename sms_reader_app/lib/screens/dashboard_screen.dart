import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import '../services/dashboard_service.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> with TickerProviderStateMixin {
  final DashboardService _dashboardService = DashboardService();
  late TabController _tabController;

  Map<String, dynamic> _stats = {};
  List<Map<String, dynamic>> _cards = [];
  List<Map<String, dynamic>> _paymentsByCard = [];
  List<Map<String, dynamic>> _monthlyPayments = [];
  List<Map<String, dynamic>> _recentPayments = [];
  bool _isLoading = false;
  bool _tablesAvailable = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 4, vsync: this);
    _loadDashboardData();
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  Future<void> _loadDashboardData() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      // Check if tables are available
      final tablesAvailable = await _dashboardService.areTablesAvailable();
      
      if (!tablesAvailable) {
        setState(() {
          _tablesAvailable = false;
          _isLoading = false;
          _error = 'Cards and payments tables not found. Please run the Python analyzer first.';
        });
        return;
      }

      // Load all dashboard data
      final results = await Future.wait([
        _dashboardService.getDashboardStats(),
        _dashboardService.getCardsWithPaymentSummary(),
        _dashboardService.getRecentPayments(limit: 20),
        _dashboardService.getPaymentsByCard(),
        _dashboardService.getMonthlyPaymentTotals(),
      ]);

      setState(() {
        _tablesAvailable = true;
        _stats = results[0] as Map<String, dynamic>;
        _cards = results[1] as List<Map<String, dynamic>>;
        _recentPayments = results[2] as List<Map<String, dynamic>>;
        _paymentsByCard = results[3] as List<Map<String, dynamic>>;
        _monthlyPayments = results[4] as List<Map<String, dynamic>>;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _isLoading = false;
        _error = e.toString();
      });
    }
  }

  Widget _buildStatCard(String title, String value, IconData icon, Color color) {
    return Card(
      elevation: 4,
      child: Padding(
        padding: const EdgeInsets.all(12.0),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 28, color: color),
            const SizedBox(height: 6),
            Flexible(
              child: FittedBox(
                fit: BoxFit.scaleDown,
                child: Text(
                  value,
                  style: const TextStyle(
                    fontSize: 20,
                    fontWeight: FontWeight.bold,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ),
            const SizedBox(height: 4),
            Flexible(
              child: Text(
                title,
                style: TextStyle(
                  fontSize: 11,
                  color: Colors.grey[600],
                ),
                textAlign: TextAlign.center,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildOverviewTab() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Statistics Cards
          Text(
            'Financial Overview',
            style: Theme.of(context).textTheme.headlineSmall,
          ),
          const SizedBox(height: 16),
          GridView.count(
            crossAxisCount: 2,
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            mainAxisSpacing: 16,
            crossAxisSpacing: 16,
            childAspectRatio: 1.2,
            children: [
              _buildStatCard(
                'Total Cards',
                _stats['totalCards']?.toString() ?? '0',
                Icons.credit_card,
                Colors.blue,
              ),
              _buildStatCard(
                'Total Payments',
                _stats['totalPayments']?.toString() ?? '0',
                Icons.payment,
                Colors.green,
              ),
              _buildStatCard(
                'Total Due',
                'AED ${(_stats['totalDue'] ?? 0.0).toStringAsFixed(2)}',
                Icons.account_balance_wallet,
                Colors.orange,
              ),
              _buildStatCard(
                'Total Paid',
                'AED ${(_stats['totalPaid'] ?? 0.0).toStringAsFixed(2)}',
                Icons.paid,
                Colors.purple,
              ),
              _buildStatCard(
                'Avg Payment',
                'AED ${(_stats['avgPayment'] ?? 0.0).toStringAsFixed(2)}',
                Icons.trending_up,
                Colors.teal,
              ),
              _buildStatCard(
                'Overdue Cards',
                _stats['overdueCards']?.toString() ?? '0',
                Icons.warning,
                Colors.red,
              ),
            ],
          ),
          const SizedBox(height: 24),
          
          // Payments by Card Chart
          if (_paymentsByCard.isNotEmpty) ...[
            Text(
              'Payments by Card',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 16),
            Container(
              height: 300,
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(12),
                boxShadow: [
                  BoxShadow(
                    color: Colors.grey.withOpacity(0.1),
                    spreadRadius: 1,
                    blurRadius: 4,
                    offset: const Offset(0, 2),
                  ),
                ],
              ),
              child: PieChart(
                PieChartData(
                  sectionsSpace: 2,
                  centerSpaceRadius: 60,
                  sections: _paymentsByCard.take(6).map((payment) {
                    final index = _paymentsByCard.indexOf(payment);
                    final colors = [
                      Colors.blue,
                      Colors.green,
                      Colors.orange,
                      Colors.purple,
                      Colors.red,
                      Colors.teal,
                    ];
                    return PieChartSectionData(
                      color: colors[index % colors.length],
                      value: (payment['total_amount'] as num).toDouble(),
                      title: '${payment['card_id']}\nAED ${(payment['total_amount'] as num).toStringAsFixed(0)}',
                      titleStyle: const TextStyle(
                        fontSize: 10,
                        fontWeight: FontWeight.bold,
                        color: Colors.white,
                      ),
                      radius: 100,
                    );
                  }).toList(),
                ),
              ),
            ),
            const SizedBox(height: 24),
          ],
          
          // Monthly Payments Chart
          if (_monthlyPayments.isNotEmpty) ...[
            Text(
              'Monthly Payment Trends',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 16),
            Container(
              height: 300,
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(12),
                boxShadow: [
                  BoxShadow(
                    color: Colors.grey.withOpacity(0.1),
                    spreadRadius: 1,
                    blurRadius: 4,
                    offset: const Offset(0, 2),
                  ),
                ],
              ),
              child: LineChart(
                LineChartData(
                  gridData: FlGridData(show: true),
                  titlesData: FlTitlesData(
                    bottomTitles: AxisTitles(
                      sideTitles: SideTitles(
                        showTitles: true,
                        getTitlesWidget: (value, meta) {
                          final index = value.toInt();
                          if (index >= 0 && index < _monthlyPayments.length) {
                            return Text(
                              _monthlyPayments[index]['month_year'] ?? '',
                              style: const TextStyle(fontSize: 10),
                            );
                          }
                          return const Text('');
                        },
                      ),
                    ),
                    leftTitles: AxisTitles(
                      sideTitles: SideTitles(
                        showTitles: true,
                        getTitlesWidget: (value, meta) {
                          return Text(
                            value.toInt().toString(),
                            style: const TextStyle(fontSize: 10),
                          );
                        },
                      ),
                    ),
                    topTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
                    rightTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
                  ),
                  borderData: FlBorderData(show: true),
                  lineBarsData: [
                    LineChartBarData(
                      spots: _monthlyPayments.asMap().entries.map((entry) {
                        return FlSpot(
                          entry.key.toDouble(),
                          (entry.value['total_amount'] as num).toDouble(),
                        );
                      }).toList(),
                      isCurved: true,
                      color: Colors.blue,
                      barWidth: 3,
                      isStrokeCapRound: true,
                      dotData: FlDotData(show: true),
                      belowBarData: BarAreaData(
                        show: true,
                        color: Colors.blue.withOpacity(0.2),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildCardsTab() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Credit Cards Summary',
            style: Theme.of(context).textTheme.headlineSmall,
          ),
          const SizedBox(height: 16),
          if (_cards.isEmpty)
            const Center(
              child: Text('No cards data available'),
            )
          else
            ListView.builder(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              itemCount: _cards.length,
              itemBuilder: (context, index) {
                final card = _cards[index];
                final totalDue = (card['latest_total_amount'] as num?) ?? 0;
                final totalPaid = (card['total_paid'] as num?) ?? 0;
                final paymentCount = (card['payment_count'] as num?) ?? 0;
                final remainingBalance = totalDue - totalPaid;
                final hasDueDate = card['latest_due_date'] != null && card['latest_due_date'].toString().isNotEmpty && card['latest_due_date'] != 'N/A';
                
                // Determine display logic based on user requirements
                final bool hasPendingAmount = remainingBalance > 0;
                final bool shouldShowAsNegative = hasPendingAmount;
                final Color amountColor = hasPendingAmount ? Colors.red.shade300 : Colors.black;
                final Color balanceColor = hasPendingAmount ? Colors.red.shade300 : Colors.green;
                
                return Card(
                  margin: const EdgeInsets.only(bottom: 16),
                  child: ExpansionTile(
                    leading: CircleAvatar(
                      backgroundColor: remainingBalance > 0 ? Colors.red : Colors.green,
                      child: Text(
                        card['card_id']?.toString().substring(0, 2) ?? '??',
                        style: const TextStyle(
                          color: Colors.white,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                    title: Text(
                      'Card *${card['card_id']}',
                      style: const TextStyle(fontWeight: FontWeight.bold),
                    ),
                    subtitle: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Due: ${shouldShowAsNegative ? '-' : ''}AED ${totalDue.toStringAsFixed(2)}',
                          style: TextStyle(color: amountColor),
                        ),
                        Text(
                          'Paid: AED ${totalPaid.toStringAsFixed(2)}',
                          style: TextStyle(color: Colors.black),
                        ),
                        Text(
                          'Balance: ${shouldShowAsNegative ? '-' : ''}AED ${remainingBalance.abs().toStringAsFixed(2)}',
                          style: TextStyle(
                            color: balanceColor,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ],
                    ),
                    trailing: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Text(
                          '${paymentCount} payments',
                          style: const TextStyle(fontSize: 12),
                        ),
                        Text(
                          'Due: ${card['latest_due_date'] ?? 'N/A'}',
                          style: TextStyle(
                            fontSize: 12,
                            color: hasDueDate && hasPendingAmount ? Colors.red.shade300 : Colors.black,
                          ),
                        ),
                      ],
                    ),
                    children: [
                      Padding(
                        padding: const EdgeInsets.all(16.0),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                Expanded(
                                  child: _buildInfoItemWithColor('Total Due', '${shouldShowAsNegative ? '-' : ''}AED ${totalDue.toStringAsFixed(2)}', amountColor),
                                ),
                                Expanded(
                                  child: _buildInfoItemWithColor('Min Payment', '${shouldShowAsNegative ? '-' : ''}AED ${((card['latest_min_amount'] as num?) ?? 0).toStringAsFixed(2)}', amountColor),
                                ),
                              ],
                            ),
                            const SizedBox(height: 8),
                            Row(
                              children: [
                                Expanded(
                                  child: _buildInfoItemWithColor('Total Paid', 'AED ${totalPaid.toStringAsFixed(2)}', Colors.black),
                                ),
                                Expanded(
                                  child: _buildInfoItemWithColor('Payment Count', paymentCount.toString(), Colors.black),
                                ),
                              ],
                            ),
                            const SizedBox(height: 8),
                            Row(
                              children: [
                                Expanded(
                                  child: _buildInfoItemWithColor('Last Payment', card['last_payment_date'] ?? 'N/A', Colors.black),
                                ),
                                Expanded(
                                  child: _buildInfoItemWithColor('Updated', card['updated_at'] ?? 'N/A', Colors.black),
                                ),
                              ],
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                );
              },
            ),
        ],
      ),
    );
  }

  Widget _buildInfoItem(String label, String value) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: TextStyle(
            fontSize: 12,
            color: Colors.grey[600],
          ),
        ),
        Text(
          value,
          style: const TextStyle(
            fontWeight: FontWeight.bold,
          ),
        ),
      ],
    );
  }

  Widget _buildInfoItemWithColor(String label, String value, Color valueColor) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: TextStyle(
            fontSize: 12,
            color: Colors.grey[600],
          ),
        ),
        Text(
          value,
          style: TextStyle(
            fontWeight: FontWeight.bold,
            color: valueColor,
          ),
        ),
      ],
    );
  }

  Widget _buildPaymentsTab() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Recent Payments',
            style: Theme.of(context).textTheme.headlineSmall,
          ),
          const SizedBox(height: 16),
          if (_recentPayments.isEmpty)
            const Center(
              child: Text('No payments data available'),
            )
          else
            ListView.builder(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              itemCount: _recentPayments.length,
              itemBuilder: (context, index) {
                final payment = _recentPayments[index];
                final amount = (payment['amount'] as num?) ?? 0;
                
                return Card(
                  margin: const EdgeInsets.only(bottom: 8),
                  child: ListTile(
                    leading: CircleAvatar(
                      backgroundColor: Colors.green,
                      child: const Icon(Icons.payment, color: Colors.white),
                    ),
                    title: Text(
                      'Card *${payment['card_id']}',
                      style: const TextStyle(fontWeight: FontWeight.bold),
                    ),
                    subtitle: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('AED ${amount.toStringAsFixed(2)}'),
                        Text('Date: ${payment['payment_date'] ?? 'N/A'}'),
                        if (payment['description'] != null && payment['description'].toString().isNotEmpty)
                          Text(
                            payment['description'].toString(),
                            style: TextStyle(
                              fontSize: 12,
                              color: Colors.grey[600],
                            ),
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                          ),
                      ],
                    ),
                    trailing: Text(
                      'ID: ${payment['payment_id']}',
                      style: const TextStyle(fontSize: 12),
                    ),
                  ),
                );
              },
            ),
        ],
      ),
    );
  }

  Widget _buildAnalyticsTab() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Payment Analytics',
            style: Theme.of(context).textTheme.headlineSmall,
          ),
          const SizedBox(height: 16),
          
          // Payment Distribution by Card
          if (_paymentsByCard.isNotEmpty) ...[
            Text(
              'Payment Distribution by Card',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 16),
            ...(_paymentsByCard.map((cardPayment) {
              final cardId = cardPayment['card_id'];
              final totalAmount = (cardPayment['total_amount'] as num?) ?? 0;
              final paymentCount = (cardPayment['payment_count'] as num?) ?? 0;
              final avgAmount = (cardPayment['avg_amount'] as num?) ?? 0;
              final minAmount = (cardPayment['min_amount'] as num?) ?? 0;
              final maxAmount = (cardPayment['max_amount'] as num?) ?? 0;
              
              return Card(
                margin: const EdgeInsets.only(bottom: 16),
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Icon(Icons.credit_card, color: Colors.blue),
                          const SizedBox(width: 8),
                          Text(
                            'Card *$cardId',
                            style: const TextStyle(
                              fontSize: 18,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 16),
                      Row(
                        children: [
                          Expanded(
                            child: _buildAnalyticsItem('Total Paid', 'AED ${totalAmount.toStringAsFixed(2)}', Icons.paid),
                          ),
                          Expanded(
                            child: _buildAnalyticsItem('Payments', paymentCount.toString(), Icons.payment),
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      Row(
                        children: [
                          Expanded(
                            child: _buildAnalyticsItem('Average', 'AED ${avgAmount.toStringAsFixed(2)}', Icons.trending_up),
                          ),
                          Expanded(
                            child: _buildAnalyticsItem('Min', 'AED ${minAmount.toStringAsFixed(2)}', Icons.trending_down),
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      _buildAnalyticsItem('Max Payment', 'AED ${maxAmount.toStringAsFixed(2)}', Icons.trending_flat),
                    ],
                  ),
                ),
              );
            }).toList()),
          ],
          
          // Monthly trends
          if (_monthlyPayments.isNotEmpty) ...[
            const SizedBox(height: 24),
            Text(
              'Monthly Payment Summary',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 16),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  children: _monthlyPayments.map((monthData) {
                    final monthYear = monthData['month_year'] ?? 'N/A';
                    final totalAmount = (monthData['total_amount'] as num?) ?? 0;
                    final paymentCount = (monthData['payment_count'] as num?) ?? 0;
                    
                    return Padding(
                      padding: const EdgeInsets.symmetric(vertical: 8),
                      child: Row(
                        children: [
                          Expanded(
                            flex: 2,
                            child: Text(
                              monthYear,
                              style: const TextStyle(fontWeight: FontWeight.bold),
                            ),
                          ),
                          Expanded(
                            flex: 3,
                            child: Text('AED ${totalAmount.toStringAsFixed(2)}'),
                          ),
                          Expanded(
                            flex: 2,
                            child: Text('$paymentCount payments'),
                          ),
                        ],
                      ),
                    );
                  }).toList(),
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildAnalyticsItem(String title, String value, IconData icon) {
    return Row(
      children: [
        Icon(icon, size: 20, color: Colors.grey[600]),
        const SizedBox(width: 8),
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              title,
              style: TextStyle(
                fontSize: 12,
                color: Colors.grey[600],
              ),
            ),
            Text(
              value,
              style: const TextStyle(
                fontWeight: FontWeight.bold,
              ),
            ),
          ],
        ),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Financial Dashboard'),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadDashboardData,
            tooltip: 'Refresh Data',
          ),
        ],
        bottom: !_isLoading && _tablesAvailable
            ? TabBar(
                controller: _tabController,
                isScrollable: true,
                tabs: const [
                  Tab(icon: Icon(Icons.dashboard), text: 'Overview'),
                  Tab(icon: Icon(Icons.credit_card), text: 'Cards'),
                  Tab(icon: Icon(Icons.payment), text: 'Payments'),
                  Tab(icon: Icon(Icons.analytics), text: 'Analytics'),
                ],
              )
            : null,
      ),
      body: _isLoading
          ? const Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  CircularProgressIndicator(),
                  SizedBox(height: 16),
                  Text('Loading dashboard data...'),
                ],
              ),
            )
          : _error != null
              ? Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Icon(Icons.error_outline, size: 64, color: Colors.red),
                      const SizedBox(height: 16),
                      Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 32),
                        child: Text(
                          _error!,
                          textAlign: TextAlign.center,
                          style: const TextStyle(fontSize: 16),
                        ),
                      ),
                      const SizedBox(height: 24),
                      ElevatedButton(
                        onPressed: _loadDashboardData,
                        child: const Text('Retry'),
                      ),
                    ],
                  ),
                )
              : !_tablesAvailable
                  ? const Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(Icons.table_chart, size: 64, color: Colors.grey),
                          SizedBox(height: 16),
                          Text(
                            'No dashboard data available',
                            style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                          ),
                          SizedBox(height: 8),
                          Text(
                            'Please run the Python analyzer to generate cards and payments data',
                            textAlign: TextAlign.center,
                          ),
                        ],
                      ),
                    )
                  : TabBarView(
                      controller: _tabController,
                      children: [
                        _buildOverviewTab(),
                        _buildCardsTab(),
                        _buildPaymentsTab(),
                        _buildAnalyticsTab(),
                      ],
                    ),
    );
  }
} 