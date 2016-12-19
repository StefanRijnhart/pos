# coding: utf-8
# © 2016 Akretion
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from openerp import fields, models, api
from openerp.exceptions import Warning as UserError
from openerp.tools.translate import _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    _sql_constraints = [('pos_reference_uniq',
                         'unique (pos_reference, session_id)',
                         'The POS reference must be uniq per session')]
    pos_reference = fields.Char(
        string='POS Receipt', readonly=True, copy=False)
    session_id = fields.Many2one(
        'pos.session', string='POS Session', readonly=True, copy=False)
    lines_as_text = fields.Text(compute='compute_lines_as_text')

    @api.multi
    def compute_lines_as_text(self):
        for sale in self:
            sale.lines_as_text = '\n'.join(
                '%s x %s' % (line.product_uos_qty, line.name)
                for line in sale.order_line)

    @api.multi
    def do_confirm_sale_from_pos(self, ui_order):
        """ API hook to make sale confirmation optional. Refactor to config """
        self.ensure_one()
        return True

    @api.model
    def get_pos_order_fields(self):
        return ['partner_id', 'name']

    @api.model
    def get_pos_order_line_fields(self):
        return [
            'name',
            'product_id',
            'price_unit',
            'discount',
            'product_uom_qty',
        ]

    @api.model
    def load_from_pos(self, res_id):
        # TODO: refactor to api.multi + ensure_one()
        order = self.browse(res_id)
        res = order.read(self.get_pos_order_fields())[0]
        if any(not l.product_id for l in order.order_line):
            raise UserError(
                _('Cannot load a sale order with a line that has no product'))
        res['order_line'] = order.order_line.read(
            self.get_pos_order_line_fields())
        return res

    @api.multi
    def _prepare_pos_payment_vals(self, data):
        self.ensure_one()
        accounting_partner = self.env['res.partner']._find_accounting_partner(
            self.partner_id)

        account = accounting_partner.property_account_receivable
        if not account:  # TODO: fix raise at runtime
            msg = _('There is no receivable account defined '
                    'to make payment for the partner: "%s" (id:%d).') % (
                        self.partner_id.name, self.partner_id.id,)
            raise UserError(_('Configuration Error!'), msg)

        args = {
            'amount': data['amount'],
            'date': data.get('payment_date', fields.Date.context_today(self)),
            'name': self.name + ': ' + (data.get('payment_name', '') or ''),
            'partner_id': accounting_partner.id,
            'account_id': account.id,
        }

        journal_id = data.get('journal', False)
        statement_id = data.get('statement_id', False)
        assert journal_id or statement_id, (
            'No statement_id and no journal_id passed to the method!')

        for statement in self.session_id.statement_ids:
            if statement.id == statement_id:
                journal_id = statement.journal_id.id
                break
            elif statement.journal_id.id == journal_id:
                statement_id = statement.id
                break

        if not statement_id:
            raise UserError(_('Error!'),
                            _('You have to open at least one cashbox.'))

        args.update({
            'statement_id': statement_id,
            'journal_id': journal_id,
            'ref': self.session_id.name,
        })

        return args

    @api.multi
    def pos_add_payment(self, payment):
        self.ensure_one()
        vals = self._prepare_pos_payment_vals(payment[2])
        st_line = self.env['account.bank.statement.line'].create(vals)
        mv_line_dict = {
            'debit': st_line.amount < 0 and -st_line.amount or 0.0,
            'credit': st_line.amount > 0 and st_line.amount or 0.0,
            'account_id': st_line.account_id.id,
            'partner_id': st_line.partner_id.id,
            'name': st_line.name
        }
        st_line.process_reconciliation([mv_line_dict])
        return st_line

    @api.multi
    def pos_reconcile(self, st_lines):
        """ Reconcile the order with the created transactions. If necessary,
        confirm order and create and confirm invoices. Take into account any
        existing partial reconciliations (does the POS UI even allow this? """
        self.ensure_one()
        account = st_lines[0].account_id
        if self.state in ('draft', 'sent'):
            self.action_button_confirm()
        self.signal_workflow('manual_invoice')
        draft_invoices = self.invoice_ids.filtered(
            lambda i: i.state == 'draft')
        if draft_invoices:
            draft_invoices.signal_workflow('invoice_open')
        moves = self.invoice_ids.mapped(
            'move_id') + st_lines.mapped('journal_entry_id')
        move_lines = moves.mapped('line_id').filtered(
            lambda l: l.account_id == account and not l.reconcile_id)
        to_reconcile = self.env['account.move.line']
        partial_seen = self.env['account.move.reconcile']
        for move_line in move_lines:
            if move_line.reconcile_partial_id:
                if move_line.reconcile_partial_id in partial_seen:
                    continue
                partial_seen += move_line.reconcile_partial_id
                to_reconcile += move_line.reconcile_partial_id.line_partial_ids
            else:
                to_reconcile += move_line
        if len(to_reconcile) > 1:
            to_reconcile.reconcile_partial()
        partial_seen.unlink()
        return (to_reconcile[0].reconcile_id or
                to_reconcile[0].reconcile_partial_id)

    @api.multi
    def pos_process_single_picking(self, picking):
        picking.force_assign()
        picking.do_transfer()

    @api.multi
    def pos_process_pickings(self):
        self.ensure_one()
        for picking in self.picking_ids.filtered(
                lambda p: p.state not in ('done', 'cancel', 'draft')):
            try:
                with self.env.cr.savepoint():
                    self.pos_process_single_picking(picking)
            except Exception as e:
                self.message_post(body=(
                    'Error processing shipping %s: %s' % (picking.name, e)))
