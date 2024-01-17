# Copyright (c) 2024, Mohan and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import requests
import pandas as pd
import requests

api_key="e7c2f23302aa774a29fcfad144c75a6c4274ef1e"

class RedmineTimesheet(Document):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.headers = headers = {"X-Redmine-API-Key": api_key,"Content-Type": "application/json"}
		self.params = None
		self.limit = 150
	def before_save(self):
		if not self.params:
			self.params={"from": self.from_date,"to": self.to_date,"limit": self.limit}
		responce = self.make_redmine_api_request()
		if  self.params and 'issues' in responce.keys(): 
			responce = responce['issues']
		elif self.params and 'time_entries' in responce:
			responce = responce['time_entries']

		redmine_df=pd.DataFrame(responce)
		self.prepare_date(responce)
		redmine_df["estimated_hours"]=redmine_df["estimated_hours"].fillna(0)

		redmine_df.drop(columns=["is_private","closed_on","fixed_version","parent"],inplace=True)

		redmine_df['description'] = redmine_df['description'].replace('[^a-zA-Z0-9 ]', '', regex=True)

		final_csv=redmine_df.to_csv("Test.csv",index=False)

		print(final_csv)



	def make_redmine_api_request(self):
		#.json used to retut=rn the data in json format
		url = self.redmine_url + ".json"
		
		# Make the GET request with SSL certificate verification disabled
		response = requests.get(url, headers=self.headers, params=self.params, verify=False)
		
		# Check if the request was successful (status code 200)
		if response.status_code == 200:
			return response.json()
		else:
			# Print the error message if the request was not successful
			frappe.throw(f"Error: {response.status_code} - {response.text}")
			return None
		
	def prepare_date(self,time_entries_list):
		fields_to_keep = ['project', 'tracker', 'status', 'priority', 'author', 'assigned_to']

		# Update each dictionary to only contain 'name' values for specified fields
		for entry in time_entries_list:
			entry.pop("custom_fields",None)
			if "spent_hours" not in entry.keys():
				id=entry["id"]
				url=f"https://redmine.promantia.in/issues/{id}.json"
				resp = requests.get(url, headers=self.headers, params=None, verify=False)
				final_responce=resp.json()
				entry["spent_hours"]=final_responce["issue"]["spent_hours"]
			for field in entry.copy():
				if field in fields_to_keep and 'name' in entry[field]:
					entry[field] = entry[field]['name']

