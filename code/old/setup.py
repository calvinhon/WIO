#!/usr/bin/env python3
"""
Installation and Setup Script for Gmail PDF Password Generator
"""

import os
import sys
import subprocess
import sqlite3
import json
import requests
import time
from datetime import datetime
from pathlib import Path

class SetupManager:
    def __init__(self):
        self.base_dir = Path.cwd()
        self.config_file = self.base_dir / "config.json"
        self.requirements_file = self.base_dir / "requirements.txt"
        self.db_path = self.base_dir / "email_data.db"
        
    def check_python_version(self):
        """Check if Python version is compatible"""
        if sys.version_info < (3, 8):
            print("❌ Python 3.8 or higher is required")
            sys.exit(1)
        print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected")
    
    def create_requirements_file(self):
        """Create requirements.txt file"""
        requirements = [
            "requests>=2.31.0",
            "google-auth>=2.22.0",
            "google-auth-oauthlib>=1.0.0",
            "google-auth-httplib2>=0.1.0",
            "google-api-python-client>=2.100.0",
            "PyPDF2>=3.0.1",
            "python-dateutil>=2.8.2",
            "flask>=2.3.2",
            "psutil>=5.9.5",
            "cryptography>=41.0.3"
        ]
        
        with open(self.requirements_file, 'w') as f:
            f.write('\n'.join(requirements))
        
        print(f"✅ Created {self.requirements_file}")
    
    def install_python_dependencies(self):
        """Install Python dependencies"""
        print("📦 Installing Python dependencies...")
        try:
            subprocess.run([
                sys.executable, "-m", "pip", "install", "-r", str(self.requirements_file)
            ], check=True, capture_output=True)
            print("✅ Python dependencies installed successfully")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install dependencies: {e}")
            sys.exit(1)
    
    def detect_os(self):
        """Detect operating system"""
        if sys.platform.startswith('linux'):
            return 'linux'
        elif sys.platform.startswith('darwin'):
            return 'macos'
        elif sys.platform.startswith('win'):
            return 'windows'
        else:
            return 'unknown'
    
    def install_ollama(self):
        """Install Ollama based on OS"""
        os_type = self.detect_os()
        
        if os_type in ['linux', 'macos']:
            print("🚀 Installing Ollama...")
            try:
                subprocess.run([
                    'curl', '-fsSL', 'https://ollama.ai/install.sh'
                ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                
                # Execute the install script
                subprocess.run(['sh', '-c', 'curl -fsSL https://ollama.ai/install.sh | sh'], 
                             check=True, capture_output=True)
                print("✅ Ollama installed successfully")
                
            except subprocess.CalledProcessError as e:
                print(f"❌ Failed to install Ollama: {e}")
                print("Please install Ollama manually from https://ollama.ai/")
                
        elif os_type == 'windows':
            print("🚀 Please download and install Ollama from https://ollama.ai/download")
            print("After installation, run 'ollama serve' in a separate command prompt")
            
        else:
            print("❌ Unsupported operating system for automatic Ollama installation")
            print("Please visit https://ollama.ai/ for manual installation")
    
    def setup_ollama_model(self):
        """Setup Ollama model"""
        print("🤖 Setting up Ollama model...")
        
        # Start Ollama service
        try:
            subprocess.Popen(['ollama', 'serve'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            time.sleep(5)  # Wait for service to start
        except FileNotFoundError:
            print("❌ Ollama not found. Please install Ollama first.")
            return False
        
        # Check if service is running
        try:
            response = requests.get('http://localhost:11434/api/tags', timeout=5)
            if response.status_code != 200:
                print("❌ Ollama service not running")
                return False
        except requests.exceptions.RequestException:
            print("❌ Cannot connect to Ollama service")
            return False
        
        # Pull recommended model
        try:
            print("📥 Downloading llama3.1:8b model (this may take a while)...")
            subprocess.run(['ollama', 'pull', 'llama3.1:8b'], check=True)
            print("✅ Model downloaded successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to download model: {e}")
            return False
    
    def create_config_file(self):
        """Create configuration file"""
        config = {
            "llm_settings": {
                "primary_backend": "ollama",
                "fallback_backend": "rule_based",
                "models": {
                    "ollama": "llama3.1:8b",
                    "lmstudio": "llama-3.1-8b-instruct",
                    "llamacpp": "llama-3.1-8b-instruct"
                },
                "endpoints": {
                    "ollama": "http://localhost:11434",
                    "lmstudio": "http://localhost:1234",
                    "llamacpp": "http://localhost:8080"
                }
            },
            "generation_settings": {
                "max_tokens": 500,
                "temperature": 0.1,
                "top_candidates": 20,
                "confidence_threshold": 5.0
            },
            "database_settings": {
                "db_path": str(self.db_path),
                "backup_enabled": True,
                "backup_interval_hours": 24
            },
            "security_settings": {
                "encrypt_database": False,
                "log_password_attempts": True,
                "max_password_attempts": 50
            }
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"✅ Created {self.config_file}")
    
    def setup_database(self):
        """Setup initial database"""
        print("🗄️  Setting up database...")
        
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Create emails table
        c.execute('''
            CREATE TABLE IF NOT EXISTS emails (
                id TEXT PRIMARY KEY,
                subject TEXT,
                sender TEXT,
                date TEXT,
                snippet TEXT,
                password_hints TEXT,
                password_rules TEXT,
                attachments TEXT,
                timestamp INTEGER,
                email_body TEXT,
                processed_date TEXT
            )
        ''')
        
        # Create personal data table
        c.execute('''
            CREATE TABLE IF NOT EXISTS personal_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data_type TEXT,
                data_value TEXT,
                description TEXT,
                created_date TEXT
            )
        ''')
        
        # Create password candidates table
        c.execute('''
            CREATE TABLE IF NOT EXISTS password_candidates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email_id TEXT,
                password TEXT,
                confidence REAL,
                source TEXT,
                reasoning TEXT,
                tested BOOLEAN DEFAULT 0,
                works BOOLEAN DEFAULT 0,
                created_date TEXT,
                FOREIGN KEY (email_id) REFERENCES emails (id)
            )
        ''')
        
        # Create audit log table
        c.execute('''
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email_id TEXT,
                action TEXT,
                details TEXT,
                timestamp TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
        
        print(f"✅ Database setup complete: {self.db_path}")
    
    def create_personal_data_template(self):
        """Create a template for personal data"""
        template_file = self.base_dir / "personal_data_template.py"
        
        template_content = '''#!/usr/bin/env python3
"""
Personal Data Template for Password Generation
Fill in your actual data and run this script to populate the database.
"""

import sqlite3
from datetime import datetime

def setup_personal_data(db_path='email_data.db'):
    """Setup personal data for password generation"""
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # REPLACE WITH YOUR ACTUAL DATA
    personal_data = [
        # Names
        ('first_name', 'John', 'Your first name'),
        ('last_name', 'Doe', 'Your last name'),
        ('middle_name', 'Michael', 'Your middle name (if applicable)'),
        
        # Dates
        ('birth_date', '15/03/1990', 'Date of birth DD/MM/YYYY'),
        ('birth_date', '15031990', 'Date of birth DDMMYYYY'),
        ('birth_date', '03/15/1990', 'Date of birth MM/DD/YYYY'),
        ('birth_date', '03151990', 'Date of birth MMDDYYYY'),
        ('birth_date', '1990/03/15', 'Date of birth YYYY/MM/DD'),
        ('birth_date', '19900315', 'Date of birth YYYYMMDD'),
        
        # Contact information
        ('mobile_number', '971501234567', 'Mobile number with country code'),
        ('mobile_number', '0501234567', 'Mobile number without country code'),
        ('mobile_number', '1234', 'Last 4 digits of mobile'),
        
        # Financial information
        ('card_last_4', '1234', 'Credit card last 4 digits - Card 1'),
        ('card_last_4', '5678', 'Credit card last 4 digits - Card 2'),
        ('account_number', '987654', 'Account number last 6 digits'),
        ('account_number', '4321', 'Account number last 4 digits'),
        
        # Emirates ID
        ('emirates_id', '784-1990-1234567-8', 'Emirates ID full'),
        ('emirates_id', '1234567', 'Emirates ID last 7 digits'),
        
        # Common password components
        ('common_password', 'password123', 'Common password you might use'),
        ('common_pattern', 'name1990', 'Common pattern: name + birth year'),
        
        # Family information (if used in passwords)
        ('spouse_name', 'Jane', 'Spouse first name'),
        ('child_name', 'Alex', 'Child name'),
        
        # Work information
        ('employee_id', 'EMP001', 'Employee ID'),
        ('company_name', 'CompanyABC', 'Company name'),
        
        # Other personal info
        ('passport_last_4', '9876', 'Passport last 4 digits'),
        ('license_last_4', '5432', 'License last 4 digits'),
    ]
    
    print("Adding personal data to database...")
    for data_type, value, description in personal_data:
        c.execute('''
            INSERT OR REPLACE INTO personal_data (data_type, data_value, description, created_date)
            VALUES (?, ?, ?, ?)
        ''', (data_type, value, description, datetime.now().isoformat()))
    
    conn.commit()
    conn.close()
    print(f"✅ Added {len(personal_data)} personal data entries")
    print("⚠️  Remember to keep this information secure!")

if __name__ == "__main__":
    print("⚠️  WARNING: This script contains sensitive personal information!")
    print("Make sure to:")
    print("1. Replace the template data with your actual information")
    print("2. Keep this file secure and never share it")
    print("3. Consider deleting this file after running it")
    print()
    
    confirm = input("Do you want to proceed? (yes/no): ").lower().strip()
    if confirm == 'yes':
        setup_personal_data()
    else:
        print("Setup cancelled.")
'''
        
        with open(template_file, 'w') as f:
            f.write(template_content)
        
        print(f"✅ Created {template_file}")
        print("📝 Edit this file with your personal data, then run it")
    
    def create_startup_script(self):
        """Create a startup script"""
        startup_script = self.base_dir / "start_password_generator.py"
        
        startup_content = '''#!/usr/bin/env python3
"""
Startup script for Gmail PDF Password Generator
"""

import sys
import subprocess
import time
import requests
import json
from pathlib import Path

def check_ollama_service():
    """Check if Ollama service is running"""
    try:
        response = requests.get('http://localhost:11434/api/tags', timeout=5)
        return response.status_code == 200
    except:
        return False

def start_ollama():
    """Start Ollama service"""
    print("🚀 Starting Ollama service...")
    try:
        subprocess.Popen(['ollama', 'serve'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        time.sleep(5)
        return check_ollama_service()
    except:
        return False

def main():
    print("Gmail PDF Password Generator")
    print("=" * 40)
    
    # Check if Ollama is running
    if not check_ollama_service():
        print("📡 Ollama service not detected, starting...")
        if not start_ollama():
            print("❌ Failed to start Ollama service")
            print("Please start Ollama manually: ollama serve")
            return
    
    print("✅ Ollama service is running")
    
    # Load configuration
    config_file = Path("config.json")
    if not config_file.exists():
        print("❌ Configuration file not found")
        print("Please run the setup script first")
        return
    
    with open(config_file) as f:
        config = json.load(f)
    
    # Import and run the password generator
    try:
        from password_generator import PasswordGeneratorLLM, setup_personal_data
        
        print("🔐 Initializing password generator...")
        generator = PasswordGeneratorLLM(config['database_settings']['db_path'])
        
        print("📧 Processing emails...")
        generator.process_all_emails()
        
        print("✅ Password generation complete!")
        print("Check the database for generated password candidates")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure all dependencies are installed")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
'''
        
        with open(startup_script, 'w') as f:
            f.write(startup_content)
        
        # Make it executable on Unix systems
        if sys.platform != 'win32':
            os.chmod(startup_script, 0o755)
        
        print(f"✅ Created {startup_script}")
    
    def run_setup(self):
        """Run the complete setup process"""
        print("Gmail PDF Password Generator Setup")
        print("=" * 40)
        
        # Step 1: Check Python version
        self.check_python_version()
        
        # Step 2: Create requirements file
        self.create_requirements_file()
        
        # Step 3: Install Python dependencies
        self.install_python_dependencies()
        
        # Step 4: Install Ollama
        self.install_ollama()
        
        # Step 5: Setup Ollama model
        self.setup_ollama_model()
        
        # Step 6: Create configuration file
        self.create_config_file()
        
        # Step 7: Setup database
        self.setup_database()
        
        # Step 8: Create personal data template
        self.create_personal_data_template()
        
        # Step 9: Create startup script
        self.create_startup_script()
        
        print("\n🎉 Setup complete!")
        print("\nNext steps:")
        print("1. Edit 'personal_data_template.py' with your actual data")
        print("2. Run: python personal_data_template.py")
        print("3. Run: python start_password_generator.py")
        print("\n⚠️  Security reminders:")
        print("- Keep your personal data secure")
        print("- Regularly backup your database")
        print("- Monitor password generation results")

def main():
    if len(sys.argv) > 1 and sys.argv[1] == '--help':
        print("Gmail PDF Password Generator Setup Script")
        print("Usage: python setup.py")
        print("\nThis script will:")
        print("- Install Python dependencies")
        print("- Install and configure Ollama")
        print("- Set up the database")
        print("- Create configuration files")
        return
    
    setup_manager = SetupManager()
    setup_manager.run_setup()

if __name__ == "__main__":
    main()