# coding: utf-8
# © 2017 Opener B.V. (<https://opener.amsterdam>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from openerp import http
from openerp.addons.point_of_sale.controllers.main import PosController


class PosRescueController(PosController):
    @http.route('/pos/web', type='http', auth='user')
    def a(self, debug=False, **args):
        """ Inject context value to trigger a filter on non-rescue sessions """
        http.request.context['rescue_test'] = True
        return super(PosRescueController, self).a(debug=debug, **args)
