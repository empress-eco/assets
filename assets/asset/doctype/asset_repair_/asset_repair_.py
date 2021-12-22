# Copyright (c) 2021, Ganga Manoj and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt
from frappe.model.document import Document

from assets.asset.doctype.asset_.asset_ import set_status

class AssetRepair_(Document):
	def validate(self):
		self.get_asset_doc()
		self.validate_asset()
		self.update_status()

		if self.get('stock_consumption'):
			self.set_total_value()

		self.calculate_total_repair_cost()

	def before_submit(self):
		self.check_repair_status()

		if self.get('stock_consumption') or self.get('capitalize_repair_cost'):
			self.increase_asset_value()
		if self.get('stock_consumption'):
			self.decrease_stock_quantity()

	def get_asset_doc(self):
		if self.get('serial_no'):
			self.asset_doc = frappe.get_doc('Asset Serial No', self.serial_no)
		else:
			self.asset_doc = frappe.get_doc('Asset_', self.asset)

	def validate_asset(self):
		if self.asset_doc.doctype == 'Asset_':
			if self.asset_doc.is_serialized_asset:
				frappe.throw(_("Please enter Serial No as {0} is a Serialized Asset")
					.format(frappe.bold(self.asset)), title=_("Missing Serial No"))

	def update_status(self):
		if self.repair_status == 'Pending':
			frappe.db.set_value(self.asset_doc.doctype, self.asset_doc.name, 'status', 'Out of Order')
		else:
			set_status(self.asset_doc)

	def set_total_value(self):
		for item in self.get('items'):
			item.amount = flt(item.rate) * flt(item.qty)

	def calculate_total_repair_cost(self):
		self.total_repair_cost = flt(self.repair_cost)

		total_value_of_stock_consumed = self.get_total_value_of_stock_consumed()
		self.total_repair_cost += total_value_of_stock_consumed

	def get_total_value_of_stock_consumed(self):
		total_value_of_stock_consumed = 0
		if self.get('stock_consumption'):
			for item in self.get('items'):
				total_value_of_stock_consumed += item.amount

		return total_value_of_stock_consumed

	def check_repair_status(self):
		if self.repair_status == "Pending":
			frappe.throw(_("Please update Repair Status."))

	def increase_asset_value(self):
		total_value_of_stock_consumed = self.get_total_value_of_stock_consumed()

		if self.asset_doc.calculate_depreciation:
			for row in self.asset_doc.finance_books:
				row.value_after_depreciation += total_value_of_stock_consumed

				if self.capitalize_repair_cost:
					row.value_after_depreciation += self.repair_cost

	def decrease_stock_quantity(self):
		stock_entry = frappe.get_doc({
			"doctype": "Stock Entry",
			"stock_entry_type": "Material Issue",
			"company": self.company
		})

		for item in self.get('items'):
			stock_entry.append('items', {
				"s_warehouse": self.warehouse,
				"item_code": item.item_code,
				"qty": item.qty,
				"basic_rate": item.rate,
				"serial_no": item.serial_no
			})

		stock_entry.insert()
		stock_entry.submit()

		self.db_set('stock_entry', stock_entry.name)