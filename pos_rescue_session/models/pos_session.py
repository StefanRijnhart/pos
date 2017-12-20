# coding: utf-8
# © 2017 Opener B.V. (<https://opener.amsterdam>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import logging
from openerp import api, fields, models, SUPERUSER_ID
from openerp.addons.point_of_sale.point_of_sale import pos_session
from openerp.exceptions import Warning as UserError
from openerp.osv.expression import normalize_domain, AND
from openerp.tools.translate import _

_logger = logging.getLogger(__name__)


@api.cr_uid_context
@api.returns('self', lambda value: value.id)
def create(self, cr, uid, values, context=None):
    if True:  # keep indentation level
        context = dict(context or {})
        config_id = values.get('config_id', False) or context.get(
            'default_config_id', False)
        if not config_id:
            raise UserError(
                _("You should assign a Point of Sale to your session."))

        # journal_id is not required on the pos_config because it does not
        # exists at the installation. If nothing is configured at the
        # installation we do the minimal configuration. Impossible to do in
        # the .xml files as the CoA is not yet installed.
        jobj = self.pool.get('pos.config')
        pos_config = jobj.browse(cr, uid, config_id, context=context)
        context.update({'company_id': pos_config.company_id.id})
        if not pos_config.journal_id:
            jid = jobj.default_get(
                cr, uid, ['journal_id'], context=context)['journal_id']
            if jid:
                jobj.write(cr, SUPERUSER_ID, [pos_config.id],
                           {'journal_id': jid}, context=context)
            else:
                raise UserError(
                    _("Unable to open the session. You have to assign a sale "
                      "journal to your point of sale."))

        # define some cash journal if no payment method exists
        if not pos_config.journal_ids:
            journal_proxy = self.pool.get('account.journal')
            cashids = journal_proxy.search(
                cr, uid, [('journal_user', '=', True), ('type', '=', 'cash')],
                context=context)
            if not cashids:
                cashids = journal_proxy.search(
                    cr, uid, [('type', '=', 'cash')], context=context)
                if not cashids:
                    cashids = journal_proxy.search(
                        cr, uid, [('journal_user', '=', True)],
                        context=context)

            journal_proxy.write(
                cr, SUPERUSER_ID, cashids, {'journal_user': True})
            jobj.write(
                cr, SUPERUSER_ID, [pos_config.id],
                {'journal_ids': [(6, 0, cashids)]})

        pos_config = jobj.browse(cr, uid, config_id, context=context)
        bank_statement_ids = []
        for journal in pos_config.journal_ids:
            bank_values = {
                'journal_id': journal.id,
                'user_id': uid,
                'company_id': pos_config.company_id.id
            }
            statement_id = self.pool.get('account.bank.statement').create(
                cr, uid, bank_values, context=context)
            bank_statement_ids.append(statement_id)

        values.update({
            'statement_ids': [(6, 0, bank_statement_ids)],
            'config_id': config_id
            # CHANGED: removed 'name' key
        })
        # CHANGE HERE
        if not values.get('name'):
            values['name'] = self.pool['ir.sequence'].get(
                cr, uid, 'pos.session', context=context)
        # END OF CHANGE
        return super(pos_session, self).create(
            cr, uid, values, context=context)


class PosSession(models.Model):
    _inherit = 'pos.session'
    # Make rescue sessions come last to prioritize regular sessions
    _order = 'rescue asc, id desc'

    rescue = fields.Boolean(compute='_compute_rescue', store=True)

    @api.multi
    @api.depends('name')
    def _compute_rescue(self):
        """ This field is added mainly to allow to apply a sorting order by
        non-rescue first (Odoo does not allow a more complex sorting expression
        such as "name like '(RESCUE FOR' asc"), but it also nicely mimics
        the same field in Odoo 11.0 """
        for session in self:
            session.rescue = '(RESCUE FOR' in (session.name or '')

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        """ Inject a clause excluding rescue sessions in case a truthy value
        for 'rescue_test' is in the context. """
        if self.env.context.get('rescue_test', False):
            args = AND([
                normalize_domain(args),
                [('rescue', '=', False)],
            ])
        return super(PosSession, self).search(
            args, offset=offset, limit=limit, order=order, count=count)

    @api.multi
    def _check_unicity(self):
        """ Filter out rescue sessions when checking for unicity """
        self = self.with_context(rescue_test=True)
        return super(PosSession, self)._check_unicity()

    @api.multi
    def _check_pos_config(self):
        """ Filter out rescue sessions when checking for unicity """
        self = self.with_context(rescue_test=True)
        return super(PosSession, self)._check_pos_config()

    @api.model
    def create(self, vals):
        """ Retrieve an existing rescue session or create one if a truthy
        value for 'rescue_for_pos_session_id' is found in the context """
        if self.env.context.get('rescue_for_pos_session_id'):
            # Rescue prefix is not translated because it would make it
            # difficult to recognize them.
            session_name = '(RESCUE FOR %s)' % self.env['pos.session'].browse(
                self.env.context['rescue_for_pos_session_id']).name
            order_name = self.env.context.get('rescue_for_pos_order_name', '-')
            rescue_session = self.search(
                [('name', '=', session_name)], limit=1)
            if rescue_session:
                if rescue_session.state in ('closed', 'closing_control'):
                    raise UserError(
                        _('You are working on a closed session. A recovery '
                          'session was found but it is closed as well: %s')
                        % session_name)
                _logger.warning(
                    'Reusing recovery session %s to save order %s',
                    session_name, order_name)
                return rescue_session
            _logger.warning(
                'Creating recovery session %s to save order %s',
                session_name, order_name)
            vals['name'] = session_name
        return super(PosSession, self).create(vals)

    _constraints = [
        # Redefine constraint to make it use our override
        (_check_unicity,
         "You cannot create two active sessions with the same responsible!",
         ['user_id', 'state']),
        (_check_pos_config,
         ("You cannot create two active sessions related to the same point of "
          "sale!"),
         ['config_id']),
    ]

    def _register_hook(self, cr):
        pos_session.create = create
        return super(PosSession, self)._register_hook(cr)
