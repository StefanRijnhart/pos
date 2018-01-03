# coding: utf-8
from openerp import fields, models


class PosUUID(models.Model):
    _name = 'pos.uuid'

    name = fields.Char(required=True, index=True)
    sale_order = fields.Many2one(
        'sale.order', required=True, ondelete='CASCADE')

    _sql_constraints = [
        # While UUID are inherently unique, the uniqueness constraint helps to
        # prevent double processing of data with the same uuid simultaneously
        ('pos_uuid_name_unique', 'UNIQUE(name)', 'UUID already exists'),
    ]
