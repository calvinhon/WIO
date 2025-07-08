import 'package:flutter/material.dart';
import '../models/sms_message_model.dart';
import '../services/nlp_service.dart';

class NlpAnalysisScreen extends StatefulWidget {
  final List<SmsMessageModel> messages;

  const NlpAnalysisScreen({super.key, required this.messages});

  @override
  State<NlpAnalysisScreen> createState() => _NlpAnalysisScreenState();
}

class _NlpAnalysisScreenState extends State<NlpAnalysisScreen> with TickerProviderStateMixin {
  final NlpService _nlpService = NlpService();
  late TabController _tabController;
  
  Map<String, dynamic>? _sentimentAnalysis;
  Map<String, dynamic>? _entityExtraction;
  Map<String, dynamic>? _categorization;
  Map<String, dynamic>? _keywordAnalysis;
  bool _isLoading = false;
  String? _error;
  bool _useSpacy = false;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 4, vsync: this);
    _performAnalysis();
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  Future<void> _performAnalysis() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      if (_useSpacy) {
        // Try spaCy first
        try {
          final spacyResults = await _nlpService.processWithSpacy(widget.messages);
          setState(() {
            _sentimentAnalysis = spacyResults['sentiment_analysis'];
            _entityExtraction = spacyResults['entity_extraction'];
            // spaCy results might have different structure
          });
        } catch (e) {
          // Fallback to Dart processing
          _useSpacy = false;
          await _performDartAnalysis();
        }
      } else {
        await _performDartAnalysis();
      }
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

  Future<void> _performDartAnalysis() async {
    final sentiment = await _nlpService.analyzeSentiment(widget.messages);
    final entities = await _nlpService.extractEntities(widget.messages);
    final categories = await _nlpService.categorizeMessages(widget.messages);
    final keywords = await _nlpService.extractKeywords(widget.messages);

    setState(() {
      _sentimentAnalysis = sentiment;
      _entityExtraction = entities;
      _categorization = categories;
      _keywordAnalysis = keywords;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('SMS Analysis'),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
        actions: [
          IconButton(
            icon: Icon(_useSpacy ? Icons.psychology : Icons.code),
            onPressed: () {
              setState(() {
                _useSpacy = !_useSpacy;
              });
              _performAnalysis();
            },
            tooltip: _useSpacy ? 'Using spaCy' : 'Using Dart NLP',
          ),
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _performAnalysis,
            tooltip: 'Refresh Analysis',
          ),
        ],
        bottom: TabBar(
          controller: _tabController,
          tabs: const [
            Tab(icon: Icon(Icons.sentiment_satisfied), text: 'Sentiment'),
            Tab(icon: Icon(Icons.category), text: 'Categories'),
            Tab(icon: Icon(Icons.search), text: 'Entities'),
            Tab(icon: Icon(Icons.text_fields), text: 'Keywords'),
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
                  Text('Analyzing SMS messages...'),
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
                      Text('Analysis failed: $_error'),
                      const SizedBox(height: 16),
                      ElevatedButton(
                        onPressed: _performAnalysis,
                        child: const Text('Retry'),
                      ),
                    ],
                  ),
                )
              : TabBarView(
                  controller: _tabController,
                  children: [
                    _buildSentimentTab(),
                    _buildCategoriesTab(),
                    _buildEntitiesTab(),
                    _buildKeywordsTab(),
                  ],
                ),
    );
  }

  Widget _buildSentimentTab() {
    if (_sentimentAnalysis == null) return const Center(child: Text('No sentiment data'));

    final summary = _sentimentAnalysis!['summary'] as Map<String, dynamic>;
    final detailed = _sentimentAnalysis!['detailed_results'] as List<dynamic>;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Summary Card
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Sentiment Overview',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  const SizedBox(height: 16),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                    children: [
                      _buildSentimentStat(
                        '😊 Positive',
                        summary['positive'].toString(),
                        '${summary['positive_percentage']}%',
                        Colors.green,
                      ),
                      _buildSentimentStat(
                        '😐 Neutral',
                        summary['neutral'].toString(),
                        '${100 - summary['positive_percentage'] - summary['negative_percentage']}%',
                        Colors.grey,
                      ),
                      _buildSentimentStat(
                        '😞 Negative',
                        summary['negative'].toString(),
                        '${summary['negative_percentage']}%',
                        Colors.red,
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
          
          const SizedBox(height: 16),
          
          // Detailed Results
          Text(
            'Message Details',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 8),
          
          ...detailed.map((item) => Card(
            margin: const EdgeInsets.only(bottom: 8),
            child: ListTile(
              leading: CircleAvatar(
                backgroundColor: _getSentimentColor(item['sentiment']),
                child: _getSentimentIcon(item['sentiment']),
              ),
              title: Text(item['address'] ?? 'Unknown'),
              subtitle: Text(item['body_preview'] ?? ''),
              trailing: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(
                    item['sentiment'].toUpperCase(),
                    style: TextStyle(
                      color: _getSentimentColor(item['sentiment']),
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  Text(
                    '${(item['confidence'] * 100).round()}%',
                    style: const TextStyle(fontSize: 12),
                  ),
                ],
              ),
            ),
          )).toList(),
        ],
      ),
    );
  }

  Widget _buildCategoriesTab() {
    if (_categorization == null) return const Center(child: Text('No categorization data'));

    final categories = _categorization!['categories'] as Map<String, dynamic>;
    final summary = _categorization!['summary'] as Map<String, dynamic>;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Summary
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Message Categories',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  const SizedBox(height: 16),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: summary.entries.map((entry) => Chip(
                      label: Text('${_getCategoryDisplayName(entry.key)}: ${entry.value}'),
                      backgroundColor: _getCategoryColor(entry.key).withOpacity(0.2),
                    )).toList(),
                  ),
                ],
              ),
            ),
          ),
          
          const SizedBox(height: 16),
          
          // Category Details
          ...categories.entries.where((entry) => (entry.value as List).isNotEmpty).map((entry) {
            final categoryMessages = entry.value as List<dynamic>;
            return ExpansionTile(
              leading: Icon(
                _getCategoryIcon(entry.key),
                color: _getCategoryColor(entry.key),
              ),
              title: Text('${_getCategoryDisplayName(entry.key)} (${categoryMessages.length})'),
              children: categoryMessages.map((msg) => ListTile(
                contentPadding: const EdgeInsets.only(left: 32, right: 16),
                title: Text(msg['address'] ?? 'Unknown'),
                subtitle: Text(msg['body_preview'] ?? ''),
                trailing: Text('${(msg['confidence'] * 100).round()}%'),
              )).toList(),
            );
          }).toList(),
        ],
      ),
    );
  }

  Widget _buildEntitiesTab() {
    if (_entityExtraction == null) return const Center(child: Text('No entity data'));

    final entities = _entityExtraction!['entities'] as Map<String, dynamic>;
    final counts = _entityExtraction!['counts'] as Map<String, dynamic>;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Extracted Entities',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 16),
          
          ...entities.entries.map((entry) {
            final entityList = entry.value as List<dynamic>;
            if (entityList.isEmpty) return const SizedBox.shrink();
            
            return Card(
              margin: const EdgeInsets.only(bottom: 16),
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(_getEntityIcon(entry.key)),
                        const SizedBox(width: 8),
                        Text(
                          '${_getEntityDisplayName(entry.key)} (${counts[entry.key]})',
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Wrap(
                      spacing: 4,
                      runSpacing: 4,
                      children: entityList.map((entity) => Chip(
                        label: Text(entity.toString()),
                        labelStyle: const TextStyle(fontSize: 12),
                      )).toList(),
                    ),
                  ],
                ),
              ),
            );
          }).toList(),
        ],
      ),
    );
  }

  Widget _buildKeywordsTab() {
    if (_keywordAnalysis == null) return const Center(child: Text('No keyword data'));

    final keywords = _keywordAnalysis!['top_keywords'] as List<dynamic>;
    final totalWords = _keywordAnalysis!['total_unique_words'] as int;

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
                  Text(
                    'Keyword Analysis',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  const SizedBox(height: 8),
                  Text('Total unique words: $totalWords'),
                ],
              ),
            ),
          ),
          
          const SizedBox(height: 16),
          
          Text(
            'Most Frequent Words',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 8),
          
          ...keywords.asMap().entries.map((entry) {
            final index = entry.key;
            final keyword = entry.value;
            final frequency = keyword['frequency'] as int;
            final maxFreq = keywords.first['frequency'] as int;
            final percentage = (frequency / maxFreq);
            
            return Card(
              margin: const EdgeInsets.only(bottom: 8),
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Row(
                  children: [
                    CircleAvatar(
                      radius: 12,
                      child: Text('${index + 1}'),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            keyword['word'],
                            style: const TextStyle(fontWeight: FontWeight.bold),
                          ),
                          const SizedBox(height: 4),
                          LinearProgressIndicator(
                            value: percentage,
                            backgroundColor: Colors.grey[300],
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 12),
                    Text(
                      frequency.toString(),
                      style: const TextStyle(fontWeight: FontWeight.bold),
                    ),
                  ],
                ),
              ),
            );
          }).toList(),
        ],
      ),
    );
  }

  Widget _buildSentimentStat(String label, String count, String percentage, Color color) {
    return Column(
      children: [
        Text(
          count,
          style: TextStyle(
            fontSize: 24,
            fontWeight: FontWeight.bold,
            color: color,
          ),
        ),
        Text(label),
        Text(
          percentage,
          style: TextStyle(color: color, fontWeight: FontWeight.bold),
        ),
      ],
    );
  }

  Color _getSentimentColor(String sentiment) {
    switch (sentiment) {
      case 'positive':
        return Colors.green;
      case 'negative':
        return Colors.red;
      default:
        return Colors.grey;
    }
  }

  Icon _getSentimentIcon(String sentiment) {
    switch (sentiment) {
      case 'positive':
        return const Icon(Icons.sentiment_very_satisfied, color: Colors.white);
      case 'negative':
        return const Icon(Icons.sentiment_very_dissatisfied, color: Colors.white);
      default:
        return const Icon(Icons.sentiment_neutral, color: Colors.white);
    }
  }

  Color _getCategoryColor(String category) {
    switch (category) {
      case 'promotional':
        return Colors.orange;
      case 'transactional':
        return Colors.blue;
      case 'personal':
        return Colors.green;
      case 'notifications':
        return Colors.purple;
      case 'spam':
        return Colors.red;
      default:
        return Colors.grey;
    }
  }

  IconData _getCategoryIcon(String category) {
    switch (category) {
      case 'promotional':
        return Icons.local_offer;
      case 'transactional':
        return Icons.receipt;
      case 'personal':
        return Icons.person;
      case 'notifications':
        return Icons.notifications;
      case 'spam':
        return Icons.warning;
      default:
        return Icons.category;
    }
  }

  String _getCategoryDisplayName(String category) {
    return category[0].toUpperCase() + category.substring(1);
  }

  IconData _getEntityIcon(String entityType) {
    switch (entityType) {
      case 'phone_numbers':
        return Icons.phone;
      case 'emails':
        return Icons.email;
      case 'urls':
        return Icons.link;
      case 'amounts':
        return Icons.attach_money;
      case 'dates':
        return Icons.calendar_today;
      default:
        return Icons.label;
    }
  }

  String _getEntityDisplayName(String entityType) {
    switch (entityType) {
      case 'phone_numbers':
        return 'Phone Numbers';
      case 'emails':
        return 'Email Addresses';
      case 'urls':
        return 'URLs';
      case 'amounts':
        return 'Amounts';
      case 'dates':
        return 'Dates';
      default:
        return entityType;
    }
  }
} 