from odoo import models, fields, api



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


class AccountInvoice_Data(models.Model):
    _inherit = 'account.invoice'

    # seller_discount = fields.Float(string = 'Seller Discount',readonly=True, tracking=True)

    channel_order_number = fields.Char(string = 'Channel Order No.',readonly=True, tracking=True)
    #address_local_lang =  fields.Text(string = 'Address (Thai)', tracking=True,readonly=True)




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

    """@api.depends('amount_untaxed','calculated_discount')
    def _cal_grand_total(self):
        for order in self:
            order.grand_total = order.amount_untaxed + order.calculated_discount

    grand_total = fields.Float(string = 'Grand Total', store = True, compute = '_cal_grand_total')
"""
    @api.depends('invoice_line_ids.seller_discount', 'invoice_line_ids.price_unit','invoice_line_ids.amount','invoice_line_ids.quantity')
    def _cal_total_baht_escl_vat(self):
        for orders in self:
            total_excl_vat = 0
            for line_items in orders.invoice_line_ids:
                total_excl_vat = total_excl_vat + (line_items.amount - (line_items.seller_discount * line_items.price_unit * line_items.quantity)/100)
            orders.total_baht_excl_VAT = total_excl_vat

    total_baht_excl_VAT = fields.Float(string = 'Total Baht Excl VAT', compute = '_cal_total_baht_escl_vat', store= True, digits=(12,4))

    @api.depends('invoice_line_ids.invoice_line_tax_ids.amount','invoice_line_ids.seller_discount','invoice_line_ids.price_unit','invoice_line_ids.amount','invoice_line_ids.quantity')
    def _cal_total_baht_incl_vat(self):
        for orders in self:
            total_incl_vat = 0
            for line_items in orders.invoice_line_ids:
                total_incl_vat = total_incl_vat + ((line_items.amount - (line_items.seller_discount * line_items.price_unit * line_items.quantity)/100) + (line_items.invoice_line_tax_ids.amount/100 * (line_items.amount - (line_items.seller_discount * line_items.price_unit * line_items.quantity)/100)))
            orders.total_baht_incl_VAT = total_incl_vat

    total_baht_incl_VAT = fields.Float(string = 'Total Baht Incl VAT', compute = '_cal_total_baht_incl_vat', store = True, digits=(12,4))

    @api.depends('total_baht_excl_VAT','total_baht_incl_VAT')
    def _cal_total_vat(self):
        for orders in self:
            orders.vat = orders.total_baht_incl_VAT - orders.total_baht_excl_VAT

    vat = fields.Float(string = 'Vat', compute = '_cal_total_vat', store = True, digits=(12,4))

    
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

