# coding: utf-8
# © 2017 Opener B.V. (<https://opener.amsterdam>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from openerp.tests.common import TransactionCase


class TestPosRescueSession(TransactionCase):
    def open_session(self, config):
        session = self.env['pos.session'].create({
            'user_id': self.env.user.id,
            'config_id': config.id,
        })
        session.signal_workflow('open')
        return session

    def get_order(self, session=None):
        if session is None:
            session = self.session
        self.count += 1
        return {
            'to_invoice': False,
            'data': {
                'user_id': session.user_id.id,
                'name': 'Test %s' % self.count,
                'partner_id': False,
                'amount_paid': 100,
                'pos_session_id': session.id,
                'lines': [[0, 0, {
                    'discount': 0,
                    'price_unit': 100,
                    'product_id': self.env.ref('stock.product_icecream').id,
                    'qty': 1
                }]],
                'statement_ids': [[0, 0, {
                    'journal_id': session.statement_ids[0].journal_id.id,
                    'amount': 100,
                    'name': '2018-01-03 10:46:19',
                    'account_id': self.env.ref('account.cash').id,
                    'statement_id': session.statement_ids[0].id,
                }]],
                'amount_tax': 0,
                'amount_return': 0,
                'sequence_number': 1,
                'amount_total': 100,
            },
        }

    def setUp(self):
        """ Set up a pos session and order """
        super(TestPosRescueSession, self).setUp()
        # Apply monkeypatch manually, as _register_hook is only called by the
        # orm after testing
        self.env['pos.session']._register_hook()
        self.count = 0
        self.journal = self.env.ref('account.cash_journal')
        self.session = self.open_session(
            self.env.ref('point_of_sale.pos_config_main'))

    def test_pos_rescue_session(self):
        """A rescue session is created for new orders for a closed sessions"""
        # Process an order and close the session
        self.env['pos.order'].create_from_ui([self.get_order()])
        self.session.signal_workflow('close')
        self.assertEqual(self.session.state, 'closed')

        # A rescue session is created for a new pos order of a closed session
        self.env['pos.order'].create_from_ui([self.get_order()])
        rescue_session = self.env['pos.session'].search([
            ('name', '=', '(RESCUE FOR %s)' % self.session.name)])
        self.assertTrue(rescue_session)
        self.assertEqual(rescue_session.order_ids.pos_reference, 'Test 2')

        # The same session is reused for the next pos order
        self.env['pos.order'].create_from_ui([self.get_order()])
        self.assertEqual(len(rescue_session.order_ids), 2)

        # The rescue session can be closed without any problems
        rescue_session.signal_workflow('close')
        self.assertEqual(rescue_session.state, 'closed')

    #def test_pos_rescue_session_new_session(self):

