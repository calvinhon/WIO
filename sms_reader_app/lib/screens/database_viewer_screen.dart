import 'package:flutter/material.dart';
import '../services/database_helper.dart';

class DatabaseViewerScreen extends StatefulWidget {
  const DatabaseViewerScreen({super.key});

  @override
  State<DatabaseViewerScreen> createState() => _DatabaseViewerScreenState();
}

class _DatabaseViewerScreenState extends State<DatabaseViewerScreen> with TickerProviderStateMixin {
  final DatabaseHelper _databaseHelper = DatabaseHelper();
  late TabController _tabController;
  
  List<String> _tableNames = [];
  Map<String, List<Map<String, dynamic>>> _tablesData = {};
  Map<String, List<Map<String, dynamic>>> _tablesSchema = {};
  Map<String, dynamic> _databaseInfo = {};
  bool _isLoading = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadDatabaseInfo();
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  Future<void> _loadDatabaseInfo() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      // Get all table names
      final tableNames = await _databaseHelper.getAllTableNames();
      
      // Load data for each table
      final tablesData = <String, List<Map<String, dynamic>>>{};
      final tablesSchema = <String, List<Map<String, dynamic>>>{};
      
      for (String tableName in tableNames) {
        // Get table schema
        final schemaResult = await _databaseHelper.getTableSchema(tableName);
        tablesSchema[tableName] = schemaResult;
        
        // Get table data (limit to 100 rows for performance)
        final dataResult = await _databaseHelper.getTableData(tableName, limit: 100);
        tablesData[tableName] = dataResult;
      }
      
      // Get database info
      final dbInfo = await _databaseHelper.getDatabaseInfo();
      
      setState(() {
        _tableNames = tableNames;
        _tablesData = tablesData;
        _tablesSchema = tablesSchema;
        _databaseInfo = dbInfo;
      });
      
      // Initialize tab controller after we have table names
      _tabController = TabController(
        length: _tableNames.length + 1, // +1 for database info tab
        vsync: this,
      );
      
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

