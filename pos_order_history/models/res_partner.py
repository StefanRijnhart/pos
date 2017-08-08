# coding: utf-8
# Copyright (C) 2017: Opener B.V. (https://opener.amsterdam)
# @author: Stefan Rijnhart <stefan@opener.am>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from openerp import api, models


class Partner(models.Model):
    _inherit = 'res.partner'

    @api.multi
    def pos_order_history(self):
        """ Gather a concise order history across sale and POS order lines """
        self.ensure_one()
        lines = []
        for pos_line in self.env['pos.order.line'].search(
                self.env['pos.order.line'].pos_order_history_domain(self)):
            lines.append(pos_line.prepare_pos_order_history())
        for sale_line in self.env['sale.order.line'].search(
                self.env['sale.order.line'].pos_order_history_domain(self)):
            lines.append(sale_line.prepare_pos_order_history())
        return sorted(lines, key=lambda line: line['date'], reverse=True)
