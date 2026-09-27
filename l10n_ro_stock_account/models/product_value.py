# Copyright (C) 2026 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, models


class ProductValue(models.Model):
    _inherit = "product.value"

    @api.model_create_multi
    def create(self, vals_list):
        """20.0 revalues the moves of the FIFO stack when a product (or lot)
        cost is updated (`product.value` without move). Up to 19.0 a cost
        update left the value of the done moves alone - the Romanian entries
        are posted from them - and only refreshed the lot valuated products
        cost. Keep that for the Romanian moves (see `stock.move._set_value`).
        """
        if all(vals.get("move_id") for vals in vals_list):
            return super().create(vals_list)
        move_vals = [vals for vals in vals_list if vals.get("move_id")]
        cost_vals = [vals for vals in vals_list if not vals.get("move_id")]
        cost_records = iter(
            super(ProductValue, self.with_context(l10n_ro_skip_revaluation=True))
            .create(cost_vals)
            .with_env(self.env)
        )
        move_records = iter(super().create(move_vals) if move_vals else [])
        records = self.browse(
            next(move_records if vals.get("move_id") else cost_records).id
            for vals in vals_list
        )
        lot_products = records.filtered(
            lambda pv: not pv.move_id and pv.lot_id and pv.product_id.is_l10n_ro_record
        ).product_id
        if lot_products:
            lot_products._update_standard_price()
        return records
