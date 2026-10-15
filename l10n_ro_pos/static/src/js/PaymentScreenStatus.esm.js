import {PaymentScreenStatus} from "@point_of_sale/app/screens/payment_screen/payment_status/payment_status";
import {patch} from "@web/core/utils/patch";

patch(PaymentScreenStatus.prototype, {
    get warningMessage() {
        let message = false;
        let value = 0;

        const paymentlines = this.props.order.payment_ids;

        for (let i = 0; i < paymentlines.length; i++) {
            const line = paymentlines[i];
            // Odoo 20: is_cash_count a fost eliminat (era type === "cash")
            if (line.payment_method_id.type === "cash") {
                value += line.amount;
            }
        }
        if (value >= 5000) {
            message = "L5000";
        }
        if (value >= 10000) {
            message = "L10000";
        }
        return message;
    },
});
