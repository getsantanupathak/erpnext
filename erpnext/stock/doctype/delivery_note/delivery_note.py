# ERPNext - web based ERP (http://erpnext.com)
# Copyright (C) 2012 Web Notes Technologies Pvt Ltd
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Please edit this list and import only required elements
import webnotes

from webnotes.utils import add_days, add_months, add_years, cint, cstr, date_diff, default_fields, flt, fmt_money, formatdate, generate_hash, getTraceback, get_defaults, get_first_day, get_last_day, getdate, has_common, month_name, now, nowdate, replace_newlines, sendmail, set_default, str_esc_quote, user_format, validate_email_add
from webnotes.model import db_exists
from webnotes.model.doc import Document, addchild, getchildren, make_autoname
from webnotes.model.doclist import getlist, copy_doclist
from webnotes.model.code import get_obj, get_server_obj, run_server_obj, updatedb, check_syntax
from webnotes import session, form, is_testing, msgprint, errprint

set = webnotes.conn.set
sql = webnotes.conn.sql
get_value = webnotes.conn.get_value
in_transaction = webnotes.conn.in_transaction
convert_to_lists = webnotes.conn.convert_to_lists

# -----------------------------------------------------------------------------------------

from utilities.transaction_base import TransactionBase

class DocType(TransactionBase):
	def __init__(self, doc, doclist=[]):
		self.doc = doc
		self.doclist = doclist
		self.tname = 'Delivery Note Item'
		self.fname = 'delivery_note_details'


	def autoname(self):
		self.doc.name = make_autoname(self.doc.naming_series+'.#####')


	def validate_fiscal_year(self):
		get_obj('Sales Common').validate_fiscal_year(self.doc.fiscal_year,self.doc.posting_date,'Posting Date')


	def get_contact_details(self):
		return get_obj('Sales Common').get_contact_details(self,0)


	def get_comm_rate(self, sales_partner):
		"""Get Commission rate of Sales Partner"""
		return get_obj('Sales Common').get_comm_rate(sales_partner, self)


	def pull_sales_order_details(self):
		self.validate_prev_docname()
		self.doclist = self.doc.clear_table(self.doclist,'other_charges')

		if self.doc.sales_order_no:
			get_obj('DocType Mapper', 'Sales Order-Delivery Note').dt_map('Sales Order', 'Delivery Note', self.doc.sales_order_no, self.doc, self.doclist, "[['Sales Order', 'Delivery Note'],['Sales Order Item', 'Delivery Note Item'],['Sales Taxes and Charges','Sales Taxes and Charges'],['Sales Team','Sales Team']]")
		else:
			msgprint("Please select Sales Order No. whose details need to be pulled")

		return cstr(self.doc.sales_order_no)


	def validate_prev_docname(self):
		"""Validates that Sales Order is not pulled twice"""
		for d in getlist(self.doclist, 'delivery_note_details'):
			if self.doc.sales_order_no == d.prevdoc_docname:
				msgprint(cstr(self.doc.sales_order_no) + " sales order details have already been pulled. ")
				raise Exception, "Validation Error. "


	def set_actual_qty(self):
		for d in getlist(self.doclist, 'delivery_note_details'):
			if d.item_code and d.warehouse:
				actual_qty = sql("select actual_qty from `tabBin` where item_code = '%s' and warehouse = '%s'" % (d.item_code, d.warehouse))
				d.actual_qty = actual_qty and flt(actual_qty[0][0]) or 0


	def get_tc_details(self):
		return get_obj('Sales Common').get_tc_details(self)


	def pull_project_customer(self):
		res = sql("select customer from `tabProject` where name = '%s'"%self.doc.project_name)
		if res:
			get_obj('DocType Mapper', 'Project-Delivery Note').dt_map('Project', 'Delivery Note', self.doc.project_name, self.doc, self.doclist, "[['Project', 'Delivery Note']]")


	def get_item_details(self, args=None):
		import json
		args = args and json.loads(args) or {}
		if args.get('item_code'):
			return get_obj('Sales Common').get_item_details(args, self)
		else:
			obj = get_obj('Sales Common')
			for doc in self.doclist:
				if doc.fields.get('item_code'):
					arg = {'item_code':doc.fields.get('item_code'), 'income_account':doc.fields.get('income_account'), 
						'cost_center': doc.fields.get('cost_center'), 'warehouse': doc.fields.get('warehouse')};
					ret = obj.get_item_defaults(arg)
					for r in ret:
						if not doc.fields.get(r):
							doc.fields[r] = ret[r]					

	def get_barcode_details(self, barcode):
		return get_obj('Sales Common').get_barcode_details(barcode)


	def get_adj_percent(self, arg=''):
		"""Re-calculates Basic Rate & amount based on Price List Selected"""
		get_obj('Sales Common').get_adj_percent(self)


	def get_actual_qty(self,args):
		"""Get Actual Qty of item in warehouse selected"""
		return get_obj('Sales Common').get_available_qty(eval(args))


	def get_rate(self,arg):
		return get_obj('Sales Common').get_rate(arg)


	def load_default_taxes(self):
		self.doclist = get_obj('Sales Common').load_default_taxes(self)


	def get_other_charges(self):
		"""Pull details from Sales Taxes and Charges Master"""
		self.doclist = get_obj('Sales Common').get_other_charges(self)


	def so_required(self):
		"""check in manage account if sales order required or not"""
		res = sql("select value from `tabSingles` where doctype = 'Global Defaults' and field = 'so_required'")
		if res and res[0][0] == 'Yes':
			 for d in getlist(self.doclist,'delivery_note_details'):
				 if not d.prevdoc_docname:
					 msgprint("Sales Order No. required against item %s"%d.item_code)
					 raise Exception


	def validate(self):
		self.so_required()
		self.validate_fiscal_year()
		self.validate_proj_cust()
		sales_com_obj = get_obj(dt = 'Sales Common')
		sales_com_obj.check_stop_sales_order(self)
		sales_com_obj.check_active_sales_items(self)
		sales_com_obj.get_prevdoc_date(self)
		self.validate_mandatory()
		self.validate_reference_value()
		self.validate_for_items()
		sales_com_obj.validate_max_discount(self, 'delivery_note_details')						 #verify whether rate is not greater than max discount
		sales_com_obj.get_allocated_sum(self)	# this is to verify that the allocated % of sales persons is 100%
		sales_com_obj.check_conversion_rate(self)
		
		# Get total in Words
		dcc = TransactionBase().get_company_currency(self.doc.company)
		self.doc.in_words = sales_com_obj.get_total_in_words(dcc, self.doc.rounded_total)
		self.doc.in_words_export = sales_com_obj.get_total_in_words(self.doc.currency, self.doc.rounded_total_export)

		# Set actual qty for each item in selected warehouse
		self.update_current_stock()

		self.doc.status = 'Draft'
		if not self.doc.billing_status: self.doc.billing_status = 'Not Billed'
		if not self.doc.installation_status: self.doc.installation_status = 'Not Installed'


	def validate_mandatory(self):
		if self.doc.amended_from and not self.doc.amendment_date:
			msgprint("Please Enter Amendment Date")
			raise Exception, "Validation Error. "


	def validate_proj_cust(self):
		"""check for does customer belong to same project as entered.."""
		if self.doc.project_name and self.doc.customer:
			res = sql("select name from `tabProject` where name = '%s' and (customer = '%s' or ifnull(customer,'')='')"%(self.doc.project_name, self.doc.customer))
			if not res:
				msgprint("Customer - %s does not belong to project - %s. \n\nIf you want to use project for multiple customers then please make customer details blank in project - %s."%(self.doc.customer,self.doc.project_name,self.doc.project_name))
				raise Exception


	def validate_reference_value(self):
		"""Validate values with reference document with previous document"""
		get_obj('DocType Mapper', 'Sales Order-Delivery Note', with_children = 1).validate_reference_value(self, self.doc.name)


	def validate_prevdoc_details(self):
		for d in getlist(self.doclist,'delivery_note_details'):
			prevdoc = d.prevdoc_doctype
			prevdoc_docname = d.prevdoc_docname

			if prevdoc_docname and prevdoc:
				# Validates Transaction Date of DN and previous doc (i.e. SO , PO, PR)
				trans_date = sql("select posting_date from `tab%s` where name = '%s'" %(prevdoc,prevdoc_docname))[0][0]
				if trans_date and getdate(self.doc.posting_date) < (trans_date):
					msgprint("Your Posting Date cannot be before "+cstr(prevdoc)+" Date.")
					raise Exception
				# Validates DN and previous doc details
				get_name = sql("select name from `tab%s` where name = '%s'" % (prevdoc, prevdoc_docname))
				name = get_name and get_name[0][0] or ''
				if name:	#check for incorrect docname
					if prevdoc == 'Sales Order':
						dt = sql("select company, docstatus, customer, currency, sales_partner from `tab%s` where name = '%s'" % (prevdoc, name))
						cust_name = dt and dt[0][2] or ''
						if cust_name != self.doc.customer:
							msgprint(cstr(prevdoc) + ": " + cstr(prevdoc_docname) + " customer :" + cstr(cust_name) + " does not match with customer : " + cstr(self.doc.customer) + " of current document.")
							raise Exception, "Validation Error. "
						sal_partner = dt and dt[0][4] or ''
						if sal_partner != self.doc.sales_partner:
							msgprint(cstr(prevdoc) + ": " + cstr(prevdoc_docname) + " sales partner name :" + cstr(sal_partner) + " does not match with sales partner name : " + cstr(self.doc.sales_partner_name) + " of current document.")
							raise Exception, "Validation Error. "
					else:
						dt = sql("select company, docstatus, supplier, currency from `tab%s` where name = '%s'" % (prevdoc, name))
						supp_name = dt and dt[0][2] or ''
						company_name = dt and dt[0][0] or ''
						docstatus = dt and dt[0][1] or 0
						currency = dt and dt[0][3] or ''
						if (currency != self.doc.currency):
							msgprint(cstr(prevdoc) + ": " + cstr(prevdoc_docname) + " currency : "+ cstr(currency) + "does not match with Currency: " + cstr(self.doc.currency) + "of current document")
							raise Exception, "Validation Error."
						if (company_name != self.doc.company):
							msgprint(cstr(prevdoc) + ": " + cstr(prevdoc_docname) + " does not belong to the Company: " + cstr(self.doc.company_name))
							raise Exception, "Validation Error."
						if (docstatus != 1):
							msgprint(cstr(prevdoc) + ": " + cstr(prevdoc_docname) + " is not Submitted Document.")
							raise Exception, "Validation Error."
				else:
					msgprint(cstr(prevdoc) + ": " + cstr(prevdoc_docname) + " is not a valid " + cstr(prevdoc))
					raise Exception, "Validation Error."


	def validate_for_items(self):
		check_list, chk_dupl_itm = [], []
		for d in getlist(self.doclist,'delivery_note_details'):
			ch = sql("select is_stock_item from `tabItem` where name = '%s'"%d.item_code)
			if d.prevdoc_doctype and d.prevdoc_detail_docname and ch and ch[0][0]=='Yes':
				self.validate_items_with_prevdoc(d)

			# validates whether item is not entered twice
			e = [d.item_code, d.description, d.warehouse, d.prevdoc_docname or '', d.batch_no or '']
			f = [d.item_code, d.description, d.prevdoc_docname or '']

			if ch and ch[0][0] == 'Yes':
				if e in check_list:
					msgprint("Please check whether item %s has been entered twice wrongly." % d.item_code)
				else:
					check_list.append(e)
			elif ch and ch[0][0] == 'No':
				if f in chk_dupl_itm:
					msgprint("Please check whether item %s has been entered twice wrongly." % d.item_code)
				else:
					chk_dupl_itm.append(f)


	def validate_items_with_prevdoc(self, d):
		"""check if same item, warehouse present in prevdoc"""
		prev_item_dt = (d.prevdoc_doctype == 'Sales Order') and 'Sales Order Item' or 'Purchase Receipt Item'
		data = sql("select item_code from `tab%s` where parent = '%s' and name = '%s'"\
		 	% (prev_item_dt, d.prevdoc_docname, d.prevdoc_detail_docname))
		if not data or data[0][0] != d.item_code:
			msgprint("Item: %s is not matching with Sales Order: %s. Sales Order might be modified after \
				fetching data from it. Please delete items and fetch again." \
				% (d.item_code, d.prevdoc_docname), raise_exception=1)


	def update_current_stock(self):
		for d in getlist(self.doclist, 'delivery_note_details'):
			bin = sql("select actual_qty from `tabBin` where item_code = %s and warehouse = %s", (d.item_code, d.warehouse), as_dict = 1)
			d.actual_qty = bin and flt(bin[0]['actual_qty']) or 0

		for d in getlist(self.doclist, 'packing_details'):
			bin = sql("select actual_qty, projected_qty from `tabBin` where item_code =	%s and warehouse = %s", (d.item_code, d.warehouse), as_dict = 1)
			d.actual_qty = bin and flt(bin[0]['actual_qty']) or 0
			d.projected_qty = bin and flt(bin[0]['projected_qty']) or 0


	def on_submit(self):
		self.validate_packed_qty()
		set(self.doc, 'message', 'Items against your Order #%s have been delivered. Delivery #%s: ' % (self.doc.po_no, self.doc.name))
		# Check for Approving Authority
		get_obj('Authorization Control').validate_approving_authority(self.doc.doctype, self.doc.company, self.doc.grand_total, self)
		sl_obj = get_obj("Stock Ledger")
		sl_obj.validate_serial_no(self, 'packing_details')
		sl_obj.validate_serial_no_warehouse(self, 'packing_details')
		sl_obj.update_serial_record(self, 'packing_details', is_submit = 1, is_incoming = 0)
		get_obj("Sales Common").update_prevdoc_detail(1,self)
		self.update_stock_ledger(update_stock = 1)

		self.credit_limit()

		# set DN status
		set(self.doc, 'status', 'Submitted')


	def validate_packed_qty(self):
		"""
			Validate that if packed qty exists, it should be equal to qty
		"""
		if not any([flt(d.fields.get('packed_qty')) for d in self.doclist if
				d.doctype=='Delivery Note Item']):
			return
		packing_error_list = []
		for d in self.doclist:
			if d.doctype != 'Delivery Note Item': continue
			if flt(d.fields.get('qty')) != flt(d.fields.get('packed_qty')):
				packing_error_list.append([
					d.fields.get('item_code', ''),
					d.fields.get('qty', 0),
					d.fields.get('packed_qty', 0)
				])
		if packing_error_list:
			from webnotes.utils import cstr
			err_msg = "\n".join([("Item: " + d[0] + ", Qty: " + cstr(d[1]) \
				+ ", Packed: " + cstr(d[2])) for d in packing_error_list])
			webnotes.msgprint("Packing Error:\n" + err_msg, raise_exception=1)


	def on_cancel(self):
		sales_com_obj = get_obj(dt = 'Sales Common')
		sales_com_obj.check_stop_sales_order(self)
		self.check_next_docstatus()
		get_obj('Stock Ledger').update_serial_record(self, 'packing_details', is_submit = 0, is_incoming = 0)
		sales_com_obj.update_prevdoc_detail(0,self)
		self.update_stock_ledger(update_stock = -1)
		# :::::: set DN status :::::::
		set(self.doc, 'status', 'Cancelled')
		self.cancel_packing_slips()


	def check_next_docstatus(self):
		submit_rv = sql("select t1.name from `tabSales Invoice` t1,`tabSales Invoice Item` t2 where t1.name = t2.parent and t2.delivery_note = '%s' and t1.docstatus = 1" % (self.doc.name))
		if submit_rv:
			msgprint("Sales Invoice : " + cstr(submit_rv[0][0]) + " has already been submitted !")
			raise Exception , "Validation Error."

		submit_in = sql("select t1.name from `tabInstallation Note` t1, `tabInstallation Note Item` t2 where t1.name = t2.parent and t2.prevdoc_docname = '%s' and t1.docstatus = 1" % (self.doc.name))
		if submit_in:
			msgprint("Installation Note : "+cstr(submit_in[0][0]) +" has already been submitted !")
			raise Exception , "Validation Error."


	def cancel_packing_slips(self):
		"""
			Cancel submitted packing slips related to this delivery note
		"""
		res = webnotes.conn.sql("""\
			SELECT name, count(*) FROM `tabPacking Slip`
			WHERE delivery_note = %s AND docstatus = 1
			""", self.doc.name)

		if res and res[0][1]>0:
			from webnotes.model.doclist import DocList
			for r in res:
				ps = DocList(dt='Packing Slip', dn=r[0])
				ps.cancel()
			webnotes.msgprint("%s Packing Slip(s) Cancelled" % res[0][1])


	def update_stock_ledger(self, update_stock, is_stopped = 0):
		self.values = []
		for d in self.get_item_list(is_stopped):
			stock_item = sql("SELECT is_stock_item, is_sample_item FROM tabItem where name = '%s'"%(d['item_code']), as_dict = 1) # stock ledger will be updated only if it is a stock item
			if stock_item[0]['is_stock_item'] == "Yes":
				if not d['warehouse']:
					msgprint("Message: Please enter Warehouse for item %s as it is stock item."% d['item_code'])
					raise Exception
				if d['reserved_qty'] < 0 :
					# Reduce reserved qty from reserved warehouse mentioned in so
					bin = get_obj('Warehouse', d['reserved_warehouse']).update_bin(0, flt(update_stock) * flt(d['reserved_qty']), \
						0, 0, 0, d['item_code'], self.doc.transaction_date,doc_type=self.doc.doctype, \
						doc_name=self.doc.name, is_amended = (self.doc.amended_from and 'Yes' or 'No'))
						
				# Reduce actual qty from warehouse
				self.make_sl_entry(d, d['warehouse'], - flt(d['qty']) , 0, update_stock)
		get_obj('Stock Ledger', 'Stock Ledger').update_stock(self.values)


	def get_item_list(self, is_stopped):
	 return get_obj('Sales Common').get_item_list(self, is_stopped)


	def make_sl_entry(self, d, wh, qty, in_value, update_stock):
		self.values.append({
			'item_code'					: d['item_code'],
			'warehouse'					: wh,
			'transaction_date'			: getdate(self.doc.modified).strftime('%Y-%m-%d'),
			'posting_date'				: self.doc.posting_date,
			'posting_time'				: self.doc.posting_time,
			'voucher_type'				: 'Delivery Note',
			'voucher_no'				: self.doc.name,
			'voucher_detail_no'	 		: d['name'],
			'actual_qty'				: qty,
			'stock_uom'					: d['uom'],
			'incoming_rate'			 	: in_value,
			'company'					: self.doc.company,
			'fiscal_year'				: self.doc.fiscal_year,
			'is_cancelled'				: (update_stock==1) and 'No' or 'Yes',
			'batch_no'					: d['batch_no'],
			'serial_no'					: d['serial_no']
		})


	def send_sms(self):
		if not self.doc.customer_mobile_no:
			msgprint("Please enter customer mobile no")
		elif not self.doc.message:
			msgprint("Please enter the message you want to send")
		else:
			msgprint(get_obj("SMS Control", "SMS Control").send_sms([self.doc.customer_mobile_no,], self.doc.message))


	def credit_limit(self):
		"""check credit limit of items in DN Detail which are not fetched from sales order"""
		amount, total = 0, 0
		for d in getlist(self.doclist, 'delivery_note_details'):
			if not d.prevdoc_docname:
				amount += d.amount
		if amount != 0:
			total = (amount/self.doc.net_total)*self.doc.grand_total
			get_obj('Sales Common').check_credit(self, total)


	def on_update(self):
		get_obj('Sales Common').make_packing_list(self,'delivery_note_details')
		self.set_actual_qty()
		get_obj('Stock Ledger').scrub_serial_nos(self)


