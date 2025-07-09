from pdf_unlocker import PDFUnlocker
import json

# Initialize
unlocker = PDFUnlocker()
privacy_info = unlocker.extract_extra_info_candidates()
emails = unlocker.load_privacy_data()

total = 0
unlocked = 0

for email in emails:
    msg_id = email.get('msg_id')
    hints = email.get('password_hints', [])
    
    # Get attached PDF paths from DB
    try:
        import sqlite3
        conn = sqlite3.connect(unlocker.db_path)
        c = conn.cursor()
        c.execute("SELECT attachments FROM emails WHERE id=?", (msg_id,))
        row = c.fetchone()
        conn.close()
        if not row or not row[0]:
            continue
        attachments = json.loads(row[0])
    except Exception as e:
        print(f"[!] Failed to get attachments for {msg_id}: {e}")
        continue

    # Generate password candidates
    candidates = unlocker.generate_password_candidates(hints, privacy_info)

    for pdf_path in attachments:
        print(f"\n📂 Trying to unlock: {pdf_path} from email ID {msg_id}")
        total += 1
        output = unlocker.unlock_and_save(pdf_path, password_list=candidates)
        if output:
            unlocked += 1

print(f"\n🔓 Unlocked {unlocked}/{total} PDFs")
