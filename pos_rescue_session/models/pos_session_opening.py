# coding: utf-8
# © 2017 Opener B.V. (<https://opener.amsterdam>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from openerp import api, models


class PosSessionOpening(models.TransientModel):
    _inherit = 'pos.session.opening'

    @api.multi
    def on_change_config(self, config_id):
        self = self.with_context(rescue_test=True)
        return super(PosSessionOpening, self).on_change_config(config_id)
