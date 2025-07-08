import 'package:flutter/material.dart';
import 'services/sms_service.dart';
import 'services/data_sender_service.dart';
import 'models/sms_message_model.dart';
import 'screens/nlp_analysis_screen.dart';
import 'screens/sms_categorization_screen.dart';
import 'screens/bank_sms_manager_screen.dart';

void main() {
  runApp(const SmsReaderApp());
}

class SmsReaderApp extends StatelessWidget {
  const SmsReaderApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'SMS Reader & Analyzer',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.blue),
        useMaterial3: true,
      ),
      home: const SmsReaderHomePage(),
    );
  }
}

class SmsReaderHomePage extends StatefulWidget {
  const SmsReaderHomePage({super.key});

  @override
  State<SmsReaderHomePage> createState() => _SmsReaderHomePageState();
}

class _SmsReaderHomePageState extends State<SmsReaderHomePage> {
  final SmsService _smsService = SmsService();
  final DataSenderService _dataSenderService = DataSenderService();
  
  List<SmsMessageModel> _smsMessages = [];
  bool _isLoading = false;
  bool _hasPermission = false;
  String _statusMessage = 'Welcome! Tap "Load SMS" to start reading messages.';
  String _serverUrl = 'http://your-server.com/api/sms';

  final TextEditingController _urlController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _urlController.text = _serverUrl;
    _checkPermissions();
  }

  @override
  void dispose() {
    _urlController.dispose();
    super.dispose();
  }

  Future<void> _checkPermissions() async {
    final hasPermission = await _smsService.checkSmsPermission();
    setState(() {
      _hasPermission = hasPermission;
      if (!_hasPermission) {
        _statusMessage = 'SMS permission required. Tap "Request Permission" to continue.';
      }
    });
  }

  Future<void> _requestPermissions() async {
    setState(() {
      _isLoading = true;
      _statusMessage = 'Requesting SMS permissions...';
    });

    final hasPermission = await _smsService.requestSmsPermission();
    
    setState(() {
      _hasPermission = hasPermission;
      _isLoading = false;
      if (_hasPermission) {
        _statusMessage = 'Permission granted! You can now load SMS messages.';
      } else {
        _statusMessage = 'Permission denied. Cannot read SMS messages.';
      }
    });
  }

  Future<void> _loadSmsMessages() async {
    if (!_hasPermission) {
      _showSnackBar('SMS permission required', Colors.red);
      return;
    }

    setState(() {
      _isLoading = true;
      _statusMessage = 'Loading SMS messages...';
    });

    try {
      final messages = await _smsService.getAllSmsMessages();
      setState(() {
        _smsMessages = messages;
        _isLoading = false;
        _statusMessage = 'Loaded ${messages.length} SMS messages';
      });
    } catch (e) {
      setState(() {
        _isLoading = false;
        _statusMessage = 'Error loading SMS: $e';
      });
      _showSnackBar('Error loading SMS messages', Colors.red);
    }
  }

  Future<void> _sendToAnalyzer() async {
    if (_smsMessages.isEmpty) {
      _showSnackBar('No SMS messages to send', Colors.orange);
      return;
    }

    setState(() {
      _isLoading = true;
      _statusMessage = 'Sending SMS data to analyzer...';
    });

    try {
      _serverUrl = _urlController.text.trim();
      if (_serverUrl.isEmpty) {
        throw Exception('Server URL cannot be empty');
      }

      final success = await _dataSenderService.sendSmsData(_smsMessages, _serverUrl);
      
      setState(() {
        _isLoading = false;
        if (success) {
          _statusMessage = 'Successfully sent ${_smsMessages.length} messages to analyzer';
        } else {
          _statusMessage = 'Failed to send data to analyzer';
        }
      });
      
      _showSnackBar(
        success ? 'Data sent successfully!' : 'Failed to send data',
        success ? Colors.green : Colors.red,
      );
    } catch (e) {
      setState(() {
        _isLoading = false;
        _statusMessage = 'Error sending data: $e';
      });
      _showSnackBar('Error: $e', Colors.red);
    }
  }

  void _categorizeMessages() {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (context) => SmsCategorization(messages: _smsMessages),
      ),
    );
  }

  void _analyzeWithNlp() {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (context) => NlpAnalysisScreen(messages: _smsMessages),
      ),
    );
  }

  void _openBankSmsManager() {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (context) => const BankSmsManagerScreen(),
      ),
    );
  }

  void _showSnackBar(String message, Color color) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: color,
        duration: const Duration(seconds: 3),
      ),
    );
  }

  void _showServerUrlDialog() {
    showDialog(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: const Text('Set Server URL'),
          content: TextField(
            controller: _urlController,
            decoration: const InputDecoration(
              labelText: 'Server URL',
              hintText: 'http://your-server.com/api/sms',
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('Cancel'),
            ),
            TextButton(
              onPressed: () {
                Navigator.of(context).pop();
                setState(() {
                  _serverUrl = _urlController.text.trim();
                });
              },
              child: const Text('Save'),
            ),
          ],
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
        title: const Text('SMS Reader & Analyzer'),
        actions: [
          IconButton(
            icon: const Icon(Icons.settings),
            onPressed: _showServerUrlDialog,
            tooltip: 'Set Server URL',
          ),
        ],
      ),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Status card
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(
                          _hasPermission ? Icons.check_circle : Icons.error,
                          color: _hasPermission ? Colors.green : Colors.red,
                        ),
                        const SizedBox(width: 8),
                        Text(
                          'Status',
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Text(_statusMessage),
                    const SizedBox(height: 8),
                    Text(
                      'Server: $_serverUrl',
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ],
                ),
              ),
            ),
            
            const SizedBox(height: 16),
            
            // Action buttons
            Row(
              children: [
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: _isLoading ? null : _requestPermissions,
                    icon: const Icon(Icons.security),
                    label: const Text('Request Permission'),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: _isLoading || !_hasPermission ? null : _loadSmsMessages,
                    icon: const Icon(Icons.message),
                    label: const Text('Load SMS'),
                  ),
                ),
              ],
            ),
            
            const SizedBox(height: 8),
            
                         Row(
               children: [
                 Expanded(
                   child: ElevatedButton.icon(
                     onPressed: _isLoading || _smsMessages.isEmpty ? null : _sendToAnalyzer,
                     icon: const Icon(Icons.send),
                     label: const Text('Send to Server'),
                     style: ElevatedButton.styleFrom(
                       backgroundColor: Theme.of(context).colorScheme.primary,
                       foregroundColor: Theme.of(context).colorScheme.onPrimary,
                     ),
                   ),
                 ),
                 const SizedBox(width: 8),
                 Expanded(
                   child: ElevatedButton.icon(
                     onPressed: _isLoading || _smsMessages.isEmpty ? null : _categorizeMessages,
                     icon: const Icon(Icons.category),
                     label: const Text('Categorize SMS'),
                     style: ElevatedButton.styleFrom(
                       backgroundColor: Theme.of(context).colorScheme.secondary,
                       foregroundColor: Theme.of(context).colorScheme.onSecondary,
                     ),
                   ),
                 ),
               ],
             ),
            
            const SizedBox(height: 8),
            
            // Additional features row
            Row(
              children: [
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: _isLoading || _smsMessages.isEmpty ? null : _analyzeWithNlp,
                    icon: const Icon(Icons.psychology),
                    label: const Text('NLP Analysis'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Theme.of(context).colorScheme.tertiary,
                      foregroundColor: Theme.of(context).colorScheme.onTertiary,
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: _openBankSmsManager,
                    icon: const Icon(Icons.account_balance),
                    label: const Text('Bank SMS DB'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.green,
                      foregroundColor: Colors.white,
                    ),
                  ),
                ),
              ],
            ),
            
            const SizedBox(height: 16),
            
            // SMS list
            Expanded(
              child: _isLoading
                  ? const Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          CircularProgressIndicator(),
                          SizedBox(height: 16),
                          Text('Loading...'),
                        ],
                      ),
                    )
                  : _smsMessages.isEmpty
                      ? const Center(
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Icon(Icons.message_outlined, size: 64, color: Colors.grey),
                              SizedBox(height: 16),
                              Text('No SMS messages loaded'),
                              SizedBox(height: 8),
                              Text(
                                'Tap "Load SMS" to read messages from your device',
                                textAlign: TextAlign.center,
                                style: TextStyle(color: Colors.grey),
                              ),
                            ],
                          ),
                        )
                      : ListView.builder(
                          itemCount: _smsMessages.length,
                          itemBuilder: (context, index) {
                            final message = _smsMessages[index];
                            return Card(
                              margin: const EdgeInsets.only(bottom: 8),
                              child: ListTile(
                                leading: CircleAvatar(
                                  child: Text(
                                    message.address?.isNotEmpty == true
                                        ? message.address![0].toUpperCase()
                                        : '?',
                                  ),
                                ),
                                title: Text(
                                  message.address ?? 'Unknown',
                                  style: const TextStyle(fontWeight: FontWeight.bold),
                                ),
                                subtitle: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      message.body ?? '',
                                      maxLines: 2,
                                      overflow: TextOverflow.ellipsis,
                                    ),
                                    const SizedBox(height: 4),
                                    Text(
                                      message.formattedDate,
                                      style: TextStyle(
                                        fontSize: 12,
                                        color: Colors.grey[600],
                                      ),
                                    ),
                                  ],
                                ),
                                                                 trailing: Icon(
                                   message.type == 'inbox'
                                       ? Icons.call_received
                                       : Icons.call_made,
                                   color: message.type == 'inbox'
                                       ? Colors.green
                                       : Colors.blue,
                                 ),
                              ),
                            );
                          },
                        ),
            ),
          ],
        ),
      ),
    );
  }
}
