import 'dart:convert';
import 'dart:io';
import 'lib/models/sms_message_model.dart';
import 'lib/services/sms_categorizer_service.dart';

void main() async {
  print('🧪 SMS CATEGORIZATION ACCURACY TEST');
  print('=' * 50);
  
  await testBankSamples();
  await testCommonSamples();
  await testMixedAccuracy();
  testSpecificPatterns();
}

Future<void> testBankSamples() async {
  print('\n🏦 Testing Bank SMS Samples (synthetic_sms_samples.json)');
  print('-' * 40);
  
  try {
    final bankSamplesFile = File('synthetic_sms_samples.json');
    final bankSamplesJson = json.decode(await bankSamplesFile.readAsString()) as List;
    
    int correctBankClassifications = 0;
    int totalBankSamples = bankSamplesJson.length;
    
    for (int i = 0; i < bankSamplesJson.length; i++) {
      final sample = bankSamplesJson[i];
      final message = SmsMessageModel(
        id: i + 1,
        address: sample['sender'],
        body: sample['message'],
        date: DateTime.now(),
        type: 'inbox',
      );
      
      final category = SmsCategorizer.categorizeMessage(message);
      
      if (category.category == 'Bank') {
        correctBankClassifications++;
        print('✅ Bank message correctly identified: ${sample['sender']}');
        print('   Confidence: ${(category.confidence * 100).round()}%');
        print('   Indicators: ${category.indicators.take(2).join(', ')}...');
      } else {
        print('❌ Bank message misclassified as: ${category.category}');
        print('   Message: ${sample['message'].toString().substring(0, 50)}...');
      }
    }
    
    final accuracy = (correctBankClassifications / totalBankSamples * 100);
    print('\n📊 Bank Classification Results:');
    print('   Total samples: $totalBankSamples');
    print('   Correctly classified: $correctBankClassifications');
    print('   Accuracy: ${accuracy.toStringAsFixed(1)}%');
    
    if (accuracy == 100.0) {
      print('   🎉 PERFECT! 100% bank message accuracy achieved!');
    }
    
  } catch (e) {
    print('❌ Error testing bank samples: $e');
  }
}

Future<void> testCommonSamples() async {
  print('\n📱 Testing Common SMS Samples (synthetic_common_sms_samples.json)');
  print('-' * 40);
  
  try {
    final commonSamplesFile = File('synthetic_common_sms_samples.json');
    final commonSamplesJson = json.decode(await commonSamplesFile.readAsString()) as List;
    
    int falsePositiveBankClassifications = 0;
    int totalCommonSamples = commonSamplesJson.length;
    Map<String, int> categoryCounts = {};
    
    for (int i = 0; i < commonSamplesJson.length; i++) {
      final sample = commonSamplesJson[i];
      final message = SmsMessageModel(
        id: i + 1000,
        address: sample['sender'],
        body: sample['message'],
        date: DateTime.now(),
        type: 'inbox',
      );
      
      final category = SmsCategorizer.categorizeMessage(message);
      
      // Count categories
      categoryCounts[category.category] = (categoryCounts[category.category] ?? 0) + 1;
      
      if (category.category == 'Bank') {
        falsePositiveBankClassifications++;
        print('⚠️  FALSE POSITIVE: Common message classified as Bank');
        print('   Sender: ${sample['sender']}');
        print('   Message: ${sample['message'].toString().substring(0, 80)}...');
        print('   Confidence: ${(category.confidence * 100).round()}%');
        print('   Indicators: ${category.indicators.join(', ')}');
      } else {
        print('✅ ${category.category}: ${sample['sender']} (${(category.confidence * 100).round()}%)');
      }
    }
    
    print('\n📊 Common SMS Classification Results:');
    print('   Total samples: $totalCommonSamples');
    print('   False positive bank classifications: $falsePositiveBankClassifications');
    print('   Bank false positive rate: ${(falsePositiveBankClassifications / totalCommonSamples * 100).toStringAsFixed(1)}%');
    
    print('\n📂 Category Distribution:');
    categoryCounts.forEach((category, count) {
      final percentage = (count / totalCommonSamples * 100).toStringAsFixed(1);
      print('   $category: $count ($percentage%)');
    });
    
    if (falsePositiveBankClassifications == 0) {
      print('   🎉 EXCELLENT! Zero false positives for bank classification!');
    } else {
      print('   ⚠️  Warning: ${falsePositiveBankClassifications} false positives detected');
    }
    
  } catch (e) {
    print('❌ Error testing common samples: $e');
  }
}

