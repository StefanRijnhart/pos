# coding: utf-8
# © 2016 Akretion
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging
from psycopg2 import OperationalError
from openerp import models, api, _
from openerp.exceptions import Warning as UserError

_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _inherit = 'pos.order'

    @api.multi
    def _prepare_product_onchange_params(self, order, line):
        return [
            (order['pricelist_id'], line['product_id']),
            {
                'qty': line['product_uom_qty'],
                'uom': False,
                'qty_uos': 0,
                'uos': False,
                'name': '',
                'partner_id': order['partner_id'],
                'lang': False,
                'update_tax': True,
                'date_order': False,
                'packaging': False,
                'fiscal_position': order.get('fiscal_position'),
                'flag': False,
                'warehouse_id': order['warehouse_id']
            }]

    @api.multi
    def _merge_product_onchange(self, order, onchange_vals, line):
        default_key = [
            'name',
            'product_uos_qty',
            'product_uom',
            'th_weight',
            'product_uos']
        for key in default_key:
            line[key] = onchange_vals.get(key)
        if 'tax_id' not in line and onchange_vals.get('tax_id'):
            line['tax_id'] = [[6, 0, onchange_vals['tax_id']]]

    @api.multi
    def _update_sale_order_line_vals(self, order, line):
        sale_line_obj = self.env['sale.order.line'].browse(False)
        if 'tax_ids' in line:  # pos_pricelist's support for fiscal positions
            line['tax_id'] = line.pop('tax_ids')
        line['product_uom_qty'] = line.pop('qty', 0)
        args, kwargs = self._prepare_product_onchange_params(order, line)
        vals = sale_line_obj.product_id_change_with_wh(*args, **kwargs)
        self._merge_product_onchange(order, vals['value'], line)

    @api.multi
    def _prepare_sale_order_vals(self, ui_order):
        pos_session = self.env['pos.session'].browse(
            ui_order['pos_session_id'])
        config = pos_session.config_id
        if not ui_order['partner_id']:
            # TODO: don't create sale orders for these orders?
            raise NotImplementedError
        warehouse = config.picking_type_id.warehouse_id
        if not warehouse:
            raise UserError(_(
                'Please configure a warehouse on the Picking Type in the '
                'POS configuration'))
        res = {
            'pricelist_id': config.pricelist_id.id,
            'warehouse_id': warehouse.id,
            'section_id': ui_order.get('section_id') or False,
            'user_id': ui_order.get('user_id') or False,
            'session_id': ui_order['pos_session_id'],
            'pos_reference': ui_order['name'],
            'partner_id': ui_order['partner_id'],
            'order_policy': 'manual',
        }
        partner = self.env['res.partner'].browse(ui_order['partner_id'])
        if partner.property_account_position:
            res['fiscal_position'] = partner.property_account_position.id
        return res

    @api.multi
    def _update_sale_order_vals(self, ui_order):
        return {
            'session_id': ui_order['pos_session_id'],
            'pos_reference': ui_order['name'],
            'partner_id': ui_order['partner_id'],
        }

    @api.model
    def create_from_ui(self, ui_orders):
        print ui_orders
        """ TODO: refactor into core methods _process_order and action_invoice,
        so that it does not need to be overwritten (does not call super).
        At least, create regular orders for orders without a partner. """
        pos_orders = []
        for ui_order in ui_orders:
            if (ui_order['data'].get('save_unpaid_sale') or
                    ui_order['data'].get('sale_id')):
                order = self.create_or_update_sale_order(ui_order)
                if not order:
                    continue
                if ui_order['data'].get('statement_ids'):
                    st_lines = self.env['account.bank.statement.line']
                    for payment in ui_order['data']['statement_ids']:
                        st_lines += order.pos_add_payment(payment)
                    if st_lines:
                        try:
                            with self.env.cr.savepoint():
                                order.pos_reconcile(st_lines)
                        except OperationalError:
                            raise
                        except Exception as e:
                            order.message_post_from_pos(
                                'Error during reconciliation: %s' % e)
                # TODO: If to_invoice: confirm, create invoice
                #     check ui callback!
                # Otherwise, do we query order.confirm_sale_from_pos(ui_order)?
                # Or can we leave this to sale_automatic_workflow instead?
                # Process pickings, also something to make configurable
                order.pos_process_pickings()
            else:
                pos_orders.append(ui_order)
        return super(PosOrder, self).create_from_ui(pos_orders)

    @api.model
    def create_or_update_sale_order(self, pos_order):
        sale_obj = self.env['sale.order']
        ui_order = pos_order['data']
        if sale_obj.search([
                ('pos_reference', '=', pos_order['data']['name']),
                ('session_id', '=', pos_order['data']['pos_session_id'])]):
            return False
        vals = self._prepare_sale_order_vals(ui_order)
        if ui_order.get('sale_id'):
            order = self.env['sale.order'].browse(ui_order['sale_id'])
            order.write(self._update_sale_order_vals(ui_order))
            if order.state not in ('draft', 'sent'):
                order.message_post_from_pos(
                    body=(
                        'Conflict between backend and POS. Could not write '
                        'the following data because the order is already '
                        'confirmed: %s' % ui_order))
                return False
            order.write({
                'pos_reference': ui_order['name'],
                'session_id': ui_order['pos_session_id']})
            order.order_line.unlink()
            _logger.debug('Updated sale order %s from POS', order.name)
        else:
            order = sale_obj.create(vals)
            _logger.debug('Created sale order %s from POS', order.name)

        # (re)create sale order lines
        for line in ui_order['lines']:
            self._update_sale_order_line_vals(vals, line[2])
        order.write({'order_line': ui_order['lines']})

        session = self.env['pos.session'].browse(
            ui_order['pos_session_id'])
        if session.sequence_number <= ui_order['sequence_number']:
            session.write(
                {'sequence_number': ui_order['sequence_number'] + 1})
        return order
