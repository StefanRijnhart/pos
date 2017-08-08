openerp.pos_order_history = function(instance, local) {

    module = instance.point_of_sale;
    var QWeb = instance.web.qweb;
    var _t = instance.web._t;

    module.ClientListScreenWidget = module.ClientListScreenWidget.extend({
        display_client_details: function(visibility, partner, clickpos){
            this._super(visibility, partner, clickpos);
            var self = this;
            var contents = this.$('.client-details-contents');
            contents.off('click', '.button.history');
            if (partner && visibility=='show'){
                this.pos_widget.clientorderlist_screen.partner = partner;
                contents.on('click','.button.history',function(){ self.client_history(); });
            }
        },
        client_history: function(){
            var ss = this.pos_widget.screen_selector;
            ss.set_current_screen('clientorderlist');
        },
    });

    module.PosWidget = module.PosWidget.extend({
        build_widgets: function() {
	    this._super();
            this.clientorderlist_screen = new module.ClientOrderListScreenWidget(this, {});
            this.clientorderlist_screen.appendTo(this.$('.screens'));
            this.clientorderlist_screen.hide();
            this.screen_selector.screen_set.clientorderlist = this.clientorderlist_screen;
	},
    });

    module.ClientOrderListScreenWidget = module.ScreenWidget.extend({
        template: 'ClientOrderListScreenWidget',
        show_leftpane: false,

        show: function(){
            var self = this;
            this._super();
            this.renderElement();
            this.load_order_history();

            this.$('.back').click(function(){
                self.pos_widget.screen_selector.back();
                self.pos_widget.pos.get('selectedOrder').set_screen_data('previous-screen', 'products');
                self.pos_widget.clientlist_screen.new_client = self.partner;
                self.pos_widget.clientlist_screen.display_client_details('show', self.partner);
            });
        },
        render_list: function(history){
            var contents = this.$el[0].querySelector('.clientorder-list-contents');
            contents.innerHTML = "";
            for(var i = 0, len = Math.min(history.length,1000); i < len; i++){
                var orderline    = history[i];
                var clientorderline_html = QWeb.render('ClientOrderLine',{widget: this, orderline: orderline});
                var clientorderline = document.createElement('tbody');
                clientorderline.innerHTML = clientorderline_html;
                clientorderline = clientorderline.childNodes[1];
                contents.appendChild(clientorderline);
            }
        },
        load_order_history: function(){
            var self = this;
            this.$el.find('.client-name').text(_t('Order history of ') + this.partner.name);
            var res = new instance.web.Model('res.partner').call('pos_order_history', [[this.partner.id]]).then(
                function(history){self.render_list(history);}).fail(function (error, event){
                    if (parseInt(error.code) === 200) {
		        // Business Logic Error, not a connection problem
		        self.pos_widget.screen_selector.show_popup(
                            'error-traceback', {
			        message: error.data.message,
			        comment: error.data.debug
                            });
                    }
                    else{
		        self.pos_widget.screen_selector.show_popup('error',{
                            message: _t('Connection error'),
                            comment: _t('Can not execute this action because the POS is currently offline'),
		        });
                    }
                    event.preventDefault();
	        });
        },
    });
};
