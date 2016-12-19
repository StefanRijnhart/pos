# coding: utf-8
from openerp.osv.expression import AND
from openerp import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def get_pos_sale_order_domain(self):
        """ What constitutes a sale order that can show up in POS? """
        return [('state', 'in', ('draft', 'sent'))]

    @api.multi
    @api.depends('pos_sale_orders')
    def compute_pos_sale_order_write_date(self):
        for partner in self:
            partner.pos_sale_order_write_date = max(
                so.write_date for so in partner.pos_sale_orders
            ) if partner.pos_sale_orders else False

    def search_pos_sale_order_write_date(self, operator, value):
        partners = self.env['sale.order'].search(AND([
            ['|', ('write_date', '>', value), ('create_date', '>', value)],
            self.get_pos_sale_order_domain()])).mapped('partner_id')
        return [('id', 'in', partners.ids)]

    def compute_pos_sale_orders(self):
        for partner in self:
            domain = AND([
                [('partner_id', '=', partner.id)],
                self.get_pos_sale_order_domain(),
            ])
            partner.pos_sale_orders = self.env['sale.order'].search(domain)

    pos_sale_order_write_date = fields.Date(
        compute='compute_pos_sale_order_write_date',
        search='search_pos_sale_order_write_date')
    pos_sale_orders = fields.Many2many(
        comodel_name='sale.order', compute='compute_pos_sale_orders')
