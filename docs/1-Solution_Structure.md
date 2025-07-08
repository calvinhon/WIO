Based on the problem statement, here is HAAC's curated list of **AI-based tools and frameworks** to build a **privacy-preserving, smart, and responsive mobile app** for both SMS and email-based financial parsing and to notify users of pending due dates and associated payment amounts.

---

### 🔶 **Challenge 1: SMS Parsing for Due Dates and Payments**

#### 1. **On-Device NLP for SMS Parsing**

* ✅ **spaCy (with custom patterns)** — fast, lightweight, easy to customize.
* ✅ **HuggingFace Transformers (MiniLM / DistilBERT)** — supports fine-tuned LLMs on SMS-like text.

#### 2. **Testing New SMS Formats**

* ✅ **Few-shot prompting with open-sourced LLM** — to label a and b (due date, total) on SMS formats.

#### 3. **Storage**

* ✅ **SQLite or Room (Android)** — privacy-first local storage.

---

### 🔶 **Challenge 2: Email PDF/HTML Parsing for Spend and Bill Payment Insights**

#### 1. **Email Access (Gmail/Outlook)**

* ✅ **Google Gmail API** — via OAuth2 for read-only access.
* ✅ **Microsoft Graph API** — for Outlook users.

#### 2. **PDF Parsing**

* ✅ **PyMuPDF** — to parse PDFs.
* ✅ **Tesseract OCR** — for scanned/image-only PDFs.

#### 3. **Password Handling**
* ✅ **PikePDF** — to open PDFs.
* ✅ **Heuristic passwords** - try combinations of DOB, email, last 4 digits of card
* ✅ **User prompt fallback** - (via secure UI)

#### 4. **Categorization + Spend Analysis**

* ✅ **BERT or LLM fine-tuned on transaction types** — extract merchant, category, etc.

---

### 🔶 **Mobile App Frameworks**

* ✅ **Flutter** — cross-platform UI, native-like performance, built-in notifications for payments due, easy chart libraries.

---

### 🔶 **Visualization Dashboards**

* ✅ **Chart libraries**:

  * **Flutter**: fl\_chart, syncfusion\_flutter\_charts

* ✅ **Insight Engine**:

  * Auto-generate visual summaries of spend by:

    * Category
    * Month/Week
    * Anomalies
    * Rewards earned

---

### 🔶 Privacy & Local-first Principles

* Store all user data **locally** unless user opts in
* Use **on-device inference** with small LLMs or quantized models (e.g., TinyBERT, DistilBERT)
* Encrypt storage (e.g., SQLCipher, Android Keystore)

---

### ✅ Summary of Recommended Stack

| Part               | Tools                                              |
| ------------------ | -------------------------------------------------- |
| **SMS Parsing**    | spaCy / MiniLM + DistilBERT                        |
| **Email Parsing**  | Gmail API + PyMuPDF + BERT + Scikit-learn          |
| **PDF Unlocking**  | PikePDF + password heuristics                      |
| **Categorization** | TinyBERT                                           |
| **Mobile App**     | Flutter                                            |
| **Dashboards**     | fl\_chart / Victory Charts                         |
| **Privacy**        | Local TFLite models + Encrypted local DB           |

---

### 🔶 Workflow Chart

![WorkFlow chart](https://ibb.co/3YGKKn4p)