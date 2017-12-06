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
    def _prepare_sale_order_vals(self, data):
        pos_session = self.env['pos.session'].browse(
            data['pos_session_id'])
        config = pos_session.config_id
        warehouse = config.picking_type_id.warehouse_id
        if not warehouse:
            raise UserError(_(
                'Please configure a warehouse on the Picking Type in the '
                'POS configuration'))
        res = {
            'pricelist_id': config.pricelist_id.id,
            'warehouse_id': warehouse.id,
            'section_id': data.get('section_id') or False,
            'user_id': data.get('user_id') or False,
            'session_id': data['pos_session_id'],
            'pos_reference': data['name'],
            'partner_id': data['partner_id'],
            'order_policy': 'manual',
            'pos_process_picking': True,
        }
        partner = self.env['res.partner'].browse(data['partner_id'])
        if partner.property_account_position:
            res['fiscal_position'] = partner.property_account_position.id
        return res

    @api.multi
    def _update_sale_order_vals(self, data):
        return {
            'session_id': data['pos_session_id'],
            'pos_reference': data['name'],
            'partner_id': data['partner_id'],
        }

    @api.model
    def create_from_ui(self, ui_orders):
        print ui_orders
        """ Create regular orders only for orders without a partner, and
        create or update a sale order otherwise. """
        pos_orders = []
        for ui_order in ui_orders:
            if not ui_order['data'].get('partner_id'):
                pos_orders.append(ui_order)
                continue
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
                            # Confirm order, confirm invoices and reconcile
                            order.pos_reconcile(st_lines)
                    except OperationalError:
                        raise
                    except Exception as e:
                        order.message_post_from_pos(
                            'Error during reconciliation: %s' % e)
            order.do_pos_process_pickings()
            order.hook_sale_order_from_pos()
        return super(PosOrder, self).create_from_ui(pos_orders)

    @api.model
    def create_or_update_sale_order(self, pos_order):
        sale_obj = self.env['sale.order']
        data = pos_order['data']
        if sale_obj.search([
                ('pos_reference', '=', data['name']),
                ('session_id', '=', data['pos_session_id'])]):
            # This order creation or update has already been processed.
            # TODO: add UUID and keep track of processed order commands
            # for all pos order commands in a generic module independent of
            # this one (for sale and pos orders alike)
            return False
        vals = self._prepare_sale_order_vals(data)
        if data.get('sale_id'):
            order = self.env['sale.order'].browse(data['sale_id'])
            if order.state not in ('draft', 'sent'):
                order.message_post_from_pos(
                    'Conflict between backend and POS. Could not write '
                    'the following data because the order is already '
                    'confirmed: %s' % data)
                return False
            order.write(self._update_sale_order_vals(data))
            order.write({
                'pos_reference': data['name'],
                'session_id': data['pos_session_id']})
            order.order_line.unlink()
            _logger.debug('Updated sale order %s from POS', order.name)
        else:
            order = sale_obj.create(vals)
            _logger.debug('Created sale order %s from POS', order.name)

        # (re)create sale order lines
        for line in data['lines']:
            self._update_sale_order_line_vals(vals, line[2])
        order.write({'order_line': data['lines']})

        session = self.env['pos.session'].browse(
            data['pos_session_id'])
        if session.sequence_number <= data['sequence_number']:
            session.write(
                {'sequence_number': data['sequence_number'] + 1})
        return order
