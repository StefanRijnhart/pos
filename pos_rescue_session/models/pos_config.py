# coding: utf-8
# © 2017 Opener B.V. (<https://opener.amsterdam>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from openerp import api, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    @api.multi
    def name_get(self):
        self = self.with_context(rescue_test=True)
        return super(PosConfig, self).name_get()
