package com.example.sms_reader_app

import android.content.Context
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.io.BufferedReader
import java.io.InputStreamReader
import java.io.File
import java.io.FileWriter

class NlpProcessor(private val context: Context) {
    
    companion object {
        private const val PYTHON_SCRIPT = """
import json
import sys
import spacy
from collections import Counter
import re

def process_sms_messages(messages_json):
    try:
        # Load spaCy model (you'll need to install: python -m spacy download en_core_web_sm)
        nlp = spacy.load("en_core_web_sm")
        
        messages = json.loads(messages_json)
        results = {
            'sentiment_analysis': [],
            'entity_extraction': [],
            'keyword_analysis': {},
            'topic_modeling': [],
            'language_detection': [],
            'summary': {}
        }
        
        all_text = ""
        entities_by_type = {}
        sentiments = []
        
        for message in messages:
            text = message.get('body', '')
            if not text:
                continue
                
            all_text += text + " "
            
            # Process with spaCy
            doc = nlp(text)
            
            # Sentiment analysis (simple approach)
            sentiment = analyze_sentiment(text)
            sentiments.append(sentiment)
            results['sentiment_analysis'].append({
                'id': message.get('id'),
                'address': message.get('address'),
                'sentiment': sentiment,
                'confidence': get_sentiment_confidence(text)
            })
            
            # Entity extraction
            entities = []
            for ent in doc.ents:
                entities.append({
                    'text': ent.text,
                    'label': ent.label_,
                    'start': ent.start_char,
                    'end': ent.end_char
                })
                
                if ent.label_ not in entities_by_type:
                    entities_by_type[ent.label_] = []
                entities_by_type[ent.label_].append(ent.text)
            
            results['entity_extraction'].append({
                'id': message.get('id'),
                'entities': entities
            })
            
            # Language detection
            results['language_detection'].append({
                'id': message.get('id'),
                'language': doc.lang_
            })
        
        # Overall keyword analysis
        doc_all = nlp(all_text)
        keywords = [token.lemma_.lower() for token in doc_all 
                   if not token.is_stop and not token.is_punct and len(token.text) > 2]
        keyword_freq = Counter(keywords)
        
        results['keyword_analysis'] = {
            'top_keywords': [{'word': word, 'frequency': freq} 
                           for word, freq in keyword_freq.most_common(20)],
            'total_unique_words': len(keyword_freq)
        }
        
        # Summary statistics
        results['summary'] = {
            'total_messages': len(messages),
            'total_entities': sum(len(entities_by_type.get(label, [])) for label in entities_by_type),
            'entity_types': {label: len(entities) for label, entities in entities_by_type.items()},
            'sentiment_distribution': dict(Counter(sentiments)),
            'avg_message_length': sum(len(msg.get('body', '')) for msg in messages) / len(messages) if messages else 0
        }
        
        return json.dumps(results, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({'error': str(e)})

def analyze_sentiment(text):
    # Simple sentiment analysis - you can replace with more sophisticated models
    positive_words = ['good', 'great', 'excellent', 'amazing', 'wonderful', 'fantastic', 'awesome', 'perfect', 'love', 'happy', 'best', 'nice', 'beautiful', 'thank', 'thanks', 'congratulations']
    negative_words = ['bad', 'terrible', 'awful', 'horrible', 'worst', 'hate', 'angry', 'sad', 'disappointed', 'fail', 'problem', 'issue', 'error', 'wrong', 'broken', 'sorry']
    
    words = text.lower().split()
    positive_score = sum(1 for word in words if word in positive_words)
    negative_score = sum(1 for word in words if word in negative_words)
    
    if positive_score > negative_score:
        return 'positive'
    elif negative_score > positive_score:
        return 'negative'
    else:
        return 'neutral'

def get_sentiment_confidence(text):
    # Simple confidence calculation
    words = len(text.split())
    return min(1.0, max(0.3, words / 100.0))

if __name__ == "__main__":
    if len(sys.argv) > 1:
        messages_json = sys.argv[1]
        result = process_sms_messages(messages_json)
        print(result)
    else:
        print(json.dumps({'error': 'No messages provided'}))
"""
    }
    
    suspend fun processWithSpacy(messages: List<Map<String, Any?>>): Map<String, Any?> = withContext(Dispatchers.IO) {
        try {
            // Check if Python and spaCy are available
            if (!isPythonAvailable()) {
                throw Exception("Python is not available on this device")
            }
            
            // Create temporary Python script
            val scriptFile = File(context.cacheDir, "nlp_processor.py")
            scriptFile.writeText(PYTHON_SCRIPT)
            
            // Convert messages to JSON
            val jsonArray = JSONArray()
            for (message in messages) {
                val jsonObj = JSONObject()
                for ((key, value) in message) {
                    jsonObj.put(key, value)
                }
                jsonArray.put(jsonObj)
            }
            
            val messagesJson = jsonArray.toString()
            
            // Execute Python script
            val process = ProcessBuilder(
                "python3", scriptFile.absolutePath, messagesJson
            ).start()
            
            val result = process.inputStream.bufferedReader().use { it.readText() }
            val errorOutput = process.errorStream.bufferedReader().use { it.readText() }
            
            process.waitFor()
            
            if (process.exitValue() != 0) {
                throw Exception("Python script failed: $errorOutput")
            }
            
            // Parse JSON result
            val jsonResult = JSONObject(result)
            return@withContext jsonObjectToMap(jsonResult)
            
        } catch (e: Exception) {
            throw Exception("spaCy processing failed: ${e.message}")
        }
    }
    
    private fun isPythonAvailable(): Boolean {
        return try {
            val process = ProcessBuilder("python3", "--version").start()
            process.waitFor()
            process.exitValue() == 0
        } catch (e: Exception) {
            false
        }
    }
    
    private fun jsonObjectToMap(jsonObject: JSONObject): Map<String, Any?> {
        val map = mutableMapOf<String, Any?>()
        val keys = jsonObject.keys()
        
        while (keys.hasNext()) {
            val key = keys.next()
            val value = jsonObject.get(key)
            
            map[key] = when (value) {
                is JSONObject -> jsonObjectToMap(value)
                is JSONArray -> jsonArrayToList(value)
                else -> value
            }
        }
        
        return map
    }
    
    private fun jsonArrayToList(jsonArray: JSONArray): List<Any?> {
        val list = mutableListOf<Any?>()
        
        for (i in 0 until jsonArray.length()) {
            val value = jsonArray.get(i)
            
            list.add(when (value) {
                is JSONObject -> jsonObjectToMap(value)
                is JSONArray -> jsonArrayToList(value)
                else -> value
            })
        }
        
        return list
    }
} 