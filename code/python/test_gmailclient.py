from gmail_client import GmailClient

# Instantiate the Gmail client
client = GmailClient()

# Search for credit card-related emails
emails = client.search_credit_card_emails()

# Show first email and download attachments
if emails:
    first_email_id = emails[0]['id']
    print(f"Email ID: {first_email_id}")
    
    # Download PDF attachments
    client.download_pdf_attachments(first_email_id)
else:
    print("No matching emails found.")
