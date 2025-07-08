import 'package:flutter/material.dart';
import '../models/bank_sms_model.dart';
import '../services/bank_sms_repository.dart';
import '../services/database_helper.dart';

class BankSmsManagerScreen extends StatefulWidget {
  const BankSmsManagerScreen({super.key});

  @override
  State<BankSmsManagerScreen> createState() => _BankSmsManagerScreenState();
}

class _BankSmsManagerScreenState extends State<BankSmsManagerScreen> with TickerProviderStateMixin {
  final BankSmsRepository _repository = BankSmsRepository();
  final DatabaseHelper _databaseHelper = DatabaseHelper();
  late TabController _tabController;
  
  List<BankSms> _bankMessages = [];
  List<BankSms> _filteredMessages = [];
  Map<String, dynamic> _statistics = {};
  Map<String, dynamic> _databaseInfo = {};
  bool _isLoading = false;
  String? _error;
  String _searchQuery = '';
  String _selectedSender = 'All';
  
  final TextEditingController _searchController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
    _loadData();
  }

  @override
  void dispose() {
    _tabController.dispose();
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _loadData() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      // Load all bank messages
      final messages = await _repository.getAllBankSms();
      
      // Load statistics
      final stats = await _repository.getBankSmsStatistics();
      
      // Load database info
      final dbInfo = await _databaseHelper.getDatabaseInfo();
      
      setState(() {
        _bankMessages = messages;
        _filteredMessages = messages;
        _statistics = stats;
        _databaseInfo = dbInfo;
      });
      
      _applyFilters();
    } catch (e) {
      setState(() {
        _error = e.toString();
      });
    } finally {
      setState(() {
        _isLoading = false;
      });
    }
  }

  void _applyFilters() {
    List<BankSms> filtered = _bankMessages;
    
    // Apply search filter
    if (_searchQuery.isNotEmpty) {
      filtered = filtered.where((msg) =>
        msg.body.toLowerCase().contains(_searchQuery.toLowerCase()) ||
        msg.address.toLowerCase().contains(_searchQuery.toLowerCase())
      ).toList();
    }
    
    // Apply sender filter
    if (_selectedSender != 'All') {
      filtered = filtered.where((msg) =>
        msg.address.toLowerCase().contains(_selectedSender.toLowerCase())
      ).toList();
    }
    
    setState(() {
      _filteredMessages = filtered;
    });
  }

  void _onSearchChanged(String query) {
    setState(() {
      _searchQuery = query;
    });
    _applyFilters();
  }

  List<String> _getUniqueSenders() {
    final senders = _bankMessages.map((msg) => msg.address).toSet().toList();
    senders.sort();
    return ['All', ...senders];
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Bank SMS Manager'),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadData,
            tooltip: 'Refresh',
          ),
          PopupMenuButton<String>(
            icon: const Icon(Icons.more_vert),
            onSelected: (value) {
              switch (value) {
                case 'clear_all':
                  _showClearAllDialog();
                  break;
                case 'export':
                  _showExportOptions();
                  break;
              }
            },
            itemBuilder: (context) => [
              const PopupMenuItem(
                value: 'export',
                child: Row(
                  children: [
                    Icon(Icons.download),
                    SizedBox(width: 8),
                    Text('Export Data'),
                  ],
                ),
              ),
              const PopupMenuItem(
                value: 'clear_all',
                child: Row(
                  children: [
                    Icon(Icons.delete_forever, color: Colors.red),
                    SizedBox(width: 8),
                    Text('Clear All Data', style: TextStyle(color: Colors.red)),
                  ],
                ),
              ),
            ],
          ),
        ],
        bottom: TabBar(
          controller: _tabController,
          tabs: const [
            Tab(icon: Icon(Icons.list), text: 'Messages'),
            Tab(icon: Icon(Icons.analytics), text: 'Statistics'),
            Tab(icon: Icon(Icons.storage), text: 'Database'),
          ],
        ),
      ),
      body: _isLoading
          ? const Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  CircularProgressIndicator(),
                  SizedBox(height: 16),
                  Text('Loading bank SMS data...'),
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
                      Text('Error: $_error'),
                      const SizedBox(height: 16),
                      ElevatedButton(
                        onPressed: _loadData,
                        child: const Text('Retry'),
                      ),
                    ],
                  ),
                )
              : TabBarView(
                  controller: _tabController,
                  children: [
                    _buildMessagesTab(),
                    _buildStatisticsTab(),
                    _buildDatabaseTab(),
                  ],
                ),
    );
  }

  Widget _buildMessagesTab() {
    return Column(
      children: [
        // Search and filter bar
        Container(
          padding: const EdgeInsets.all(16),
          child: Column(
            children: [
              TextField(
                controller: _searchController,
                decoration: const InputDecoration(
                  labelText: 'Search messages',
                  hintText: 'Search by content or sender',
                  prefixIcon: Icon(Icons.search),
                  border: OutlineInputBorder(),
                ),
                onChanged: _onSearchChanged,
              ),
              const SizedBox(height: 8),
              Row(
                children: [
                  const Text('Filter by sender: '),
                  const SizedBox(width: 8),
                  Expanded(
                    child: DropdownButton<String>(
                      value: _selectedSender,
                      isExpanded: true,
                      onChanged: (value) {
                        setState(() {
                          _selectedSender = value!;
                        });
                        _applyFilters();
                      },
                      items: _getUniqueSenders().map((sender) =>
                        DropdownMenuItem(
                          value: sender,
                          child: Text(
                            sender,
                            overflow: TextOverflow.ellipsis,
                          ),
                        )
                      ).toList(),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
        
        // Results count
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: Row(
            children: [
              Text(
                'Showing ${_filteredMessages.length} of ${_bankMessages.length} messages',
                style: Theme.of(context).textTheme.bodySmall,
              ),
              const Spacer(),
              if (_filteredMessages.length != _bankMessages.length)
                TextButton(
                  onPressed: () {
                    _searchController.clear();
                    setState(() {
                      _searchQuery = '';
                      _selectedSender = 'All';
                    });
                    _applyFilters();
                  },
                  child: const Text('Clear filters'),
                ),
            ],
          ),
        ),
        
        // Messages list
        Expanded(
          child: _filteredMessages.isEmpty
              ? Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Icon(Icons.inbox, size: 64, color: Colors.grey),
                      const SizedBox(height: 16),
                      Text(
                        _bankMessages.isEmpty ? 'No bank messages stored yet' : 'No messages match your filters',
                        style: const TextStyle(fontSize: 16, color: Colors.grey),
                      ),
                      if (_bankMessages.isEmpty) ...[
                        const SizedBox(height: 8),
                        const Text(
                          'Bank messages will appear here after categorization',
                          style: TextStyle(color: Colors.grey),
                        ),
                      ],
                    ],
                  ),
                )
              : ListView.builder(
                  padding: const EdgeInsets.all(16),
                  itemCount: _filteredMessages.length,
                  itemBuilder: (context, index) {
                    final message = _filteredMessages[index];
                    return _buildMessageCard(message);
                  },
                ),
        ),
      ],
    );
  }

  Widget _buildMessageCard(BankSms message) {
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header
            Row(
              children: [
                const Icon(Icons.account_balance, size: 16, color: Colors.blue),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(
                    message.address,
                    style: const TextStyle(fontWeight: FontWeight.bold),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                const SizedBox(width: 8),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                  decoration: BoxDecoration(
                    color: Colors.green.withOpacity(0.2),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Text(
                    '${(message.confidence * 100).round()}%',
                    style: const TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.bold,
                      color: Colors.green,
                    ),
                  ),
                ),
              ],
            ),
            
            const SizedBox(height: 8),
            
            // Message content
            Text(
              message.body,
              style: const TextStyle(fontSize: 14),
            ),
            
            const SizedBox(height: 8),
            
            // Date and indicators
            Row(
              children: [
                Icon(Icons.access_time, size: 14, color: Colors.grey[600]),
                const SizedBox(width: 4),
                Text(
                  _formatDate(message.dateTime),
                  style: TextStyle(fontSize: 12, color: Colors.grey[600]),
                ),
                const SizedBox(width: 16),
                Icon(Icons.save, size: 14, color: Colors.grey[600]),
                const SizedBox(width: 4),
                Text(
                  _formatDate(message.createdAt),
                  style: TextStyle(fontSize: 12, color: Colors.grey[600]),
                ),
              ],
            ),
            
            // Indicators
            if (message.indicators.isNotEmpty) ...[
              const SizedBox(height: 8),
              Wrap(
                spacing: 4,
                runSpacing: 4,
                children: message.indicators.take(3).map((indicator) =>
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                    decoration: BoxDecoration(
                      color: Colors.blue.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: Text(
                      indicator,
                      style: const TextStyle(fontSize: 10, color: Colors.blue),
                    ),
                  )
                ).toList(),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildStatisticsTab() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildStatCard(
            'Total Bank Messages',
            '${_statistics['total'] ?? 0}',
            Icons.account_balance,
            Colors.blue,
          ),
          _buildStatCard(
            'Unique Senders',
            '${_statistics['uniqueSenders'] ?? 0}',
            Icons.contacts,
            Colors.green,
          ),
          _buildStatCard(
            'Average Confidence',
            '${((_statistics['averageConfidence'] ?? 0.0) * 100).toStringAsFixed(1)}%',
            Icons.trending_up,
            Colors.orange,
          ),
          
          const SizedBox(height: 16),
          
          if (_statistics['oldestMessage'] != null || _statistics['newestMessage'] != null)
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Date Range',
                      style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(height: 12),
                    if (_statistics['oldestMessage'] != null)
                      Row(
                        children: [
                          const Icon(Icons.first_page, color: Colors.grey),
                          const SizedBox(width: 8),
                          const Text('Oldest: '),
                          Text(_formatDate(_statistics['oldestMessage'])),
                        ],
                      ),
                    const SizedBox(height: 8),
                    if (_statistics['newestMessage'] != null)
                      Row(
                        children: [
                          const Icon(Icons.last_page, color: Colors.grey),
                          const SizedBox(width: 8),
                          const Text('Newest: '),
                          Text(_formatDate(_statistics['newestMessage'])),
                        ],
                      ),
                  ],
                ),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildStatCard(String title, String value, IconData icon, Color color) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: color.withOpacity(0.1),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Icon(icon, color: color, size: 24),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: const TextStyle(fontSize: 14, color: Colors.grey),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    value,
                    style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildDatabaseTab() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Database Information',
                    style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 12),
                  _buildInfoRow('Database Path', '${_databaseInfo['path'] ?? 'Unknown'}'),
                  _buildInfoRow('Version', '${_databaseInfo['version'] ?? 'Unknown'}'),
                  _buildInfoRow('Tables', '${_databaseInfo['tables'] ?? 'Unknown'}'),
                  _buildInfoRow('Bank SMS Count', '${_databaseInfo['bankSmsCount'] ?? 'Unknown'}'),
                ],
              ),
            ),
          ),
          
          const SizedBox(height: 16),
          
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Database Actions',
                    style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 12),
                  
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton.icon(
                      onPressed: _loadData,
                      icon: const Icon(Icons.refresh),
                      label: const Text('Refresh Data'),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.blue,
                        foregroundColor: Colors.white,
                      ),
                    ),
                  ),
                  
                  const SizedBox(height: 8),
                  
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton.icon(
                      onPressed: _showExportOptions,
                      icon: const Icon(Icons.download),
                      label: const Text('Export Data'),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.green,
                        foregroundColor: Colors.white,
                      ),
                    ),
                  ),
                  
                  const SizedBox(height: 8),
                  
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton.icon(
                      onPressed: _showClearAllDialog,
                      icon: const Icon(Icons.delete_forever),
                      label: const Text('Clear All Data'),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.red,
                        foregroundColor: Colors.white,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildInfoRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 100,
            child: Text(
              '$label:',
              style: const TextStyle(fontWeight: FontWeight.w500),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: const TextStyle(color: Colors.grey),
            ),
          ),
        ],
      ),
    );
  }

  String _formatDate(DateTime? dateTime) {
    if (dateTime == null) return 'Unknown';
    return '${dateTime.day}/${dateTime.month}/${dateTime.year} ${dateTime.hour}:${dateTime.minute.toString().padLeft(2, '0')}';
  }

  void _showClearAllDialog() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Clear All Data'),
        content: const Text(
          'Are you sure you want to delete all stored bank SMS messages? This action cannot be undone.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () async {
              Navigator.of(context).pop();
              await _clearAllData();
            },
            style: TextButton.styleFrom(foregroundColor: Colors.red),
            child: const Text('Delete All'),
          ),
        ],
      ),
    );
  }

  Future<void> _clearAllData() async {
    try {
      setState(() => _isLoading = true);
      await _repository.deleteAllBankSms();
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('All bank SMS data cleared successfully'),
          backgroundColor: Colors.green,
        ),
      );
      await _loadData();
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Error clearing data: $e'),
          backgroundColor: Colors.red,
        ),
      );
    } finally {
      setState(() => _isLoading = false);
    }
  }

  void _showExportOptions() {
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Export functionality coming soon!'),
        backgroundColor: Colors.blue,
      ),
    );
  }
} 