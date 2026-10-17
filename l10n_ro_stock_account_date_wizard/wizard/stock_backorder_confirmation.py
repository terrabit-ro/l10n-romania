# Copyright (C) 2022 NextERP Romania SRL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class StockBackorderConfirmation(models.TransientModel):
    _name = "stock.backorder.confirmation"
    _inherit = ["stock.backorder.confirmation", "l10n.ro.mixin"]

    l10n_ro_accounting_date = fields.Datetime(
        help="If this field is set, the svl and accounting entries will "
        "have this date, If not will have the today date as it should be",
    )

    def _l10n_ro_get_pickings_to_validate(self):
        """The pickings validated by the wizard, as in the stock core: the
        ``button_validate_picking_ids`` from the context, falling back to the
        pickings of the wizard."""
        picking_ids = self.env.context.get("button_validate_picking_ids")
        if picking_ids:
            return self.env["stock.picking"].browse(picking_ids)
        return self.pick_ids

    @api.depends("pick_ids")
    @api.depends_context("company")
    def _compute_is_l10n_ro_record(self):
        for wizard in self:
            pickings = wizard._l10n_ro_get_pickings_to_validate()
            if pickings:
                wizard.is_l10n_ro_record = any(
                    picking.company_id._check_is_l10n_ro_record()
                    for picking in pickings
                )
            else:
                wizard.is_l10n_ro_record = wizard.env.company._check_is_l10n_ro_record()

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        if "l10n_ro_accounting_date" in fields and res.get("pick_ids"):
            pickings = self.env["stock.picking"].browse(res["pick_ids"][0][2])
            ro_pickings = pickings.filtered(
                lambda p: p.company_id._check_is_l10n_ro_record()
            )
            dates = set(ro_pickings.mapped("l10n_ro_accounting_date"))
            # propose the accounting date only when all pickings share it
            if len(dates) == 1:
                res["l10n_ro_accounting_date"] = dates.pop()
        return res

    def _l10n_ro_write_accounting_date(self):
        """Write the accounting date on the Romanian pickings to validate,
        only when the user set one."""
        self.ensure_one()
        if not self.l10n_ro_accounting_date:
            return
        pickings = self._l10n_ro_get_pickings_to_validate().filtered(
            lambda p: p.company_id._check_is_l10n_ro_record()
            and p.l10n_ro_accounting_date != self.l10n_ro_accounting_date
        )
        if pickings:
            pickings.write(
                {
                    "l10n_ro_accounting_date": self.l10n_ro_accounting_date,
                    "date_done": self.l10n_ro_accounting_date,
                }
            )

    def process(self):
        for wizard in self:
            wizard._l10n_ro_write_accounting_date()
        return super().process()

    def process_cancel_backorder(self):
        for wizard in self:
            wizard._l10n_ro_write_accounting_date()
        return super().process_cancel_backorder()
