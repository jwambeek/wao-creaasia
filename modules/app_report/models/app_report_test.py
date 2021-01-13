from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class SaleOrder_Data(models.Model):
    _inherit = 'sale.order'

    channel_order_number = fields.Char(string = 'Channel Order No.')

    def _prepare_invoice(self):
        """
        Prepare the dict of values to create the new invoice for a sales order. This method may be
        overridden to implement custom invoice generation (making sure to call super() to establish
        a clean extension chain).
        """
        self.ensure_one()
        company_id = self.company_id.id
        journal_id = (self.env['account.invoice'].with_context(company_id=company_id or self.env.user.company_id.id)
            .default_get(['journal_id'])['journal_id'])
        if not journal_id:
            raise UserError(_('Please define an accounting sales journal for this company.'))
        vinvoice = self.env['account.invoice'].new({'partner_id': self.partner_invoice_id.id, 'type': 'out_invoice'})
        # Get partner extra fields
        vinvoice._onchange_partner_id()
        invoice_vals = vinvoice._convert_to_write(vinvoice._cache)
        invoice_vals.update({
            'name': (self.client_order_ref or '')[:2000],
            'origin': self.name,
            'type': 'out_invoice',
            'account_id': self.partner_invoice_id.property_account_receivable_id.id,
            'partner_shipping_id': self.partner_shipping_id.id,
            'journal_id': journal_id,
            'channel_order_number':self.channel_order_number,
            'currency_id': self.pricelist_id.currency_id.id,
            'comment': self.note,
            'payment_term_id': self.payment_term_id.id,
            'fiscal_position_id': self.fiscal_position_id.id or self.partner_invoice_id.property_account_position_id.id,
            'company_id': company_id,
            'user_id': self.user_id and self.user_id.id,
            'team_id': self.team_id.id,
            'transaction_ids': [(6, 0, self.transaction_ids.ids)],
        })
        return invoice_vals

    
class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    seller_discount = fields.Float(string='Seller Discount')

    @api.multi
    def _prepare_invoice_line(self, qty):
        """
        Prepare the dict of values to create the new invoice line for a sales order line.

        :param qty: float quantity to invoice
        """
        self.ensure_one()
        res = {}
        product = self.product_id.with_context(force_company=self.company_id.id)
        account = product.property_account_income_id or product.categ_id.property_account_income_categ_id

        if not account and self.product_id:
            raise UserError(_('Please define income account for this product: "%s" (id:%d) - or for its category: "%s".') %
                (self.product_id.name, self.product_id.id, self.product_id.categ_id.name))

        fpos = self.order_id.fiscal_position_id or self.order_id.partner_id.property_account_position_id
        if fpos and account:
            account = fpos.map_account(account)

        res = {
            'name': self.name,
            'sequence': self.sequence,
            'origin': self.order_id.name,
            'account_id': account.id,
            'price_unit': self.price_unit,
            'quantity': qty,
            'discount': self.discount,
            'seller_discount': self.seller_discount,
            'uom_id': self.product_uom.id,
            'product_id': self.product_id.id or False,
            'invoice_line_tax_ids': [(6, 0, self.tax_id.ids)],
            'account_analytic_id': self.order_id.analytic_account_id.id,
            'analytic_tag_ids': [(6, 0, self.analytic_tag_ids.ids)],
            'display_type': self.display_type,
        }
        return res

# mapping invoice type to refund type
TYPE2REFUND = {
    'out_invoice': 'out_refund',        # Customer Invoice
    'in_invoice': 'in_refund',          # Vendor Bill
    'out_refund': 'out_invoice',        # Customer Credit Note
    'in_refund': 'in_invoice',          # Vendor Credit Note
}

