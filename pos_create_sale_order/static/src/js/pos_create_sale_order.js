openerp.pos_create_sale_order = function(instance) {
    var module = instance.point_of_sale;
    var _t = instance.web._t;
    var qweb = instance.web.qweb;

    var origClientListScreenWidget = module.ClientListScreenWidget;
    module.ClientListScreenWidget = module.ClientListScreenWidget.extend({
        display_client_details: function(visibility,partner,clickpos) {
            var self = this;
            origClientListScreenWidget.prototype.display_client_details.apply(this, arguments);
            if (visibility == 'show'){
                self.$('.sale-orders').on('click', 'tr', function(){
                    self.pos.fetch_sale_order(parseInt($(this).data('id')));
                    self.pos.pos_widget.screen_selector.back();
                });
            }
        },
        show: function(){
            origClientListScreenWidget.prototype.show.apply(this);
            var self = this;
            this.$('input.has_orders').click(function(){
                var query = self.$('.searchbox input')[0].value;
                self.perform_search(query);
            });
        },
        render_list: function(partners){
            var filtered_partners = [];
            if ($('input.has_orders')[0].checked){
                _.each(partners, function(partner){
                    if (partner.pos_sale_orders && partner.pos_sale_orders.length){
                        filtered_partners.push(partner);
                    }
                });
                partners = filtered_partners;
            }
            origClientListScreenWidget.prototype.render_list.apply(this, [partners]);
        }
    });

    var origPosDB = module.PosDB;
    module.PosDB = module.PosDB.extend({
        init: function(options){
            this.sale_orders = {};
            return origPosDB.prototype.init(options);
        },

        add_partners: function(partners){
            var all_order_ids = [];
            _.each(partners, function(partner){
                all_order_ids.push.apply(all_order_ids, partner.pos_sale_orders);
            });
            var self = this;
            res = origPosDB.prototype.add_partners.apply(this, arguments);
            new instance.web.Model('sale.order').get_func("read")(
                all_order_ids, ['name', 'date_order', 'amount_total', 'lines_as_text']).then(function(orders){
                    _.each(orders, function(order){
                        self.sale_orders[order.id] = order;
                    });
                    _.each(partners, function(partner){
                        order_ids = partner.pos_sale_orders;
                        partner.pos_sale_orders = [];
                        _.each(order_ids, function(order_id){
                            partner.pos_sale_orders.push(self.sale_orders[order_id]);
                        });
                    });
                });
            return res;
        }
    });

    origOrder = module.Order;
    module.Order = module.Order.extend({
        // Propagate save_unpaid_sale property to backend
        export_as_JSON: function() {
            // Set sale id or draft sale order flag
            res = origOrder.prototype.export_as_JSON.apply(this, arguments);
            if (this.save_unpaid_sale) {
                res.save_unpaid_sale = this.save_unpaid_sale;
            }
            if (this.sale_id) {
                res.sale_id = this.sale_id;
            }
            return res;
        },
        export_for_printing: function() {
            // Set sale order number for printing purposes
            res = origOrder.prototype.export_for_printing.apply(this, arguments);
            if (this.sale_name) {
                res.name = this.sale_name;
            }
            return res;
        },
    });

    origOrderline = module.Orderline;
    module.Orderline = module.Orderline.extend({
        export_as_JSON: function() {
            res = origOrderline.prototype.export_as_JSON.apply(this, arguments);
            res.name = this.get_name();
            return res;
        },
        export_for_printing: function() {
            res = origOrderline.prototype.export_for_printing.apply(this, arguments);
            res.product_name = this.get_name();
            return res;
        },
        get_name: function() {
            return this.name || this.get_product().display_name;
        },
    });

    module.SaveUnpaidSaleWidget = module.PosBaseWidget.extend({
        template: 'SaveUnpaidSaleWidget',
        next_screen: 'receipt',
        init: function(parent){
            this._super(parent);
            this.pos = parent.pos;
        },
        save_unpaid_sale: function() {
            // queue to save as unpaid sale order
            // TODO: Print some kind of receipt?
            // and clear screen.
            var order = this.pos.get_order();
            if(order.get('orderLines').models.length === 0){
                this.pos.pos_widget.screen_selector.show_popup('error',{
                    'message': _t('Empty Order'),
                    'comment': _t('There must be at least one product in your order before it can be validated'),
                });
                return;
            }
            if (!order.get_client()) {
                this.pos.pos_widget.screen_selector.show_popup('error',{
                    'message': _t('Missing customer'),
                    'comment': _t('To save as a sale order you must select a customer'),
                });
                return;
            }
            order.save_unpaid_sale = true;
            this.pos.push_order(order);
            if(this.pos.config.iface_print_via_proxy){
                var receipt = order.export_for_printing();
                this.pos.proxy.print_receipt(qweb.render('XmlReceipt',{
                    receipt: receipt, widget: self,
                }));
                this.pos.get('selectedOrder').destroy();    //finish order and go back to scan screen
            }else{
                this.pos_widget.screen_selector.set_current_screen(this.next_screen);
            }
        },
        renderElement: function() {
            var self = this;
            this._super();
            this.$el.click(function(){
                // TODO: ask for confirmation,
                self.save_unpaid_sale();
            });
        },
    });

    module.PaypadWidget = module.PaypadWidget.extend({
        renderElement: function() {
            this._super();
            var button = new module.SaveUnpaidSaleWidget(this);
            button.appendTo(this.$el);
        },
    });

    var _posmodel_initialize = module.PosModel.prototype.initialize;
    module.PosModel.prototype.initialize = function(session, attributes){
        // Select POS sale orders when loading partners
        var self = this;
        _.each(self.models, function(model) {
            if (model.model === 'res.partner') {
                model.fields.push('pos_sale_orders');
            }
        });
        return _posmodel_initialize.apply(this, arguments);
    };

    var _posmodel_load_new_partners = module.PosModel.prototype.load_new_partners;
    module.PosModel.prototype.load_new_partners = function(){
        /* Overwriting the method on this model, which only checks for write_date.
           The problem with inheriting is the race condition on the POS' partner_write_date,
        */
        var self = this;
        var fields = _.find(this.models,function(model){ return model.model === 'res.partner'; }).fields;
        var write_date = this.db.get_partner_write_date();
        var def = $.Deferred();
        new instance.web.Model('res.partner')
            .query(fields)
            .filter(['|', ['write_date', '>', write_date], ['pos_sale_order_write_date', '>', write_date]])
            .all({'timeout':3000, 'shadow': true})
            .then(function(partners){
                self.db.add_partners(partners);
                _.each(partners, function(partner){
                    self.db.partner_by_id[partner.id] = partner;
                });
                if (partners.length > 0){
                    def.resolve();
                } else {
                    def.reject();
                }
            }, function(err,event){
                event.preventDefault(); def.reject();
            });
        return def;
    };

    module.PosModel.prototype.load_sale_order = function(sale) {
        // TODO: prevent other customer to be selected on existing sale order
        this.add_new_order();
        var order = this.get_order();
        order.set_client(this.db.get_partner_by_id(sale.partner_id[0]));
        order.sale_id = sale.id;
        order.sale_name = sale.name;
        var self = this;
        _.each(sale.order_line, function(sale_line){
            // TODO: error out if product can not be found (not available in POS)
            var pos_line = new module.Orderline({}, {
                pos: self,
                order: order,
                product: self.db.get_product_by_id(sale_line.product_id[0])});
            pos_line.set_quantity(sale_line.product_uom_qty);
            pos_line.name = sale_line.name;
            if (sale_line.discount) {
                pos_line.set_discount(sale_line.discount);
            }
            pos_line.set_unit_price(sale_line.price_unit);
            order.get('orderLines').add(pos_line);
        });
        order.selectLine(order.getLastOrderline());
        return order;
    };

    module.PosModel.prototype.fetch_sale_order = function(sale_id) {
        var self = this;
        new instance.web.Model('sale.order').call(
            'load_from_pos', [sale_id]).then(function (sale) {
                self.load_sale_order(sale);
            }).fail(function (error, event){
                self.pos_widget.screen_selector.show_popup('error-traceback',{
                    message: error.data.message,
                    comment: error.data.debug,
                });
            });
    };
};
