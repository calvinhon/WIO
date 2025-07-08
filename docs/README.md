# Architecture Design:

1. On-device SMS parsing (no data leaves device)

2. Server-assisted email processing (OAuth + PDF decryption)

3. Cloud functions for heavy ML tasks (categorization/OCR)


# Tool Stack:

Mobile: Flutter (cross-platform)

Backend: FastAPI (Python) + Firebase Auth

AI: spaCy (SMS), BERT (categorization), Tesseract (OCR)

Security: AES-256 encryption, OAuth scopes

![WorkFlow chart](docs/mermaid_20250708_4458eb.png)