  Widget _buildDatabaseInfoTab() {
    return Padding(
      padding: const EdgeInsets.all(16.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      const Icon(Icons.storage, color: Colors.blue),
                      const SizedBox(width: 8),
                      Text(
                        'Database Information',
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),
                                     _buildInfoRow('Database Version', _databaseInfo['version']?.toString() ?? 'Unknown'),
                   _buildInfoRow('Total Tables', _tableNames.length.toString()),
                   _buildInfoRow('Database Path', _databaseInfo['path']?.toString() ?? 'Unknown'),
                   const SizedBox(height: 8),
                   Text(
                     'Table Row Counts:',
                     style: TextStyle(fontWeight: FontWeight.bold, color: Colors.grey[600]),
                   ),
                   const SizedBox(height: 4),
                   if (_databaseInfo['tableCounts'] != null)
                     ...(_databaseInfo['tableCounts'] as Map<String, int>).entries.map(
                       (entry) => _buildInfoRow('  ${entry.key}', entry.value.toString()),
                     ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      const Icon(Icons.table_chart, color: Colors.green),
                      const SizedBox(width: 8),
                      Text(
                        'Tables Overview',
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),
                  if (_tableNames.isEmpty)
                    const Text('No tables found in database')
                  else
                                         ...(_tableNames.map((tableName) {
                       final displayedRows = _tablesData[tableName]?.length ?? 0;
                       final actualRows = _databaseInfo['tableCounts'] != null 
                         ? (_databaseInfo['tableCounts'] as Map<String, int>)[tableName] ?? 0
                         : displayedRows;
                       final columnCount = _tablesSchema[tableName]?.length ?? 0;
                       
                       return Padding(
                         padding: const EdgeInsets.symmetric(vertical: 4.0),
                         child: Row(
                           children: [
                             Expanded(
                               child: Text(
                                 tableName,
                                 style: const TextStyle(fontWeight: FontWeight.bold),
                               ),
                             ),
                             Text(
                               '$columnCount columns, $actualRows rows${actualRows > 100 ? ' (showing first 100)' : ''}',
                               style: TextStyle(
                                 color: actualRows > 100 ? Colors.orange[700] : null,
                               ),
                             ),
                           ],
                         ),
                       );
                     }).toList()),
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
      padding: const EdgeInsets.symmetric(vertical: 4.0),
      child: Row(
        children: [
          SizedBox(
            width: 120,
            child: Text(
              label,
              style: const TextStyle(fontWeight: FontWeight.bold),
            ),
          ),
          const Text(': '),
          Expanded(
            child: Text(value),
          ),
        ],
      ),
    );
  }

  Widget _buildTableTab(String tableName) {
    final tableData = _tablesData[tableName] ?? [];
    final tableSchema = _tablesSchema[tableName] ?? [];
    
    if (tableData.isEmpty) {
      return const Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.table_chart, size: 64, color: Colors.grey),
            SizedBox(height: 16),
            Text('No data found in this table'),
          ],
        ),
      );
    }
    
    return Column(
      children: [
        // Schema information
        Card(
          margin: const EdgeInsets.all(8.0),
          child: Padding(
            padding: const EdgeInsets.all(12.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    const Icon(Icons.schema, size: 20, color: Colors.blue),
                    const SizedBox(width: 8),
                    Text(
                      'Schema for $tableName',
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 8,
                  runSpacing: 4,
                  children: tableSchema.map<Widget>((column) {
                    final name = column['name'] as String;
                    final type = column['type'] as String;
                    final isPrimary = (column['pk'] as int) == 1;
                    final isNotNull = (column['notnull'] as int) == 1;
                    
                    return Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(
                        color: isPrimary ? Colors.orange.shade100 : Colors.grey.shade100,
                        borderRadius: BorderRadius.circular(4),
                        border: Border.all(color: isPrimary ? Colors.orange : Colors.grey),
                      ),
                      child: Text(
                        '$name: $type${isPrimary ? ' (PK)' : ''}${isNotNull ? ' NOT NULL' : ''}',
                        style: TextStyle(
                          fontSize: 12,
                          fontWeight: isPrimary ? FontWeight.bold : FontWeight.normal,
                        ),
                      ),
                    );
                  }).toList(),
                ),
              ],
            ),
          ),
        ),
        // Data table
        Expanded(
          child: Card(
            margin: const EdgeInsets.all(8.0),
            child: Padding(
              padding: const EdgeInsets.all(8.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                                     Row(
                     children: [
                       const Icon(Icons.table_rows, size: 20, color: Colors.green),
                       const SizedBox(width: 8),
                       Text(
                         'Data in $tableName (${tableData.length} rows${tableData.length == 100 ? ' - showing first 100' : ''})',
                         style: Theme.of(context).textTheme.titleMedium,
                       ),
                     ],
                   ),
                  const SizedBox(height: 8),
                  Expanded(
                    child: SingleChildScrollView(
                      scrollDirection: Axis.horizontal,
                      child: SingleChildScrollView(
                        child: DataTable(
                          columnSpacing: 16,
                          columns: tableData.isNotEmpty
                              ? tableData.first.keys.map<DataColumn>((key) {
                                  return DataColumn(
                                    label: Text(
                                      key,
                                      style: const TextStyle(fontWeight: FontWeight.bold),
                                    ),
                                  );
                                }).toList()
                              : [],
                          rows: tableData.map<DataRow>((row) {
                            return DataRow(
                              cells: row.values.map<DataCell>((value) {
                                String displayValue = value?.toString() ?? 'NULL';
                                
                                // Format long text
                                if (displayValue.length > 50) {
                                  displayValue = '${displayValue.substring(0, 50)}...';
                                }
                                
                                return DataCell(
                                  Container(
                                    constraints: const BoxConstraints(maxWidth: 200),
                                    child: Text(
                                      displayValue,
                                      overflow: TextOverflow.ellipsis,
                                      style: TextStyle(
                                        fontStyle: value == null ? FontStyle.italic : FontStyle.normal,
                                        color: value == null ? Colors.grey : null,
                                      ),
                                    ),
                                  ),
                                );
                              }).toList(),
                            );
                          }).toList(),
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Database Viewer'),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadDatabaseInfo,
            tooltip: 'Refresh',
          ),
        ],
        bottom: _isLoading || _error != null || _tableNames.isEmpty
            ? null
            : TabBar(
                controller: _tabController,
                isScrollable: true,
                tabs: [
                  const Tab(icon: Icon(Icons.info), text: 'Database Info'),
                  ..._tableNames.map((tableName) => Tab(
                    icon: const Icon(Icons.table_chart),
                    text: tableName,
                  )),
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
                  Text('Loading database information...'),
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
                        onPressed: _loadDatabaseInfo,
                        child: const Text('Retry'),
                      ),
                    ],
                  ),
                )
              : _tableNames.isEmpty
                  ? const Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(Icons.table_chart, size: 64, color: Colors.grey),
                          SizedBox(height: 16),
                          Text('No tables found in database'),
                        ],
                      ),
                    )
                  : TabBarView(
                      controller: _tabController,
                      children: [
                        _buildDatabaseInfoTab(),
                        ..._tableNames.map((tableName) => _buildTableTab(tableName)),
                      ],
                    ),
    );
  }
} 