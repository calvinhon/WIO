import 'package:flutter/services.dart';
import '../models/sms_message_model.dart';

class NlpService {
  static const MethodChannel _channel = MethodChannel('com.example.sms_reader/nlp');

  /// Process SMS messages using spaCy via platform channels
  Future<Map<String, dynamic>> processWithSpacy(List<SmsMessageModel> messages) async {
    try {
      final List<Map<String, dynamic>> messagesJson = messages.map((msg) => msg.toJson()).toList();
      
      final Map<dynamic, dynamic> result = await _channel.invokeMethod('processWithSpacy', {
        'messages': messagesJson,
      });
      
      return Map<String, dynamic>.from(result);
    } catch (e) {
      throw Exception('Failed to process SMS with spaCy: $e');
    }
  }

  /// Simple Dart-based NLP processing (fallback)
  Future<Map<String, dynamic>> processWithDart(List<SmsMessageModel> messages) async {
    try {
      final analysis = await _performDartNlpAnalysis(messages);
      return analysis;
    } catch (e) {
      throw Exception('Failed to process SMS with Dart NLP: $e');
    }
  }

  /// Sentiment analysis using on-device processing
  Future<Map<String, dynamic>> analyzeSentiment(List<SmsMessageModel> messages) async {
    final sentimentResults = <String, dynamic>{};
    
    int positiveCount = 0;
    int negativeCount = 0;
    int neutralCount = 0;
    
    final List<Map<String, dynamic>> detailedResults = [];
    
    for (final message in messages) {
      final sentiment = _analyzeSentimentDart(message.body ?? '');
      
      detailedResults.add({
        'id': message.id,
        'address': message.address,
        'sentiment': sentiment['label'],
        'confidence': sentiment['confidence'],
        'body_preview': message.body?.substring(0, message.body!.length > 50 ? 50 : message.body!.length),
      });
      
      switch (sentiment['label']) {
        case 'positive':
          positiveCount++;
          break;
        case 'negative':
          negativeCount++;
          break;
        default:
          neutralCount++;
      }
    }
    
    return {
      'summary': {
        'total_messages': messages.length,
        'positive': positiveCount,
        'negative': negativeCount,
        'neutral': neutralCount,
        'positive_percentage': (positiveCount / messages.length * 100).round(),
        'negative_percentage': (negativeCount / messages.length * 100).round(),
      },
      'detailed_results': detailedResults,
    };
  }

