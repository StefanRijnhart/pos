# coding: utf-8
# © 2016 Akretion
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp import fields, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    stock_location_id = fields.Many2one(
        'stock.location',
        string='Stock Location',
        related='picking_type_id.warehouse_id.lot_stock_id',
        readonly=True, store=True,
        required=False)
