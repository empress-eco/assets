# Copyright (c) 2021, Ganga Manoj and Contributors
# See license.txt

import unittest

import frappe
from frappe.utils import getdate

from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt

class TestAsset_(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		create_company()
		create_asset_data()
		enable_cwip_accounting("Computers")
		enable_book_asset_depreciation_entry_automatically()
		# make_purchase_receipt(item_code="Macbook Pro", qty=1, rate=100000.0, location="Test Location")
		frappe.db.sql("delete from `tabTax Rule`")

	@classmethod
	def tearDownClass(cls):
		frappe.db.rollback()

	def test_asset_category_is_fetched(self):
		"""Tests if the Item's Asset Category value is assigned to the Asset, if the field is empty."""

		asset = create_asset(item_code="Macbook Pro", do_not_save=1)
		asset.asset_category = None
		asset.save()

		self.assertEqual(asset.asset_category, "Computers")

	def test_gross_purchase_amount_is_mandatory(self):
		asset = create_asset(item_code="Macbook Pro", do_not_save=1)
		asset.gross_purchase_amount = 0

		self.assertRaises(frappe.MandatoryError, asset.save)

	def test_pr_or_pi_mandatory_if_not_existing_asset(self):
		"""Tests if either PI or PR is present if CWIP is enabled and is_existing_asset=0."""

		asset = create_asset(item_code="Macbook Pro", do_not_save=1)
		asset.is_existing_asset=0

		self.assertRaises(frappe.ValidationError, asset.save)

	def test_available_for_use_date_is_after_purchase_date(self):
		asset = create_asset(item_code="Macbook Pro", calculate_depreciation=1, do_not_save=1)
		asset.is_existing_asset = 0
		asset.purchase_date = getdate("2021-10-10")
		asset.available_for_use_date = getdate("2021-10-1")

		self.assertRaises(frappe.ValidationError, asset.save)

	def test_item_exists(self):
		asset = create_asset(item_code="MacBook", do_not_save=1)

		self.assertRaises(frappe.DoesNotExistError, asset.save)

	def test_validate_item(self):
		asset = create_asset(item_code="MacBook Pro", do_not_save=1)
		item = frappe.get_doc("Item", "MacBook Pro")

		item.disabled = 1
		item.save()
		self.assertRaises(frappe.ValidationError, asset.save)
		item.disabled = 0

		item.is_fixed_asset = 0
		self.assertRaises(frappe.ValidationError, asset.save)
		item.is_fixed_asset = 1

		item.is_stock_item = 1
		self.assertRaises(frappe.ValidationError, asset.save)

def create_company():
	if not frappe.db.exists("Company", "_Test Company"):
		company = frappe.get_doc({
			"doctype": "Company",
			"company_name": "_Test Company",
			"country": "United States",
			"default_currency": "USD",
			"accumulated_depreciation_account": "_Test Accumulated Depreciations - _TC",
			"depreciation_expense_account": "_Test Depreciations - _TC",
			"disposal_account": "_Test Gain/Loss on Asset Disposal - _TC",
			"depreciation_cost_center": "_Test Cost Center - _TC",
		})
		company.insert(ignore_if_duplicate = True)
	else:
		set_depreciation_settings_in_company()

def set_depreciation_settings_in_company():
	company = frappe.get_doc("Company", "_Test Company")
	company.accumulated_depreciation_account = "_Test Accumulated Depreciations - _TC"
	company.depreciation_expense_account = "_Test Depreciations - _TC"
	company.disposal_account = "_Test Gain/Loss on Asset Disposal - _TC"
	company.depreciation_cost_center = "_Test Cost Center - _TC"
	company.save()

def create_asset_data():
	if not frappe.db.exists("Asset Category_", "Computers"):
		create_asset_category()

	if not frappe.db.exists("Item", "Macbook Pro"):
		create_fixed_asset_item()

	if not frappe.db.exists("Location_", "Test Location"):
		create_location()

	if not frappe.db.exists("Depreciation Template", "Straight Line Method Annually for 5 Years"):
		create_depreciation_template()

def create_asset_category():
	asset_category = frappe.get_doc({
		"doctype": "Asset Category_",
		"asset_category_name": "Computers",
		"enable_cwip_accounting": 1,
		"accounts": [{
			"company_name": "_Test Company",
			"fixed_asset_account": "_Test Fixed Asset - _TC",
			"accumulated_depreciation_account": "_Test Accumulated Depreciations - _TC",
			"depreciation_expense_account": "_Test Depreciations - _TC"
		}]
	})

	asset_category.insert()

def create_fixed_asset_item(item_code=None):
	naming_series = get_naming_series()

	try:
		item = frappe.get_doc({
			"doctype": "Item",
			"item_code": item_code or "Macbook Pro",
			"item_name": "Macbook Pro",
			"description": "Macbook Pro Retina Display",
			"asset_category": "Computers",
			"item_group": "All Item Groups",
			"stock_uom": "Nos",
			"is_stock_item": 0,
			"is_fixed_asset": 1,
			"auto_create_assets": 1,
			"asset_naming_series": naming_series
		})
		item.insert(ignore_if_duplicate=True)
	except frappe.DuplicateEntryError:
		pass

	return item

def get_naming_series():
	meta = frappe.get_meta("Asset_")
	naming_series = meta.get_field("naming_series").options.splitlines()[0] or "ACC-ASS-.YYYY.-"

	return naming_series

def create_location():
	frappe.get_doc({
		"doctype": "Location_",
		"location_name": "Test Location"
	}).insert()

def create_depreciation_template(**args):
	args = frappe._dict(args)

	depreciation_template = frappe.get_doc({
		"doctype": "Depreciation Template",
		"template_name": args.template_name or "Straight Line Method Annually for 5 Years",
		"depreciation_method": args.depreciation_method or "Straight Line",
		"frequency_of_depreciation": args.frequency_of_depreciation or "Yearly",
		"asset_life": args.asset_life or 5,
		"asset_life_unit": args.asset_life_unit or "Years",
		"rate_of_depreciation": args.rate_of_depreciation or "0"
	})
	depreciation_template.insert()

	return depreciation_template.name

def enable_cwip_accounting(asset_category, enable=1):
	frappe.db.set_value("Asset Category_", asset_category, "enable_cwip_accounting", enable)

def enable_book_asset_depreciation_entry_automatically():
	frappe.db.set_value("Accounts Settings", None, "book_asset_depreciation_entry_automatically", 1)

def enable_finance_books(enable=1):
	frappe.db.set_value("Accounts Settings", None, "enable_finance_books", enable)

def create_asset(**args):
	args = frappe._dict(args)

	asset = frappe.get_doc({
		"doctype": "Asset_",
		"asset_name": args.asset_name or "Macbook Pro 1",
		"asset_category": args.asset_category or "Computers",
		"item_code": args.item_code or "Macbook Pro",
		"num_of_assets": args.num_of_assets or 1,
		"is_serialized_asset": args.is_serialized_asset or 0,
		"asset_owner": args.asset_owner or "Company",
		"company": args.company or "_Test Company",
		"is_existing_asset": args.is_existing_asset or 1,
		"purchase_date": args.purchase_date or "2020-01-01",
		"gross_purchase_amount": args.gross_purchase_amount or 100000,
		"calculate_depreciation": args.calculate_depreciation or 0
	})

	if not asset.is_serialized_asset:
		asset.location = args.location or "Test Location"

		if asset.calculate_depreciation:
			asset.opening_accumulated_depreciation = args.opening_accumulated_depreciation or 0
			asset.available_for_use_date = args.available_for_use_date or "2020-06-06"
			asset.salvage_value = args.salvage_value or 0
			asset.depreciation_posting_start_date = args.depreciation_posting_start_date or "2021-06-06"

			if args.enable_finance_books:
				asset.append("finance_books", {
					"finance_book": args.finance_book,
					"depreciation_template": args.depreciation_template or "Straight Line Method Annually for 5 Years"
				})
			else:
				asset.depreciation_template = args.depreciation_template or "Straight Line Method Annually for 5 Years"

	if not args.do_not_save:
		try:
			asset.insert(ignore_if_duplicate=True)
		except frappe.DuplicateEntryError:
			pass

	if args.submit:
		asset.submit()

	return asset