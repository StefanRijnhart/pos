// © 2017 Opener B.V. (<https://opener.amsterdam>)
// License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
openerp.pos_rescue_session = function(instance, local) {
    module = instance.point_of_sale;

    var initialize_original = module.PosModel.prototype.initialize;
    module.PosModel = module.PosModel.extend({

        initialize: function(session, attributes) {
            // Amend this model's domain to exclude rescue sessions
            var self = this;
            for (var i = 0 ; i < this.models.length; i++){
                if (this.models[i].model == 'pos.session') {
                    this.models[i].domain = function(self){
                        return [['state', '=', 'opened'],
                                ['user_id', '=', self.session.uid],
                                ['name', 'not like', '(RESCUE FOR']
                               ];
                    };
                }
            }
            return initialize_original.call(this, session, attributes);
        }
    });
}
