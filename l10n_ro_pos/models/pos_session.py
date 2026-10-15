# Copyright (C) 2015 Deltatech
# Copyright (C) 2015 Dorin Hongu <dhongu(@)gmail(.)com
# Copyright (C) 2026 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


from odoo import Command, models


class PosSession(models.Model):
    _inherit = "pos.session"

    def _get_l10n_ro_stock_closing_accounts(self, orders):
        """Conturile folosite de pos_stock pentru liniile de stoc din nota de
        inchidere (cheltuiala, mapata prin pozitia fiscala, si valorizarea
        stocului), pentru miscarile valorizate in timp real ale comenzilor."""
        not_linked_to_order = self.picking_ids.filtered(lambda p: not p.pos_order_id)
        linked_to_order = orders.filtered(lambda o: not o.shipping_date).picking_ids
        pickings = not_linked_to_order | linked_to_order
        accounts = self.env["account.account"]
        if not pickings:
            return accounts
        stock_moves = (
            self.env["stock.move"]
            .sudo()
            .search(
                [
                    ("picking_id", "in", pickings.ids),
                    ("product_id.valuation", "=", "real_time"),
                    ("product_id.is_storable", "=", True),
                ]
            )
        )
        for move in stock_moves:
            product_accounts = move.with_company(
                move.company_id
            ).product_id._get_product_accounts()
            expense = product_accounts["expense"]
            pos_order = move.picking_id.pos_order_id
            if pos_order and pos_order.fiscal_position_id:
                expense = pos_order.fiscal_position_id.map_account(expense)
            accounts |= expense | product_accounts["stock_valuation"]
        return accounts

    def _prepare_session_closing_extra_line_commands(
        self, orders, refund, payments=None
    ):
        lines = super()._prepare_session_closing_extra_line_commands(
            orders, refund, payments=payments or []
        )
        if not self.company_id.l10n_ro_accounting or not lines:
            return lines
        # Nu trebuie generate note contabile de stoc (cheltuiala / valorizare)
        # in nota de inchidere a sesiunii: acestea sunt generate in miscarea de
        # stoc. In Odoo 20 liniile sunt adaugate de pos_stock in acest hook
        # (in 19 erau cheile stock_* din _accumulate_amounts).
        stock_accounts = self._get_l10n_ro_stock_closing_accounts(orders)
        if not stock_accounts:
            return lines
        return [
            line
            for line in lines
            if not (
                line[0] == Command.CREATE
                and not line[2].get("display_type")
                and line[2].get("account_id") in stock_accounts.ids
            )
        ]
