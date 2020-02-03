from odoo import models, fields


class AccountTax(models.Model):
    _inherit = 'account.tax'

    rate_type = fields.Selection([
        ('basic', 'Basic'),
        ('first_reduced', 'First Reduced'),
        ('second_reduced', 'Second Reduced')
    ], string='VAT Rate Type', default='basic')