Future<void> testMixedAccuracy() async {
  print('\n🔄 Testing Mixed Sample Accuracy');
  print('-' * 40);
  
  try {
    // Load both files
    final bankSamplesFile = File('synthetic_sms_samples.json');
    final commonSamplesFile = File('synthetic_common_sms_samples.json');
    
    final bankSamplesJson = json.decode(await bankSamplesFile.readAsString()) as List;
    final commonSamplesJson = json.decode(await commonSamplesFile.readAsString()) as List;
    
    // Create mixed list
    List<Map<String, dynamic>> allSamples = [];
    
    // Add bank samples with expected category
    for (final sample in bankSamplesJson) {
      allSamples.add({
        'data': sample,
        'expected_category': 'Bank',
      });
    }
    
    // Add common samples with expected category (not bank)
    for (final sample in commonSamplesJson) {
      allSamples.add({
        'data': sample,
        'expected_category': 'Not-Bank',
      });
    }
    
    // Shuffle for random testing
    allSamples.shuffle();
    
    int correctClassifications = 0;
    int bankTruePositives = 0;
    int bankFalsePositives = 0;
    int bankFalseNegatives = 0;
    int bankTrueNegatives = 0;
    
    for (int i = 0; i < allSamples.length; i++) {
      final testCase = allSamples[i];
      final sample = testCase['data'];
      final expected = testCase['expected_category'];
      
      final message = SmsMessageModel(
        id: i + 2000,
        address: sample['sender'],
        body: sample['message'],
        date: DateTime.now(),
        type: 'inbox',
      );
      
      final category = SmsCategorizer.categorizeMessage(message);
      final isClassifiedAsBank = category.category == 'Bank';
      final isActuallyBank = expected == 'Bank';
      
      if (isActuallyBank && isClassifiedAsBank) {
        bankTruePositives++;
        correctClassifications++;
      } else if (!isActuallyBank && !isClassifiedAsBank) {
        bankTrueNegatives++;
        correctClassifications++;
      } else if (!isActuallyBank && isClassifiedAsBank) {
        bankFalsePositives++;
      } else if (isActuallyBank && !isClassifiedAsBank) {
        bankFalseNegatives++;
      }
    }
    
    // Calculate metrics
    final totalSamples = allSamples.length;
    final overallAccuracy = (correctClassifications / totalSamples * 100);
    
    final precision = bankTruePositives / (bankTruePositives + bankFalsePositives);
    final recall = bankTruePositives / (bankTruePositives + bankFalseNegatives);
    final f1Score = 2 * (precision * recall) / (precision + recall);
    
    print('📊 Mixed Sample Test Results:');
    print('   Total samples: $totalSamples');
    print('   Overall accuracy: ${overallAccuracy.toStringAsFixed(1)}%');
    print('');
    print('🏦 Bank Detection Metrics:');
    print('   True Positives: $bankTruePositives');
    print('   False Positives: $bankFalsePositives');
    print('   True Negatives: $bankTrueNegatives');
    print('   False Negatives: $bankFalseNegatives');
    print('   Precision: ${(precision * 100).toStringAsFixed(1)}%');
    print('   Recall: ${(recall * 100).toStringAsFixed(1)}%');
    print('   F1-Score: ${(f1Score * 100).toStringAsFixed(1)}%');
    
    if (bankFalsePositives == 0 && bankFalseNegatives == 0) {
      print('   🏆 PERFECT CLASSIFICATION! 100% precision and recall!');
    } else if (bankFalsePositives == 0) {
      print('   ✅ ZERO FALSE POSITIVES - No common messages misclassified as bank!');
    }
    
  } catch (e) {
    print('❌ Error in mixed accuracy test: $e');
  }
}

// Simple test for individual patterns
void testSpecificPatterns() {
  print('\n🔍 Testing Specific Bank Patterns');
  print('-' * 40);
  
  final testCases = [
    'Your statement for card ending with 7551 is available. Total due AED 3954.16',
    'Emirates NBD Credit Card payment of AED 488.79 processed',
    'Thank you for the meeting yesterday', // Should NOT be bank
    'OTP 123456 expires in 10 minutes', // Should NOT be bank
    'Flash Sale! 50% off everything!', // Should NOT be bank
  ];
  
  for (int i = 0; i < testCases.length; i++) {
    final testText = testCases[i];
    final message = SmsMessageModel(
      id: 9990 + i,
      address: 'TEST',
      body: testText,
      date: DateTime.now(),
      type: 'inbox',
    );
    
    final category = SmsCategorizer.categorizeMessage(message);
    print('📝 "${testText.substring(0, 40)}..."');
    print('   → ${category.category} (${(category.confidence * 100).round()}%)');
  }
} 