import pikepdf
import re
import itertools
import sqlite3
from datetime import datetime, timedelta

class PDFUnlocker:
	def __init__(self, db_path='email_data.db'):
		self.db_path = db_path
		self.common_patterns = [
			# Date patterns
			lambda: datetime.now().strftime("%d%m%Y"),
			lambda: datetime.now().strftime("%d%m%y"),
			lambda: datetime.now().strftime("%Y%m%d"),
			lambda: (datetime.now() - timedelta(days=30)).strftime("%d%m%Y"),
			
			# Common passwords
			"password", "123456", "admin", "user",
			"creditcard", "statement", "default"
		]

	def load_privacy_data(self):
		"""
		Load privacy-related data from the email database
		Returns a list of dicts, each representing one email's hints and info
		Expected columns in DB: password_hints, sender, subject, etc.
		"""
		conn = sqlite3.connect(self.db_path)
		c = conn.cursor()
		c.execute("SELECT id, password_hints, subject, sender FROM emails")
		rows = c.fetchall()
		conn.close()

		data = []
		for row in rows:
			msg_id, hints_json, subject, sender = row
			hints = []
			if hints_json:
				import json
				try:
					hints = json.loads(hints_json)
				except Exception:
					hints = []
			data.append({
				"msg_id": msg_id,
				"password_hints": hints,
				"subject": subject,
				"sender": sender
			})
		return data

	def extract_extra_info_candidates(self):
		"""
		Stub function: Replace with real extraction from user data or DB.
		For example:
		- date of birth formats
		- user full name variations (e.g. firstname, lastname, initials)
		- mobile phone number parts
		- last 4 digits of card or account number
		Returns a list of strings representing privacy info to try
		"""
		# Example static values, replace or load dynamically
		dob_formats = ["01011990", "010190", "19900101"]  # ddmmyyyy, ddmmyy, yyyymmdd
		names = ["hoach", "hoachtran", "tran"]  # e.g. lowercase, no spaces
		mobile_parts = ["1234", "5678"]  # last 4 digits of mobile
		last4_card = ["9876"]

		# Combine all as candidate strings
		candidates = dob_formats + names + mobile_parts + last4_card
		return candidates

	def generate_password_candidates(self, hints, privacy_info):
		"""
		Generate password guesses from hints + privacy info + common patterns
		Combine hints and privacy_info with common patterns as single or concat combos
		"""
		candidates = set()

		# Add all common patterns (evaluated)
		for pattern in self.common_patterns:
			if callable(pattern):
				candidates.add(pattern())
			else:
				candidates.add(pattern)

		# Add all hints and privacy info
		for x in hints + privacy_info:
			candidates.add(str(x))

		# Generate simple concatenations of hint + privacy_info (e.g. hint + dob)
		for hint, priv in itertools.product(hints, privacy_info):
			combined = f"{hint}{priv}"
			candidates.add(combined)
			candidates.add(f"{priv}{hint}")

		return list(candidates)

	def try_unlock_pdf(self, pdf_path, password_list=None):
		"""Try to unlock PDF with various passwords"""
		if password_list is None:
			password_list = []

		# Try without password first
		try:
			pdf = pikepdf.open(pdf_path)
			print(f"✅ PDF is not password protected: {pdf_path}")
			return pdf, None
		except pikepdf._qpdf.PasswordError:
			pass

		for password in password_list:
			try:
				pdf = pikepdf.open(pdf_path, password=str(password))
				print(f"✅ PDF unlocked with password: {password}")
				return pdf, password
			except pikepdf._qpdf.PasswordError:
				continue
		
		print(f"❌ Could not unlock PDF: {pdf_path}")
		return None, None
	
	def unlock_and_save(self, pdf_path, password_list=None, output_path=None):
		"""Unlock PDF and save unlocked version"""
		pdf, password = self.try_unlock_pdf(pdf_path, password_list)
		if not pdf:
			print("❌ Failed to unlock.")
			return None

		if output_path is None:
			output_path = pdf_path.replace('.pdf', '_unlocked.pdf')

		pdf.save(output_path)
		pdf.close()
		print(f"📄 Saved unlocked file to {output_path}")
		return output_path


	def unlock_pdfs_from_db(self, download_dir='downloads'):
		"""
		Attempt to unlock all PDFs stored in DB metadata with associated hints and privacy info.
		"""
		privacy_info = self.extract_extra_info_candidates()
		data = self.load_privacy_data()

		for email in data:
			hints = email.get('password_hints', [])
			msg_id = email.get('msg_id')
			# Fetch attachments from DB
			# Assuming attachments stored as JSON list of filepaths
			attachments = []
			try:
				conn = sqlite3.connect(self.db_path)
				c = conn.cursor()
				c.execute("SELECT attachments FROM emails WHERE id=?", (msg_id,))
				row = c.fetchone()
				conn.close()
				if row and row[0]:
					attachments = json.loads(row[0])
			except Exception as e:
				print(f"Failed to get attachments for {msg_id}: {e}")

			if not attachments:
				print(f"No attachments found for email {msg_id}")
				continue

			# Generate candidate passwords
			candidates = self.generate_password_candidates(hints, privacy_info)

			for pdf_path in attachments:
				print(f"\nTrying to unlock PDF: {pdf_path} for email {msg_id}")
				pdf, password = self.try_unlock_pdf(pdf_path, candidates)
				if pdf:
					unlocked_path = pdf_path.replace('.pdf', '_unlocked.pdf')
					pdf.save(unlocked_path)
					pdf.close()
					print(f"📄 Unlocked PDF saved: {unlocked_path}")
				else:
					print(f"Failed to unlock PDF {pdf_path}")

if __name__ == "__main__":
	unlocker = PDFUnlocker()
	unlocker.unlock_pdfs_from_db()
