# Copyright (c) 2024, Mohan and contributors
# For license information, please see license.txt

import io
import frappe
from frappe.model.document import Document
from frappe.utils.file_manager import save_file
import requests
import pandas as pd
import requests
import json
import string
from datetime import datetime, timedelta


api_key="e7c2f23302aa774a29fcfad144c75a6c4274ef1e"

class RedmineTimesheet(Document):
	
# class RedmineTimesheetAPI(Document):
	def __init__(self,*args,**kwargs):
		super().__init__(*args, **kwargs)
		self.headers = headers = {"X-Redmine-API-Key": api_key,"Content-Type": "application/json"}
		self.params = None
		# self.redmine_url = "https://redmine.promantia.in/issues"
		self.limit = 100
	def fetch_and_convert_all_data_to_csv(self):
		self.offset = 0
		self.all_data = []

		while True:
			if not self.params:
				self.params = {
					"start_date": "><",
					"v[start_date][]": [self.from_date, self.to_date],
					"limit": self.limit,
					"offset": self.offset,
					"sort": "id:desc",
					"c[]": ["project", "tracker", "parent.subject", "subject", "assigned_to", "status", "estimated_hours", "start_date", "due_date", "spent_hours", "done_ratio"],
					"f[]": ["start_date"],
					"op[start_date]": "><",
					"t[]": ["estimated_hours", "spent_hours"]
				}
			else:
				self.params.update({
					"start_date": "><",
					"v[start_date][]": [self.from_date, self.to_date],
					"limit": self.limit,
					"offset": self.offset,
					"sort": "id:desc",
					"c[]": ["project", "tracker", "parent.subject", "subject", "assigned_to", "status", "estimated_hours", "start_date", "due_date", "spent_hours", "done_ratio"],
					"f[]": ["start_date"],
					"op[start_date]": "><",
					"t[]": ["estimated_hours", "spent_hours"]
				})

			response = self.make_redmine_api_request()

			if self.params and 'issues' in response.keys():
				response = response['issues']
			elif self.params and 'time_entries' in response:
				response = response['time_entries']

			self.all_data.extend(response)

			if len(response) < self.limit:
				break

			self.offset += self.limit

		# After fetching all data, convert it to CSV
		self.prepare_data(self.all_data)

		redmine_df = pd.DataFrame(self.all_data)
		redmine_df["estimated_hours"] = redmine_df["estimated_hours"].fillna(0).astype(int)

		redmine_df.drop(columns=["is_private", "closed_on", "fixed_version", "parent"], inplace=True)

		redmine_df['description'] = redmine_df['description'].replace('[^a-zA-Z0-9 ]', '', regex=True)

		csv_buffer = io.StringIO()
		redmine_df.to_csv(csv_buffer, index=False)
		self.final_csv_data = csv_buffer.getvalue()
		csv_buffer.close()



		
	def before_save(self):
		if not frappe.flags.in_import:
			self.fetch_and_convert_all_data_to_csv()
						
			save_file = self.upload_csv_to_files()
			update=self.sourcee()

	def make_redmine_api_request(self):
		#.json used to retut=rn the data in json format
		url = self.redmine_url + ".json"
		full_url = f"Request URL: {url}: {self.headers}\nParams: {self.params}"
		
		# Make the GET request with SSL certificate verification disabled
		response = requests.get(url, headers=self.headers, params=self.params, verify=False)
		
		# Check if the request was successful (status code 200)
		if response.status_code == 200:
			return response.json()
		else:
			# Print the error message if the request was not successful
			frappe.throw(f"Error: {response.status_code} - {response.text}")
			return None
		
	def prepare_data(self,time_entries_list):
		fields_to_keep = ['project', 'tracker', 'status', 'priority', 'author', 'assigned_to']	
		for idx, entry in enumerate(time_entries_list): 
			progress_percent = int((idx + 1) / len(time_entries_list) * 100)
			frappe.publish_realtime('show_progress', {'message': 'Processing data ..', 'percent': progress_percent}, user=frappe.session.user)
			entry.pop("custom_fields",None)
			if "spent_hours" not in entry.keys():
				id=entry["id"]
				url=f"https://redmine.promantia.in/issues/{id}.json"
				resp = requests.get(url, headers=self.headers, params=None, verify=False)
				final_responce=resp.json()
				entry["spent_hours"]=int(final_responce["issue"]["spent_hours"])
				for field in entry.copy():
					if field in fields_to_keep:
						if isinstance(entry[field], dict) and 'name' in entry[field]:
							entry[field] = entry[field]['name']
						elif isinstance(entry[field], int):
							pass
		


	def upload_csv_to_files(self):
		if not self.final_csv_data:
			frappe.msgprint("No CSV data to upload.")
			return
		
		file_name = f"{self.file_name}.csv"
		#check for existing file
		existing_file = frappe.get_value(
			'File',
			{
				'attached_to_doctype': 'Redmine Timesheet',
				'attached_to_name': self.name,
				'file_name': file_name
			}
		)


		if existing_file:
			existing_file_doc=frappe.get_doc("File",existing_file)
			existing_csv_data = frappe.get_file_content(existing_file_doc.file_url)

			combined_csv_data = existing_csv_data + '\n' + self.final_csv_data
			existing_file_doc.file_data = combined_csv_data
			existing_file_doc.save()
			frappe.msgprint(f"CSV file '{file_name}' updated successfully.")

		else:
			file_doc = save_file(file_name, self.final_csv_data, 'Redmine Timesheet', self.name)
			frappe.publish_realtime('hide_progress', user=frappe.session.user)

			
			frappe.get_doc({
				"doctype": "File",
				"file_url": file_doc.file_url,
				"file_name": file_name,
				"attached_to_doctype": "Redmine Timesheet",
				"attached_to_name": self.name,

			})
			
			frappe.msgprint(f"CSV file '{file_name}' uploaded successfully.")

	def sourcee (self):
		if self.docstatus != 1:
			filters = {
				'attached_to_name': self.name 
				}
			path = frappe.db.get_value("File",filters,'file_url')
			self.source = path
	
	


	@frappe.whitelist()
	def upload_to_insights(self):
		try:
			new_doc = frappe.new_doc("Insights Table Import")
			new_doc.table_label = self.table_lable
			new_doc.table_name = self.table_name
			new_doc.data_source = "File Uploads"
			new_doc.source = self.source
			
			new_doc.insert()
			new_doc.save()
			
			self.submitted_doc = frappe.get_doc("Insights Table Import", new_doc.name)
			data=self.update_child_table_types(self.submitted_doc)
			

			return {"status": "success", "message": f"New Insights Table Import created successfully with name: {new_doc.name}"}
		except frappe.exceptions.ValidationError as e:
			return {"status": "error", "message": f"Validation Error: {e}"}
		
	def update_child_table_types(self,submitted_doc):
			# Fetch the child table entries
			columns = submitted_doc.columns
			if columns is None:
				raise ValueError("child not found ")


			# Iterate through each row and update the 'Type' field based on the column name
			for column in columns:
				column_name = column.get("column")
				if column_name.lower() in ["start_date", "due_date"]:
					column.type = "Date"
				elif column_name.lower() in ["spent_hours", "estimated_hours"]:
					column.type = "Integer"
				elif column_name.lower() in ["created_on", "updated_on"]:
					column.type = "Datetime"
            
				else:
					column.type = "String" 
			submitted_doc.save()
			submitted_doc.submit()
	

	


# # @frappe.whitelist()
# # def triggering_scheduler():
# # 	main_ = RedmineTimesheetAPI()
# # 	main_.before_save()