  /// Extract entities (phone numbers, dates, etc.)
  Future<Map<String, dynamic>> extractEntities(List<SmsMessageModel> messages) async {
    final entities = <String, Set<String>>{
      'phone_numbers': {},
      'dates': {},
      'urls': {},
      'emails': {},
      'amounts': {},
    };
    
    for (final message in messages) {
      final body = message.body ?? '';
      
      // Extract phone numbers
      final phoneRegex = RegExp(r'\+?1?\d{9,15}');
      entities['phone_numbers']!.addAll(
        phoneRegex.allMatches(body).map((match) => match.group(0)!)
      );
      
      // Extract URLs
      final urlRegex = RegExp(r'https?://[^\s]+');
      entities['urls']!.addAll(
        urlRegex.allMatches(body).map((match) => match.group(0)!)
      );
      
      // Extract email addresses
      final emailRegex = RegExp(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b');
      entities['emails']!.addAll(
        emailRegex.allMatches(body).map((match) => match.group(0)!)
      );
      
      // Extract amounts (currency)
      final amountRegex = RegExp(r'[\$€£¥]\d+(?:\.\d{2})?|\d+(?:\.\d{2})?\s*(?:USD|EUR|GBP|JPY)');
      entities['amounts']!.addAll(
        amountRegex.allMatches(body).map((match) => match.group(0)!)
      );
    }
    
    return {
      'entities': entities.map((key, value) => MapEntry(key, value.toList())),
      'counts': entities.map((key, value) => MapEntry(key, value.length)),
    };
  }

  /// Categorize messages
  Future<Map<String, dynamic>> categorizeMessages(List<SmsMessageModel> messages) async {
    final categories = <String, List<Map<String, dynamic>>>{
      'promotional': [],
      'transactional': [],
      'personal': [],
      'notifications': [],
      'spam': [],
      'other': [],
    };
    
    for (final message in messages) {
      final category = _categorizeMessage(message.body ?? '');
      categories[category]!.add({
        'id': message.id,
        'address': message.address,
        'body_preview': message.body?.substring(0, message.body!.length > 100 ? 100 : message.body!.length),
        'confidence': _getCategoryConfidence(message.body ?? '', category),
      });
    }
    
    return {
      'categories': categories,
      'summary': categories.map((key, value) => MapEntry(key, value.length)),
    };
  }

  /// Keyword extraction and frequency analysis
  Future<Map<String, dynamic>> extractKeywords(List<SmsMessageModel> messages) async {
    final wordFrequency = <String, int>{};
    final stopWords = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them', 'my', 'your', 'his', 'her', 'its', 'our', 'their', 'a', 'an'};
    
    for (final message in messages) {
      final words = (message.body ?? '').toLowerCase()
          .replaceAll(RegExp(r'[^\w\s]'), '')
          .split(' ')
          .where((word) => word.length > 2 && !stopWords.contains(word));
      
      for (final word in words) {
        wordFrequency[word] = (wordFrequency[word] ?? 0) + 1;
      }
    }
    
    // Sort by frequency
    final sortedWords = wordFrequency.entries.toList()
      ..sort((a, b) => b.value.compareTo(a.value));
    
    return {
      'top_keywords': sortedWords.take(20).map((entry) => {
        'word': entry.key,
        'frequency': entry.value,
      }).toList(),
      'total_unique_words': wordFrequency.length,
    };
  }

  // Private helper methods
  Future<Map<String, dynamic>> _performDartNlpAnalysis(List<SmsMessageModel> messages) async {
    final results = <String, dynamic>{};
    
    // Combine all analyses
    results['sentiment'] = await analyzeSentiment(messages);
    results['entities'] = await extractEntities(messages);
    results['categories'] = await categorizeMessages(messages);
    results['keywords'] = await extractKeywords(messages);
    
    return results;
  }

  Map<String, dynamic> _analyzeSentimentDart(String text) {
    final positiveWords = ['good', 'great', 'excellent', 'amazing', 'wonderful', 'fantastic', 'awesome', 'perfect', 'love', 'happy', 'best', 'nice', 'beautiful', 'congratulations', 'success', 'win', 'won', 'thank', 'thanks'];
    final negativeWords = ['bad', 'terrible', 'awful', 'horrible', 'worst', 'hate', 'angry', 'sad', 'disappointed', 'fail', 'failed', 'problem', 'issue', 'error', 'wrong', 'broken', 'cancel', 'cancelled', 'sorry', 'apologize'];
    
    final words = text.toLowerCase().split(' ');
    int positiveScore = 0;
    int negativeScore = 0;
    
    for (final word in words) {
      if (positiveWords.contains(word)) positiveScore++;
      if (negativeWords.contains(word)) negativeScore++;
    }
    
    String label = 'neutral';
    double confidence = 0.5;
    
    if (positiveScore > negativeScore) {
      label = 'positive';
      confidence = (positiveScore / (positiveScore + negativeScore + 1)).clamp(0.5, 1.0);
    } else if (negativeScore > positiveScore) {
      label = 'negative';
      confidence = (negativeScore / (positiveScore + negativeScore + 1)).clamp(0.5, 1.0);
    }
    
    return {
      'label': label,
      'confidence': confidence,
      'positive_score': positiveScore,
      'negative_score': negativeScore,
    };
  }

  String _categorizeMessage(String text) {
    final lower = text.toLowerCase();
    
    // Promotional keywords
    if (lower.contains(RegExp(r'\b(offer|sale|discount|deal|promo|coupon|free|save|limited|exclusive)\b'))) {
      return 'promotional';
    }
    
    // Transactional keywords
    if (lower.contains(RegExp(r'\b(payment|transaction|receipt|invoice|order|shipped|delivered|confirm|otp|code|verify)\b'))) {
      return 'transactional';
    }
    
    // Notification keywords
    if (lower.contains(RegExp(r'\b(alert|reminder|notification|update|news|info|announcement)\b'))) {
      return 'notifications';
    }
    
    // Spam indicators
    if (lower.contains(RegExp(r'\b(click here|act now|urgent|winner|prize|lottery|loan|credit|debt)\b'))) {
      return 'spam';
    }
    
    // Default to personal if none of the above
    return 'personal';
  }

  double _getCategoryConfidence(String text, String category) {
    // Simple confidence scoring based on keyword matches
    final keywords = _getCategoryKeywords(category);
    final matches = keywords.where((keyword) => 
      text.toLowerCase().contains(keyword.toLowerCase())).length;
    
    return (matches / keywords.length).clamp(0.3, 1.0);
  }

  List<String> _getCategoryKeywords(String category) {
    switch (category) {
      case 'promotional':
        return ['offer', 'sale', 'discount', 'deal', 'promo', 'coupon', 'free', 'save'];
      case 'transactional':
        return ['payment', 'transaction', 'receipt', 'invoice', 'order', 'shipped', 'delivered'];
      case 'notifications':
        return ['alert', 'reminder', 'notification', 'update', 'news', 'info'];
      case 'spam':
        return ['click here', 'act now', 'urgent', 'winner', 'prize', 'lottery'];
      default:
        return ['personal', 'friend', 'family', 'message'];
    }
  }
} 