#!/usr/bin/env python3
"""
SMS NLP Analysis Demo

This script demonstrates the kind of analysis your Flutter app can perform
on SMS messages using the built-in NLP capabilities.
"""

import json
from datetime import datetime

# Sample SMS messages for demonstration
sample_messages = [
    {
        "id": 1,
        "address": "+1234567890",
        "body": "Hey! Thanks for the amazing dinner last night. Had such a great time!",
        "date": 1641024000000,
        "type": "inbox"
    },
    {
        "id": 2,
        "address": "BANK-ALERT",
        "body": "Your payment of $25.99 to Netflix has been processed successfully. Account balance: $1,234.56",
        "date": 1641110400000,
        "type": "inbox"
    },
    {
        "id": 3,
        "address": "PROMO-DEALS",
        "body": "🎉 FLASH SALE! Get 50% off everything! Limited time offer - click here now!",
        "date": 1641196800000,
        "type": "inbox"
    },
    {
        "id": 4,
        "address": "+9876543210",
        "body": "Can you pick up milk on your way home? Meeting at 3pm tomorrow.",
        "date": 1641283200000,
        "type": "sent"
    },
    {
        "id": 5,
        "address": "DELIVERY-UPDATE",
        "body": "Your order #12345 has been shipped! Track at https://tracking.example.com",
        "date": 1641369600000,
        "type": "inbox"
    }
]

def analyze_sentiment_demo(text):
    """Demo sentiment analysis"""
    positive_words = ['great', 'amazing', 'thanks', 'successfully', 'sale']
    negative_words = ['problem', 'issue', 'failed', 'error', 'cancel']
    
    words = text.lower().split()
    pos_score = sum(1 for word in words if any(pw in word for pw in positive_words))
    neg_score = sum(1 for word in words if any(nw in word for nw in negative_words))
    
    if pos_score > neg_score:
        return {'sentiment': 'positive', 'confidence': 0.8}
    elif neg_score > pos_score:
        return {'sentiment': 'negative', 'confidence': 0.7}
    else:
        return {'sentiment': 'neutral', 'confidence': 0.6}

def categorize_message_demo(text):
    """Demo message categorization"""
    text_lower = text.lower()
    
    if any(word in text_lower for word in ['sale', 'offer', 'deal', 'discount', '50%']):
        return {'category': 'promotional', 'confidence': 0.9}
    elif any(word in text_lower for word in ['payment', 'balance', 'processed', 'order', 'shipped']):
        return {'category': 'transactional', 'confidence': 0.85}
    elif any(word in text_lower for word in ['hey', 'thanks', 'dinner', 'pick up', 'meeting']):
        return {'category': 'personal', 'confidence': 0.8}
    else:
        return {'category': 'notifications', 'confidence': 0.6}

def extract_entities_demo(text):
    """Demo entity extraction"""
    import re
    
    entities = {}
    
    # Phone numbers
    phone_pattern = r'\+?\d{10,15}'
    phones = re.findall(phone_pattern, text)
    if phones:
        entities['phone_numbers'] = phones
    
    # URLs
    url_pattern = r'https?://[^\s]+'
    urls = re.findall(url_pattern, text)
    if urls:
        entities['urls'] = urls
    
    # Money amounts
    money_pattern = r'\$\d+(?:\.\d{2})?'
    amounts = re.findall(money_pattern, text)
    if amounts:
        entities['amounts'] = amounts
    
    # Order numbers
    order_pattern = r'#\d+'
    orders = re.findall(order_pattern, text)
    if orders:
        entities['order_numbers'] = orders
    
    return entities

def run_nlp_demo():
    """Run complete NLP analysis demo"""
    print("🧠 SMS NLP ANALYSIS DEMO")
    print("=" * 50)
    
    # Initialize results
    sentiment_results = []
    category_results = []
    all_entities = {}
    word_frequency = {}
    
    print(f"\nAnalyzing {len(sample_messages)} sample SMS messages...\n")
    
    for i, message in enumerate(sample_messages, 1):
        print(f"📱 Message {i}: {message['address']}")
        print(f"   💬 \"{message['body'][:50]}{'...' if len(message['body']) > 50 else ''}\"")
        
        # Sentiment analysis
        sentiment = analyze_sentiment_demo(message['body'])
        sentiment_results.append(sentiment)
        print(f"   😊 Sentiment: {sentiment['sentiment']} ({sentiment['confidence']:.0%})")
        
        # Categorization
        category = categorize_message_demo(message['body'])
        category_results.append(category)
        print(f"   📂 Category: {category['category']} ({category['confidence']:.0%})")
        
        # Entity extraction
        entities = extract_entities_demo(message['body'])
        for entity_type, entity_list in entities.items():
            if entity_type not in all_entities:
                all_entities[entity_type] = []
            all_entities[entity_type].extend(entity_list)
            print(f"   🏷️  {entity_type}: {entity_list}")
        
        # Word frequency
        words = message['body'].lower().split()
        for word in words:
            word = ''.join(c for c in word if c.isalnum())
            if len(word) > 3:
                word_frequency[word] = word_frequency.get(word, 0) + 1
        
        print()
    
    # Summary statistics
    print("📊 ANALYSIS SUMMARY")
    print("-" * 30)
    
    # Sentiment distribution
    sentiment_dist = {}
    for result in sentiment_results:
        sentiment = result['sentiment']
        sentiment_dist[sentiment] = sentiment_dist.get(sentiment, 0) + 1
    
    print("😊 Sentiment Distribution:")
    for sentiment, count in sentiment_dist.items():
        percentage = (count / len(sample_messages)) * 100
        print(f"   {sentiment.title()}: {count} ({percentage:.0f}%)")
    
    # Category distribution
    category_dist = {}
    for result in category_results:
        category = result['category']
        category_dist[category] = category_dist.get(category, 0) + 1
    
    print("\n📂 Category Distribution:")
    for category, count in category_dist.items():
        print(f"   {category.title()}: {count}")
    
    # Entities found
    print("\n🏷️  Entities Extracted:")
    for entity_type, entities in all_entities.items():
        print(f"   {entity_type}: {len(entities)} found")
        for entity in entities[:3]:  # Show first 3
            print(f"      - {entity}")
    
    # Top keywords
    print("\n📝 Top Keywords:")
    sorted_words = sorted(word_frequency.items(), key=lambda x: x[1], reverse=True)
    for word, freq in sorted_words[:5]:
        print(f"   '{word}': {freq} times")
    
    print(f"\n✅ Analysis complete! Your Flutter app performs this automatically.")
    print("🚀 Try loading SMS messages and tapping 'Analyze with NLP'")

if __name__ == "__main__":
    run_nlp_demo() 