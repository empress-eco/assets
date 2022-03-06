# Copyright (c) 2021, Ganga Manoj and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.desk.form import assign_to
from frappe.model.document import Document
from frappe.utils import getdate, add_days, add_months, add_years

class AssetMaintenance_(Document):
	def validate(self):
		self.validate_tasks()

	def on_update(self):
		self.assign_tasks()
		self.sync_maintenance_tasks()

	def validate_tasks(self):
		for task in self.get("asset_maintenance_tasks"):
			self.validate_start_date(task)
			self.check_if_task_is_overdue(task)
			self.validate_assignee(task)

	def validate_start_date(self, task):
		if task.end_date and (getdate(task.start_date) >= getdate(task.end_date)):
			frappe.throw(_("Row #{0}: Start Date should be before End Date for task {1}")
				.format(task.idx, task.maintenance_task))

	def check_if_task_is_overdue(self, task):
		if getdate(task.next_due_date) < getdate():
			task.maintenance_status = "Overdue"

	def validate_assignee(self, task):
		if not task.assign_to and self.docstatus == 0:
			frappe.throw(_("Row #{0}: Please asign task {1} to a team member.")
				.format(task.idx, task.maintenance_task))

	def assign_tasks(self):
		for task in self.get("asset_maintenance_tasks"):
			self.assign_task(task)

	def assign_task(self, task):
		team_member = frappe.db.get_value("User", task.assign_to, "email")

		args = {
			"doctype" : "Asset Maintenance_",
			"assign_to" : [team_member],
			"name" : self.name,
			"description" : task.maintenance_task,
			"date" : task.next_due_date
		}

		if not self.have_todos_already_been_created(args):
			assign_to.add(args)

	def have_todos_already_been_created(self, args):
		todos = frappe.get_all(
			"ToDo",
			filters = {
				"reference_type": args["doctype"],
				"reference_name": args["name"],
				"status": "Open",
				"owner": args["assign_to"]
			}
		)

		if todos:
			return True
		else:
			return False

	def sync_maintenance_tasks(self):
		tasks_names = []
		for task in self.get("asset_maintenance_tasks"):
			tasks_names.append(task.name)
			self.update_maintenance_log(task)

		self.cancel_maintenance_logs_for_removed_tasks(tasks_names)

	def update_maintenance_log(self, task):
		asset_maintenance_log = self.get_maintenance_log(task)

		if not asset_maintenance_log:
			self.create_new_maintenance_log(task)
		else:
			maintenance_log = frappe.get_doc("Asset Maintenance Log_", asset_maintenance_log)
			maintenance_log.assign_to_name = task.assign_to_name
			maintenance_log.has_certificate = task.certificate_required
			maintenance_log.description = task.description
			maintenance_log.periodicity = str(task.periodicity)
			maintenance_log.maintenance_type = task.maintenance_type
			maintenance_log.due_date = task.next_due_date
			maintenance_log.save()

	def get_maintenance_log(self, task):
		return frappe.get_value(
			"Asset Maintenance Log_",
			{
				"asset_maintenance": self.name,
				"task": task.name,
				"maintenance_status": ("in",["Planned","Overdue"])
			}
		)

	def create_new_maintenance_log(self, task):
		asset_maintenance_log = frappe.get_doc({
			"doctype": "Asset Maintenance Log_",
			"asset_maintenance": self.name,
			"asset_name": self.asset_name,
			"task": task.name,
			"has_certificate": task.certificate_required,
			"description": task.description,
			"assign_to_name": task.assign_to_name,
			"periodicity": str(task.periodicity),
			"maintenance_type": task.maintenance_type,
			"due_date": task.next_due_date
		})
		asset_maintenance_log.insert()

	def cancel_maintenance_logs_for_removed_tasks(self, tasks_names):
		asset_maintenance_logs = self.get_maintenance_logs_for_removed_tasks(tasks_names)

		if asset_maintenance_logs:
			for asset_maintenance_log in asset_maintenance_logs:
				frappe.db.set_value("Asset Maintenance Log_", asset_maintenance_log.name, "maintenance_status", "Cancelled")

	def get_maintenance_logs_for_removed_tasks(self, tasks_names):
		return frappe.get_all(
			"Asset Maintenance Log_",
			fields = ["name"],
			filters = {
				"asset_maintenance": self.name,
				"task": ("not in", tasks_names)
			}
		)

@frappe.whitelist()
def calculate_next_due_date(periodicity, start_date = None, end_date = None, last_completion_date = None, next_due_date = None):
	start_date = get_start_date(start_date, last_completion_date)

	if periodicity == "Daily":
		next_due_date = add_days(start_date, 1)
	elif periodicity == "Weekly":
		next_due_date = add_days(start_date, 7)
	elif periodicity == "Monthly":
		next_due_date = add_months(start_date, 1)
	elif periodicity == "Yearly":
		next_due_date = add_years(start_date, 1)
	elif periodicity == "2 Yearly":
		next_due_date = add_years(start_date, 2)
	elif periodicity == "Quarterly":
		next_due_date = add_months(start_date, 3)

	if end_date and ((start_date and start_date >= end_date) or (last_completion_date and last_completion_date >= end_date) or next_due_date):
		next_due_date = ""

	return next_due_date

def get_start_date(start_date, last_completion_date):
	if not start_date and not last_completion_date:
		return frappe.utils.now()
	elif last_completion_date and ((start_date and last_completion_date > start_date) or not start_date):
		return last_completion_date

	return start_date

@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_team_members(doctype, txt, searchfield, start, page_len, filters):
	return frappe.db.get_values(
		"Maintenance Team Member_", {
			"parent": filters.get("maintenance_team")
		},
		"team_member"
	)
