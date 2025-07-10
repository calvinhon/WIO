class SmsMessageModel {
  final int? id;
  final String? address;
  final String? body;
  final DateTime? date;
  final String? type; // 'inbox' or 'sent'
  final bool? read;
  final int? threadId;

  SmsMessageModel({
    this.id,
    this.address,
    this.body,
    this.date,
    this.type,
    this.read,
    this.threadId,
  });

  /// Create from platform channel data
  factory SmsMessageModel.fromPlatformMap(Map<String, dynamic> data) {
    return SmsMessageModel(
      id: data['id'],
      address: data['address'],
      body: data['body'],
      date: data['date'] != null ? DateTime.fromMillisecondsSinceEpoch(data['date']) : null,
      type: data['type'],
      read: data['read'],
      threadId: data['threadId'],
    );
  }

  // Convert to JSON for API transmission
  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'address': address,
      'body': body,
      'date': date?.millisecondsSinceEpoch,
      'type': type,
      'read': read,
      'threadId': threadId,
      'formattedDate': formattedDate,
    };
  }

  // Create from JSON
  factory SmsMessageModel.fromJson(Map<String, dynamic> json) {
    return SmsMessageModel(
      id: json['id'],
      address: json['address'],
      body: json['body'],
      date: json['date'] != null ? DateTime.fromMillisecondsSinceEpoch(json['date']) : null,
      type: json['type'],
      read: json['read'],
      threadId: json['threadId'],
    );
  }

  // Formatted date string
  String get formattedDate {
    if (date == null) return 'Unknown date';
    
    final now = DateTime.now();
    final difference = now.difference(date!);
    
    if (difference.inDays > 0) {
      return '${difference.inDays} day${difference.inDays > 1 ? 's' : ''} ago';
    } else if (difference.inHours > 0) {
      return '${difference.inHours} hour${difference.inHours > 1 ? 's' : ''} ago';
    } else if (difference.inMinutes > 0) {
      return '${difference.inMinutes} minute${difference.inMinutes > 1 ? 's' : ''} ago';
    } else {
      return 'Just now';
    }
  }

  // String representation for debugging
  @override
  String toString() {
    return 'SmsMessageModel(id: $id, address: $address, body: ${body?.substring(0, body!.length > 50 ? 50 : body!.length)}..., date: $date, type: $type)';
  }
} 