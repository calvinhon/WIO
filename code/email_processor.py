from gmail_client import GmailClient
import datetime
import re

def extract_password_hints(email_body):
    """
    Extract password hints or relevant tokens from the email body.
    You can extend this with more sophisticated NLP later.
    """
    hints = []
    # Regex to find password hint phrases
    hint_phrases = re.findall(
        r'(password (is|:|=|to open|for pdf|hint|your pdf password)? ?([^\s.,;]+))',
        email_body, flags=re.I)
    
    for full, _, pwd_candidate in hint_phrases:
        hints.append(pwd_candidate.strip())
    
    # Also extract date-like strings and 4-digit sequences often used as passwords
    dates = re.findall(r'\d{2}/\d{2}/\d{4}', email_body)
    hints.extend([d.replace('/', '') for d in dates])
    
    four_digits = re.findall(r'\b\d{4}\b', email_body)
    hints.extend(four_digits)
    
    return list(set(hints))


def process_credit_card_emails():
    """Main function to process credit card emails and extract password hints"""
    client = GmailClient()
    
    # Search for credit card related emails
    messages = client.search_credit_card_emails()
    
    downloaded_statements = []
    email_password_hints = {}  # Map message_id -> list of hints
    
    for msg in messages[:5]:  # Limit to first 5 for now
        msg_id = msg['id']
        message_details = client.get_message_details(msg_id)
        
        if message_details:
            headers = message_details['payload'].get('headers', [])
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
            date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown')
            
            print(f"\nProcessing email:")
            print(f"Subject: {subject}")
            print(f"From: {sender}")
            print(f"Date: {date}")
            
            # Extract the email body (you may need to implement this in GmailClient if not done)
            email_body = client.get_email_body(msg_id)
            
            # Extract password hints from the email body
            hints = extract_password_hints(email_body)
            email_password_hints[msg_id] = hints
            
            print(f"Extracted password hints: {hints}")
            
            # Download PDF attachments
            files = client.download_pdf_attachments(msg_id, message_details['payload'])
            downloaded_statements.extend(files)
    
    # Now you have:
    # - downloaded_statements: list of PDF file paths
    # - email_password_hints: dict mapping email msg_id to password hint list
    return downloaded_statements, email_password_hints


if __name__ == "__main__":
    statements, hints_map = process_credit_card_emails()
    print(f"\nTotal statements downloaded: {len(statements)}")
    for statement in statements:
        print(f"- {statement}")
    
    print("\nPassword hints extracted per email:")
    for msg_id, hints in hints_map.items():
        print(f"Email ID {msg_id}: {hints}")
