odoo.define('eet_cz.screens', function (require) {
"use strict";

var screens = require('point_of_sale.screens');

screens.PaymentScreenWidget.include({
    finalize_validation: function() {
        var self = this;
        var order = this.pos.get_order();

        if (order.is_paid_with_cash() && this.pos.config.iface_cashdrawer) {

                this.pos.proxy.open_cashbox();
        }

        order.initialize_validation_date();
        order.finalized = true;

        if (order.is_to_invoice()) {
            var invoiced = this.pos.push_and_invoice_order(order);
            this.invoicing = true;

            invoiced.fail(this._handleFailedPushForInvoice.bind(this, order, false));

            invoiced.done(function(){
                self.invoicing = false;
            });
        } else {
            this.pos.push_order(order);
        }

    },
});
});

