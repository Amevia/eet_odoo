from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    travel_service = fields.Boolean('Travel Service')
    coupon = fields.Boolean('Coupon')
    used_goods = fields.Boolean('Used Goods')
    direct_representation = fields.Boolean('Direct Representation')
    auth_taxpayer_id = fields.Many2one('res.partner', string='Authorized Taxpayer', domain="[('supplier', '=', True)]")

