#!/usr/bin/env python3
"""
Demo SMS Analysis Server

A simple HTTP server that receives SMS data from the Flutter app
and demonstrates how to process the incoming data.

Usage:
    python demo_server.py

The server will run on http://localhost:8000/api/sms
Configure this URL in your Flutter app's settings.
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SMSAnalysisHandler(BaseHTTPRequestHandler):
    """HTTP request handler for SMS data analysis"""
    
    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, User-Agent')
        self.end_headers()
    
    def do_POST(self):
        """Handle POST requests with SMS data"""
        if self.path == '/api/sms':
            try:
                # Read the request body
                content_length = int(self.headers.get('Content-Length', 0))
                post_data = self.rfile.read(content_length)
                
                # Parse JSON data
                sms_data = json.loads(post_data.decode('utf-8'))
                
                # Process the SMS data
                self.analyze_sms_data(sms_data)
                
                # Send success response
                response = {
                    'status': 'success',
                    'message': 'SMS data received and processed',
                    'received_at': datetime.datetime.now().isoformat(),
                    'message_count': sms_data.get('sms_count', 0)
                }
                
                self.send_json_response(200, response)
                logger.info(f"Successfully processed {sms_data.get('sms_count', 0)} SMS messages")
                
            except json.JSONDecodeError as e:
                self.send_error_response(400, f"Invalid JSON: {str(e)}")
            except Exception as e:
                self.send_error_response(500, f"Server error: {str(e)}")
        else:
            self.send_error_response(404, "Endpoint not found")
    
    def do_HEAD(self):
        """Handle HEAD requests for connectivity testing"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
    
    def analyze_sms_data(self, data):
        """Analyze the received SMS data and print insights"""
        print("\n" + "="*60)
        print("📱 SMS DATA ANALYSIS REPORT")
        print("="*60)
        
        # Basic info
        print(f"📊 Timestamp: {data.get('timestamp', 'Unknown')}")
        print(f"📱 Device: {data.get('device_info', {}).get('platform', 'Unknown')} "
              f"{data.get('device_info', {}).get('platform_version', '')}")
        print(f"📩 Total Messages: {data.get('sms_count', 0)}")
        
        # Analyze messages if present
        messages = data.get('sms_messages', [])
        if messages:
            self.analyze_messages(messages)
        
        print("="*60)
    
    def analyze_messages(self, messages):
        """Perform detailed analysis of SMS messages"""
        print("\n📈 MESSAGE ANALYSIS:")
        
        # Count by type
        inbox_count = sum(1 for msg in messages if 'INBOX' in str(msg.get('type', '')))
        sent_count = sum(1 for msg in messages if 'SENT' in str(msg.get('type', '')))
        
        print(f"   📥 Inbox: {inbox_count}")
        print(f"   📤 Sent: {sent_count}")
        
        # Contact analysis
        contacts = {}
        total_chars = 0
        
        for msg in messages:
            address = msg.get('address', 'Unknown')
            if address in contacts:
                contacts[address] += 1
            else:
                contacts[address] = 1
            
            body = msg.get('body', '')
            total_chars += len(body)
        
        print(f"\n👥 CONTACT ANALYSIS:")
        print(f"   🔢 Unique contacts: {len(contacts)}")
        
        # Top 5 contacts
        top_contacts = sorted(contacts.items(), key=lambda x: x[1], reverse=True)[:5]
        print(f"   📊 Top contacts:")
        for i, (contact, count) in enumerate(top_contacts, 1):
            # Mask phone numbers for privacy
            masked_contact = self.mask_phone_number(contact)
            print(f"      {i}. {masked_contact}: {count} messages")
        
        # Content analysis
        avg_length = total_chars // len(messages) if messages else 0
        print(f"\n📝 CONTENT ANALYSIS:")
        print(f"   📏 Average message length: {avg_length} characters")
        print(f"   📊 Total characters: {total_chars}")
        
        # Simple keyword analysis
        self.analyze_keywords(messages)
    
    def analyze_keywords(self, messages):
        """Perform basic keyword analysis"""
        common_words = {}
        
        for msg in messages:
            body = msg.get('body', '').lower()
            words = body.split()
            
            for word in words:
                # Simple word cleaning
                word = ''.join(c for c in word if c.isalnum())
                if len(word) > 3:  # Only count words longer than 3 characters
                    common_words[word] = common_words.get(word, 0) + 1
        
        if common_words:
            print(f"\n🏷️ KEYWORD ANALYSIS:")
            top_words = sorted(common_words.items(), key=lambda x: x[1], reverse=True)[:10]
            print(f"   🔤 Most common words:")
            for i, (word, count) in enumerate(top_words, 1):
                print(f"      {i}. '{word}': {count} times")
    
    def mask_phone_number(self, phone):
        """Mask phone numbers for privacy"""
        if phone and len(phone) > 4:
            return phone[:2] + "*" * (len(phone) - 4) + phone[-2:]
        return phone
    
    def send_json_response(self, status_code, data):
        """Send a JSON response"""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        response_json = json.dumps(data, indent=2)
        self.wfile.write(response_json.encode('utf-8'))
    
    def send_error_response(self, status_code, message):
        """Send an error response"""
        error_data = {
            'status': 'error',
            'message': message,
            'timestamp': datetime.datetime.now().isoformat()
        }
        self.send_json_response(status_code, error_data)
        logger.error(f"Error {status_code}: {message}")

def run_server(port=8000):
    """Start the SMS analysis server"""
    server_address = ('', port)
    httpd = HTTPServer(server_address, SMSAnalysisHandler)
    
    print(f"\n🚀 SMS Analysis Server Starting...")
    print(f"📡 Server running on: http://localhost:{port}/api/sms")
    print(f"💡 Configure this URL in your Flutter app settings")
    print(f"🛑 Press Ctrl+C to stop the server\n")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
        httpd.server_close()

if __name__ == '__main__':
    run_server() 