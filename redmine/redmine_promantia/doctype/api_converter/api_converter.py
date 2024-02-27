# Copyright (c) 2024, Mohan and contributors
# For license information, please see license.txt

from io import StringIO
import requests
import frappe
import json
import csv
import pandas as pd
from frappe.utils.file_manager import save_file
from frappe.model.document import Document

class Apiconverter(Document):
	def before_save(self):
		key = self.api_key
		response = requests.get(key)

		if response.status_code == 200:
			try:
				data = json.loads(response.text)

				# Convert JSON data to pandas DataFrame
				if isinstance(data, list):
					df = pd.DataFrame(data)
				else:
					df = pd.DataFrame([data])

				# Create an in-memory file-like object
				csv_file_buffer = StringIO()

				# Write DataFrame to CSV buffer
				df.to_csv(csv_file_buffer, index=False)

				csv_contents = csv_file_buffer.getvalue()

				# Save CSV file
				file_name = f"{self.file_name}.csv"
				folder = 'Home'
				file_path = save_file(file_name, csv_contents, 'Api converter', self.name, folder=folder)

			except json.JSONDecodeError as e:
				frappe.throw(f"Error decoding JSON: {e}")
		else:
			frappe.throw(f"Error in getting API data. Status code: {response.status_code}")

	def on_update(self):
			if self.docstatus != 1:
				filters = {
					'attached_to_name': self.name 
					}
					
				path = frappe.db.get_value("File",filters,'file_url')
				self.file_path = path
			
	# def on_submit(self):
	# 	file_path = self.file_path
	# 	self.create_new_document(file_path)




	# def create_new_document(self, file_path):
	# 		try:
	# 			new_doc = frappe.new_doc("Insights Table Import")
	# 			new_doc.table_label = self.table_lable
	# 			new_doc.table_name = self.table_name
	# 			new_doc.data_source = "File Uploads"
	# 			new_doc.source = file_path
	# 			new_doc.insert()
	# 			new_doc.submit()
	# 			frappe.msgprint(f"New Insights Table Import created successfully with name: {new_doc.name}")
	# 			return new_doc
	# 		except frappe.exceptions.ValidationError as e:
	# 			frappe.msgprint(f"Validation Error: {e}")
	# 		except Exception as e:
	# 			frappe.msgprint(f"Error creating Insights Table Import: {e}")
