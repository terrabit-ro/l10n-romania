# Copyright (C) 2026 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, models

VALUATION_FIELDS = [
    "quantity",
    "location_id",
    "location_dest_id",
    "owner_id",
    "quant_id",
    "lot_id",
]


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    # 20.0: adding or editing the lines of a done move replays the valuation
    # from the move date (`stock.move._set_value(recompute_date=...)`), which
    # rewrites the value of every later outgoing move. Up to 19.0 only the
    # edited move was revalued: an incoming move from its documents, an
    # outgoing move pro rata to the quantity correction. The Romanian entries
    # are posted from those values, so the 19.0 behaviour is kept for the
    # Romanian moves (`l10n_ro_defer_ml_valuation` makes `_set_value` skip
    # them, see `stock.move._set_value`).

    @api.model_create_multi
    def create(self, vals_list):
        mls = super(
            StockMoveLine, self.with_context(l10n_ro_defer_ml_valuation=True)
        ).create(vals_list)
        mls = mls.with_env(self.env)
        mls._l10n_ro_update_stock_move_value()
        return mls

    def write(self, vals):
        if not any(field in vals for field in VALUATION_FIELDS):
            return super().write(vals)
        old_qty_by_ml = {
            ml: ml.quantity
            for ml in self
            if ml.move_id.is_l10n_ro_record and (ml.move_id.is_in or ml.move_id.is_out)
        }
        res = super(
            StockMoveLine, self.with_context(l10n_ro_defer_ml_valuation=True)
        ).write(vals)
        if old_qty_by_ml:
            self.env["stock.move.line"].concat(
                *old_qty_by_ml
            )._l10n_ro_update_stock_move_value(old_qty_by_ml)
        return res

    def _l10n_ro_update_stock_move_value(self, old_qty_by_ml=None):
        """19.0 `stock.move.line._update_stock_move_value`, for Romanian moves."""
        old_qty_by_ml = old_qty_by_ml or {}
        moves_in = self.env["stock.move"]
        for move, mls in self.grouped("move_id").items():
            if not move.is_l10n_ro_record or not (move.is_in or move.is_out):
                continue
            if move.is_in:
                moves_in |= move
                continue
            delta = sum(
                ml.quantity - old_qty_by_ml.get(ml, 0)
                for ml in mls
                if not ml._should_exclude_for_valuation()
            )
            if delta:
                move._l10n_ro_correct_out_value(delta)
        if moves_in:
            moves_in._set_value()
