# Local LLM Setup Guide for Password Generation

## Recommended Local LLM Tools

### 1. Ollama (Recommended)

 **Best for** : Ease of use, good performance, wide model support

#### Installation:

```bash
# macOS/Linux
curl -fsSL https://ollama.ai/install.sh | sh

# Windows
# Download from https://ollama.ai/download
```

#### Setup:

```bash
# Pull recommended model
ollama pull llama3.1:8b

# Start Ollama service
ollama serve

# Test the installation
curl http://localhost:11434/api/tags
```

#### Recommended Models:

* `llama3.1:8b` - Good balance of performance and accuracy
* `mistral:7b` - Faster, still good for text analysis
* `codellama:7b` - If you need more code understanding

### 2. LM Studio

 **Best for** : GUI interface, easy model management

#### Installation:

1. Download from https://lmstudio.ai/
2. Install the application
3. Start the local server from the interface

#### Setup:

1. Download a model through the LM Studio interface
2. Start the local server (usually on port 1234)
3. Configure the model in the server settings

#### Recommended Models:

* `microsoft/DialoGPT-medium`
* `meta-llama/Llama-2-7b-chat-hf`
* `microsoft/DialoGPT-large`

### 3. llama.cpp Server

 **Best for** : Maximum control, custom configurations

#### Installation:

```bash
# Clone repository
git clone https://github.com/ggerganov/llama.cpp
cd llama.cpp

# Build
make

# Download a model (example)
wget https://huggingface.co/TheBloke/Llama-2-7B-Chat-GGUF/resolve/main/llama-2-7b-chat.Q4_K_M.gguf
```

#### Setup:

```bash
# Start server
./server -m llama-2-7b-chat.Q4_K_M.gguf --port 8080 --host 0.0.0.0
```

## Configuration Files

### requirements.txt

```
requests>=2.31.0
sqlite3
PyPDF2>=3.0.1
python-dateutil>=2.8.2
pathlib>=1.0.1
logging>=0.4.9.6
```

### config.json

```json
{
  "llm_settings": {
    "primary_backend": "ollama",
    "fallback_backend": "lmstudio",
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
  "password_patterns": {
    "common_formats": [
      "DDMMYYYY",
      "MMDDYYYY",
      "YYYYMMDD",
      "last_4_digits",
      "first_name_last_4",
      "birth_date_variants"
    ],
    "bank_specific": {
      "fab": ["account_last_6", "card_last_4", "mobile_last_4"],
      "adcb": ["birth_date_ddmmyyyy", "card_last_4"],
      "enbd": ["mobile_last_4", "account_last_4"],
      "default": ["card_last_4", "birth_date_ddmmyyyy"]
    }
  }
}
```

## Bank-Specific Password Guidelines

### UAE Banks Common Patterns:

1. **FAB (First Abu Dhabi Bank)**
   * Usually: Last 6 digits of account number
   * Alternative: Last 4 digits of card + birth date (DDMM)
2. **ADCB (Abu Dhabi Commercial Bank)**
   * Usually: Birth date (DDMMYYYY)
   * Alternative: Last 4 digits of card number
3. **Emirates NBD**
   * Usually: Last 4 digits of mobile number
   * Alternative: Last 4 digits of account number
4. **ADIB (Abu Dhabi Islamic Bank)**
   * Usually: Birth date (DDMMYYYY)
   * Alternative: Last 4 digits of card
5. **Mashreq Bank**
   * Usually: Last 4 digits of card + birth year
   * Alternative: Mobile number last 4 digits

### General Password Rules:

* Length: Usually 4-12 characters
* Common formats: Numbers only, alphanumeric combinations
* Case sensitivity: Usually not case-sensitive
* Special characters: Rarely used

## Installation and Usage

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Setup Local LLM (Choose one)

#### Option A: Ollama (Recommended)

```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Pull model
ollama pull llama3.1:8b

# Start service
ollama serve
```

#### Option B: LM Studio

1. Download and install LM Studio
2. Download a chat model through the interface
3. Start the local server

### 3. Configure Personal Data

```python
# Update the setup_personal_data function with your actual data
personal_data = [
    ('first_name', 'YourFirstName', 'First name'),
    ('last_name', 'YourLastName', 'Last name'),
    ('birth_date', 'DD/MM/YYYY', 'Date of birth'),
    ('mobile_number', '971XXXXXXXXX', 'Mobile number'),
    # Add more personal data as needed
]
```

### 4. Run the Password Generator

```python
python password_generator.py
```

## Security Considerations

### Data Privacy:

* All processing happens locally
* No data sent to external servers
* Email content stays on your machine
* Generated passwords are stored locally

### Security Best Practices:

1. Use encrypted database storage
2. Implement secure password testing
3. Log all password attempts
4. Use secure connections for LLM APIs
5. Regularly update models and dependencies

### Database Security:

```python
# Add to your database initialization
def init_secure_db(db_path, password):
    # Use SQLCipher for encrypted SQLite
    conn = sqlite3.connect(db_path)
    conn.execute(f"PRAGMA key = '{password}'")
    # Rest of your database initialization
```

## Performance Optimization

### Model Selection:

* **Speed** : Use 7B parameter models
* **Accuracy** : Use 13B+ parameter models
* **Memory** : 7B models need ~8GB RAM, 13B need ~16GB

### Inference Optimization:

* Use GPU acceleration if available
* Batch process multiple emails
* Cache model responses for similar patterns
* Use quantized models for faster inference

## Troubleshooting

### Common Issues:

1. **LLM Service Not Available**
   * Check if the service is running
   * Verify correct port configuration
   * Test with curl/browser
2. **Model Download Issues**
   * Ensure sufficient disk space
   * Check internet connection
   * Try alternative model sources
3. **Poor Password Generation**
   * Verify personal data is correctly configured
   * Check if email content is properly extracted
   * Adjust confidence thresholds
4. **Database Errors**
   * Ensure proper database permissions
   * Check SQLite version compatibility
   * Verify database file path

### Debug Mode:

```python
# Enable verbose logging
logging.basicConfig(level=logging.DEBUG)

# Test LLM connectivity
llm = LocalLLMManager("ollama", "llama3.1:8b")
print(f"LLM Available: {llm.is_available()}")
```

## Advanced Features

### Custom Password Rules:

```python
# Add custom rules for specific banks
custom_rules = {
    'bank_name': {
        'patterns': ['custom_pattern_1', '
```
