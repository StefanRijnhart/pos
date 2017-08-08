# coding: utf-8
# Copyright (C) 2017: Opener B.V. (https://opener.amsterdam)
# @author: Stefan Rijnhart <stefan@opener.am>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from openerp import api, fields, models


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    @api.model
    def pos_order_history_domain(self, partner):
        return [
            ('order_id.partner_id', '=', partner.id),
            ('order_id.state', 'not in', ('draft', 'cancel')),
        ]

    @api.multi
    def prepare_pos_order_history(self):
        self.ensure_one()
        return {
            'name': self.product_id.name,
            'qty': self.qty,
            'reference': self.order_id.name,
            'date': fields.Date.context_today(
                self, fields.Datetime.from_string(self.order_id.date_order)),
        }
