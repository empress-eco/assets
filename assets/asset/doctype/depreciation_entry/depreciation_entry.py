# Copyright (c) 2022, Ganga Manoj and contributors
# For license information, please see license.txt

import frappe
from frappe import _

from assets.controllers.base_asset import validate_serial_no

from erpnext.controllers.accounts_controller import AccountsController

class DepreciationEntry(AccountsController):
	def validate(self):
		self.validate_depreciation_amount()
		self.validate_reference_doc()
		self.validate_depr_schedule_row()
		validate_serial_no(self)
		self.validate_finance_book()

	def validate_depreciation_amount(self):
		if self.depreciation_amount <= 0:
			frappe.throw(_("Depreciation Amount must be greater than zero."), title = _("Invalid Amount"))

	def validate_reference_doc(self):
		if self.reference_doctype not in ["Asset_", "Asset Serial No", "Depreciation Schedule_"]:
			frappe.throw(_("Reference Document can only be an Asset, Asset Serial No or Depreciation Schedule."),
				title = _("Invalid Reference"))

	def validate_depr_schedule_row(self):
		if self.reference_doctype == "Depreciation Schedule_" and not self.depr_schedule_row:
			frappe.throw(_("Depreciation Schedule Row needs to be fetched."), title = _("Missing Value"))

	def validate_finance_book(self):
		is_depreciable_asset = frappe.get_value("Asset_", self.asset, "calculate_depreciation")

		if is_depreciable_asset:
			asset_or_serial_no = self.get_asset_or_serial_no()
			finance_books = self.get_finance_books_linked_with_asset(asset_or_serial_no)

			if len(finance_books) == 1:
				if not self.finance_book:
					self.finance_book = finance_books[0]
			elif len(finance_books) > 1:
				if not self.finance_book:
					frappe.throw(_("Enter Finance Book as {0} is linked with multiple Finance Books.").
						format(asset_or_serial_no), title = _("Missing Finance Book"))
			else:
				frappe.throw(_("{0} is not linked with any Finance Books").format(asset_or_serial_no),
					title = _("Invalid Asset"))

			if self.finance_book:
				if self.finance_book not in finance_books:
					finance_books = ', '.join([str(fb) for fb in finance_books])

					frappe.throw(_("{0} is not used in {1}. Please use one of the following instead: {2}").
						format(self.finance_book, asset_or_serial_no, finance_books))

	def get_asset_or_serial_no(self):
		if self.serial_no:
			return self.serial_no
		else:
			return self.asset

	def get_finance_books_linked_with_asset(self, asset_or_serial_no):
		return frappe.get_all(
			"Asset Finance Book_",
			filters = {
				"parent": asset_or_serial_no
			},
			pluck = "finance_book"
		)
