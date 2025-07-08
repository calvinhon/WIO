class BankSms {
  final int? id;
  final String address;
  final String body;
  final DateTime dateTime;
  final String category;
  final double confidence;
  final List<String> indicators;
  final DateTime createdAt;

  BankSms({
    this.id,
    required this.address,
    required this.body,
    required this.dateTime,
    required this.category,
    required this.confidence,
    required this.indicators,
    required this.createdAt,
  });

  // Convert a BankSms into a Map for database operations
  Map<String, dynamic> toMap() {
    return {
      'id': id,
      'address': address,
      'body': body,
      'dateTime': dateTime.millisecondsSinceEpoch,
      'category': category,
      'confidence': confidence,
      'indicators': indicators.join(','), // Store as comma-separated string
      'createdAt': createdAt.millisecondsSinceEpoch,
    };
  }

  // Convert a Map into a BankSms
  factory BankSms.fromMap(Map<String, dynamic> map) {
    return BankSms(
      id: map['id'],
      address: map['address'] ?? '',
      body: map['body'] ?? '',
      dateTime: DateTime.fromMillisecondsSinceEpoch(map['dateTime'] ?? 0),
      category: map['category'] ?? '',
      confidence: map['confidence']?.toDouble() ?? 0.0,
      indicators: map['indicators'] != null && map['indicators'].isNotEmpty
          ? map['indicators'].split(',')
          : [],
      createdAt: DateTime.fromMillisecondsSinceEpoch(map['createdAt'] ?? 0),
    );
  }

  // Create from existing SMS message and categorization result
  factory BankSms.fromCategorizedSms({
    required String address,
    required String body,
    required DateTime dateTime,
    required String category,
    required double confidence,
    required List<String> indicators,
  }) {
    return BankSms(
      address: address,
      body: body,
      dateTime: dateTime,
      category: category,
      confidence: confidence,
      indicators: indicators,
      createdAt: DateTime.now(),
    );
  }

  @override
  String toString() {
    return 'BankSms{id: \$id, address: \$address, body: \${body.substring(0, body.length > 50 ? 50 : body.length)}..., category: \$category, confidence: \$confidence}';
  }

  @override
  bool operator ==(Object other) {
    if (identical(this, other)) return true;
    return other is BankSms &&
        other.address == address &&
        other.body == body &&
        other.dateTime == dateTime;
  }

  @override
  int get hashCode {
    return address.hashCode ^ body.hashCode ^ dateTime.hashCode;
  }
}
