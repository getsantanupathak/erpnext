// ERPNext - web based ERP (http://erpnext.com)
// Copyright (C) 2012 Web Notes Technologies Pvt Ltd
// 
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
// 
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
// 
// You should have received a copy of the GNU General Public License
// along with this program.  If not, see <http://www.gnu.org/licenses/>.

report.customize_filters = function() {
  this.hide_all_filters();
  this.filter_fields_dict['Sales Order'+FILTER_SEP +'Customer'].df.filter_hide = 0;
  this.filter_fields_dict['Sales Order'+FILTER_SEP +'ID'].df.filter_hide = 0;
  this.filter_fields_dict['Sales Order'+FILTER_SEP +'Quotation No'].df.filter_hide = 0;
  this.filter_fields_dict['Sales Order'+FILTER_SEP +'Company'].df.filter_hide = 0;
  this.filter_fields_dict['Sales Order'+FILTER_SEP +'Sales Partner'].df.filter_hide = 0;
  this.filter_fields_dict['Sales Order'+FILTER_SEP +'Fiscal Year'].df.filter_hide = 0;
  this.filter_fields_dict['Sales Order'+FILTER_SEP +'From Sales Order Date'].df.filter_hide = 0;
  this.filter_fields_dict['Sales Order'+FILTER_SEP +'To Sales Order Date'].df.filter_hide = 0;
}