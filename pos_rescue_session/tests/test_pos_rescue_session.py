# coding: utf-8
# © 2017 Opener B.V. (<https://opener.amsterdam>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from openerp.tests.common import TransactionCase


class TestPosRescueSession(TransactionCase):
    def setUp(self):
        """ Set up a pos session and order """
        super(TestPosRescueSession, self).setUp()
        # Apply monkeypatch manually, as _register_hook is only called by the
        # orm after testing
        self.env['pos.session']._register_hook()
        user = self.env.ref('base.user_root')
        self.session = self.env['pos.session'].create({
            'user_id': user.id,
            'config_id': self.env.ref('point_of_sale.pos_config_main').id,
        })
        journal = self.env.ref('account.cash_journal')
        self.session.signal_workflow('open')
        statement = self.env['account.bank.statement'].search([
            ('pos_session_id', '=', self.session.id),
            ('journal_id', '=', journal.id),
        ])
        self.order = {
            'to_invoice': False,
            'data': {
                'user_id': user.id,
                'name': 'Test 1',
                'partner_id': False,
                'amount_paid': 100,
                'pos_session_id': self.session.id,
                'lines': [[0, 0, {
                    'discount': 0,
                    'price_unit': 100,
                    'product_id': self.env.ref('stock.product_icecream').id,
                    'qty': 1
                }]],
                'statement_ids': [[0, 0, {
                    'journal_id': journal.id,
                    'amount': 100,
                    'name': '2018-01-03 10:46:19',
                    'account_id': self.env.ref('account.cash').id,
                    'statement_id': statement.id,
                }]],
                'amount_tax': 0,
                'amount_return': 0,
                'sequence_number': 1,
                'amount_total': 100,
            },
        }

    def test_pos_rescue_session(self):
        """A rescue session is created for new orders for a closed sessions"""
        # Process an order and close the session
        self.env['pos.order'].create_from_ui([self.order])
        self.session.signal_workflow('close')
        self.assertEqual(self.session.state, 'closed')

        # A rescue session is created for a new pos order of a closed session
        self.order['data']['name'] = 'Test 2'
        self.env['pos.order'].create_from_ui([self.order])
        rescue_session = self.env['pos.session'].search([
            ('name', '=', '(RESCUE FOR %s)' % self.session.name)])
        self.assertTrue(rescue_session)
        self.assertEqual(rescue_session.order_ids.pos_reference, 'Test 2')

        # The same session is reused for the next pos order
        self.order['data']['name'] = 'Test 3'
        self.env['pos.order'].create_from_ui([self.order])
        self.assertEqual(len(rescue_session.order_ids), 2)

        # The rescue session can be closed without any problems
        rescue_session.signal_workflow('close')
        self.assertEqual(rescue_session.state, 'closed')
