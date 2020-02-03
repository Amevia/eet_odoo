from odoo import models, fields


class Company(models.Model):
    _inherit = 'res.company'

    estd_reg_no = fields.Integer(related='partner_id.estd_reg_no', string='Establishment Reg. No.',
                                 readonly=False)
    sale_regime = fields.Selection(related='partner_id.sale_regime', string='Sale Regime',
                                   readonly=False)
