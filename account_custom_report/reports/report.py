# -*- coding:utf-8 -*-

# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class AccountCustomReport(models.AbstractModel):
    _name = 'report.account_custom_report.report_custom_account'  # report.modulename.your_modelname of report

    @api.model
    def _get_report_values(self, docids, data=None):
        acct_invoice = self.env["account.invoice"].search([("id", "=", docids)])
        # for s in acct_invoice.invoice_line_ids:
        #     s.product_id.name

        return {
            'account': acct_invoice,
            'doc_model': 'account.invoice',
            'proforma': True
        }