class AccountInvoice_Data(models.Model):
    _inherit = 'account.invoice'

    channel_order_number = fields.Char(string = 'Channel Order No.',readonly=True, tracking=True)
    number = fields.Char(related='move_id.name', store=True, readonly=True, copy=False)
    test = fields.Monetary(related='move_id.line_ids.amount_residual', store=True, readonly=True, copy=False)
    origin = fields.Monetary(string='Source Document',
        help="Reference of the document that produced this invoice.",
        readonly=True, states={'draft': [('readonly', False)]})

    tax_invoice_amount = fields.Monetary(string='Tax Invoice Amount',
        help="Reference of the document that produced this invoice.",
        readonly=True, states={'draft': [('readonly', False)]})    

    @api.multi
    def action_invoice_draft(self):
        if self.filtered(lambda inv: inv.state != 'cancel'):
            raise UserError(_("Invoice must be cancelled in order to reset it to draft."))
        # go from canceled state to draft state
        self.write({'state': 'draft', 'date': False})
        # Delete former printed invoice
        try:
            report_invoice = self.env['ir.actions.report']._get_report_from_name('account.report_invoice')
        except IndexError:
            report_invoice = False
        if report_invoice and report_invoice.attachment:
            for invoice in self:
                with invoice.env.do_in_draft():
                    invoice.number,invoice.test, invoice.state = invoice.move_name, 'open'
                    attachment = self.env.ref('account.account_invoices').retrieve_attachment(invoice)
                if attachment:
                    attachment.unlink()
        return True

    @api.multi
    def name_get(self):
        TYPES = {
            'out_invoice': _('Invoice'),
            'in_invoice': _('Vendor Bill'),
            'out_refund': _('Credit Note'),
            'in_refund': _('Vendor Credit note'),
        }
        result = []
        for inv in self:
            result.append((inv.id, "%s %s" % (inv.number or TYPES[inv.type], inv.name or '')),
                          (inv.id, "%s %s" % (inv.test or TYPES[inv.type], inv.name or '')))
        return result

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        invoice_ids = []
        if name:
            invoice_ids = self._search([('number', '=', name)] + args, limit=limit, access_rights_uid=name_get_uid)
            invoice_ids = self._search([('test', '=', name)] + args, limit=limit, access_rights_uid=name_get_uid)
        if not invoice_ids:
            invoice_ids = self._search([('number', operator, name)] + args, limit=limit, access_rights_uid=name_get_uid)
            invoice_ids = self._search([('test', operator, name)] + args, limit=limit, access_rights_uid=name_get_uid)
        if not invoice_ids:
            invoice_ids = self._search([('name', operator, name)] + args, limit=limit, access_rights_uid=name_get_uid)
        return self.browse(invoice_ids).name_get()

    @api.model
    def _prepare_refund(self, invoice, date_invoice=None, date=None, description=None, journal_id=None):
        """ Prepare the dict of values to create the new credit note from the invoice.
            This method may be overridden to implement custom
            credit note generation (making sure to call super() to establish
            a clean extension chain).

            :param record invoice: invoice as credit note
            :param string date_invoice: credit note creation date from the wizard
            :param integer date: force date from the wizard
            :param string description: description of the credit note from the wizard
            :param integer journal_id: account.journal from the wizard
            :return: dict of value to create() the credit note
        """
        values = {}
        for field in self._get_refund_copy_fields():
            if invoice._fields[field].type == 'many2one':
                values[field] = invoice[field].id
            else:
                values[field] = invoice[field] or False

        values['invoice_line_ids'] = self._refund_cleanup_lines(invoice.invoice_line_ids)

        tax_lines = invoice.tax_line_ids
        taxes_to_change = {
            line.tax_id.id: line.tax_id.refund_account_id.id
            for line in tax_lines.filtered(lambda l: l.tax_id.refund_account_id != l.tax_id.account_id)
        }
        cleaned_tax_lines = self._refund_cleanup_lines(tax_lines)
        values['tax_line_ids'] = self._refund_tax_lines_account_change(cleaned_tax_lines, taxes_to_change)

        if journal_id:
            journal = self.env['account.journal'].browse(journal_id)
        elif invoice['type'] == 'in_invoice':
            journal = self.env['account.journal'].search([('type', '=', 'purchase')], limit=1)
        else:
            journal = self.env['account.journal'].search([('type', '=', 'sale')], limit=1)
        values['journal_id'] = journal.id

        values['type'] = TYPE2REFUND[invoice['type']]
        values['date_invoice'] = date_invoice or fields.Date.context_today(invoice)
        values['date_due'] = values['date_invoice']
        values['state'] = 'draft'
        values['number'] = False
        values['origin'] = invoice.number
        values['test'] = False
        values['tax_invoice_amount'] = invoice.test
        values['refund_invoice_id'] = invoice.id
        values['reference'] = False

        if values['type'] == 'in_refund':
            values['payment_term_id'] = invoice.partner_id.property_supplier_payment_term_id.id
            partner_bank_result = self._get_partner_bank_id(values['company_id'])
            if partner_bank_result:
                values['partner_bank_id'] = partner_bank_result.id
        else:
            values['payment_term_id'] = invoice.partner_id.property_payment_term_id.id

        if date:
            values['date'] = date
        if description:
            values['name'] = description
        return values


    @api.depends('invoice_line_ids.price_unit','invoice_line_ids.quantity')
    def _cal_total_amount(self):
        for order in self:
            cal_amount = 0
            for  line_items in order.invoice_line_ids:
                #line_items.amount = line_items.quantity * line_items.price_unit
                cal_amount = cal_amount + (line_items.quantity * line_items.price_unit)
            order.total_amount = cal_amount

    total_amount = fields.Float(string = 'Total', compute = '_cal_total_amount', store = True, digits=(12,4))            
                
    @api.depends('invoice_line_ids.price_unit', 'invoice_line_ids.seller_discount','invoice_line_ids.quantity')
    def _cal_total_discount(self):
        for order in self:
            cal_discount = 0
            for line_items in order.invoice_line_ids:
                cal_discount = cal_discount + (line_items.quantity * line_items.price_unit * line_items.seller_discount) / 100
            order.calculated_discount = cal_discount
        

    calculated_discount = fields.Float(string = 'Discount', compute = '_cal_total_discount', store = True, digits=(12,4))

    @api.depends('invoice_line_ids.seller_discount', 'invoice_line_ids.price_unit','invoice_line_ids.amount','invoice_line_ids.quantity')
    def _cal_total_baht_escl_vat(self):
        for orders in self:
            total_excl_vat = 0
            for line_items in orders.invoice_line_ids:
                total_excl_vat = total_excl_vat + (line_items.amount - (line_items.seller_discount * line_items.price_unit * line_items.quantity)/100)
            orders.total_baht_excl_VAT = total_excl_vat

    total_baht_excl_VAT = fields.Float(string = 'Total Baht Excl VAT', compute = '_cal_total_baht_escl_vat', store= True, digits=(12,4))

    @api.depends('invoice_line_ids.invoice_line_tax_ids','invoice_line_ids.invoice_line_tax_ids.amount','invoice_line_ids.seller_discount','invoice_line_ids.price_unit','invoice_line_ids.amount','invoice_line_ids.quantity')
    def _cal_total_baht_incl_vat(self):
        for orders in self:
            total_incl_vat = 0
            for line_items in orders.invoice_line_ids:
                if line_items.invoice_line_tax_ids == '':
                    total_incl_vat = total_incl_vat + ((line_items.amount - (line_items.seller_discount * line_items.price_unit * line_items.quantity)/100) + (0.00/100 * (line_items.amount - (line_items.seller_discount * line_items.price_unit * line_items.quantity)/100)))
                    orders.total_baht_incl_VAT = total_incl_vat
                else:
                    total_incl_vat = total_incl_vat + ((line_items.amount - (line_items.seller_discount * line_items.price_unit * line_items.quantity)/100) + (line_items.invoice_line_tax_ids.amount/100 * (line_items.amount - (line_items.seller_discount * line_items.price_unit * line_items.quantity)/100)))
                    orders.total_baht_incl_VAT = total_incl_vat



    total_baht_incl_VAT = fields.Float(string = 'Total Baht Incl VAT', compute = '_cal_total_baht_incl_vat', store = True, digits=(12,4))

    @api.depends('total_baht_excl_VAT','total_baht_incl_VAT')
    def _cal_total_vat(self):
        for orders in self:
            orders.vat = orders.total_baht_incl_VAT - orders.total_baht_excl_VAT

    vat = fields.Float(string = 'Vat', compute = '_cal_total_vat', store = True, digits=(12,4))

    # Function :- Corrected Goods/Service Amount for Credit Note Report
    @api.depends('total_amount','total_baht_excl_VAT')
    def _corrected_service_amount(self):
        for orders in self:
            orders.corrected_service_amount = orders.total_amount - orders.total_baht_excl_VAT

    corrected_service_amount = fields.Float(string = 'Corrected Service Amount', compute = '_corrected_service_amount', store = True, digits=(12,4))        

class AccountInvoice_Line_Data(models.Model):
    _inherit = 'account.invoice.line'
    seller_discount = fields.Float(string='Seller Discount',tracking=True)
    amount = fields.Float(string='Amount',compute='_cal_amount',readonly=True )

    @api.depends('price_unit','quantity')
    def _cal_amount(self):
        for line_items in self:
            line_items.amount = line_items.quantity * line_items.price_unit


class ResPartner_Data(models.Model):
    _inherit = 'res.company'

    address_local_lang =  fields.Text(string = 'Local language address')
    company_name_local_lang = fields.Text(string = 'Company name (in local lang)')  
    
          

