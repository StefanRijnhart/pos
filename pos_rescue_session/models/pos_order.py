# coding: utf-8
# © 2017 Opener B.V. (<https://opener.amsterdam>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from openerp import api, models


class PosOrder(models.Model):
    _inherit = 'pos.order'

    @api.model
    def _get_valid_session(self, order):
        """ Inject the original session id which triggers the creation of a
        rescue session """
        self = self.with_context(
            rescue_for_pos_session_id=order['pos_session_id'],
            rescue_for_pos_order_name=order['name'])
        return super(PosOrder, self)._get_valid_session(order)
