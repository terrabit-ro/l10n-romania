# Copyright (C) 2022 NextERP Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

# NOTE migrare 18.0 -> 19.0:
# In 18.0 acest model rescria account.move.line._compute_account_id ca,
# la factura furnizor/client legata de un aviz (picking.l10n_ro_notice),
# sa puna contul 408 / 418
# (l10n_ro_property_stock_picking_payable_account_id /
# ..._receivable_account_id). De asemenea oferea
# _get_account_change_stock_moves_purchase / _sale folosite de
# l10n_ro_stock_account.account_move din 18 pentru re-clasarea 408 -> 401.
#
# In Odoo 19 ambele mecanisme sunt deja in modulul parinte
# l10n_ro_stock_account: _compute_account_id + _get_l10n_ro_line_account
# trateaza explicit tipurile reception_notice(_return) ->
# l10n_ro_picking_payable si delivery_notice(_return) ->
# l10n_ro_picking_receivable, citind stock_move.l10n_ro_move_type.
# Logica de re-clasare a fost rescrisa in parinte fara
# _get_account_change_stock_moves_*, deci aceste override-uri nu mai au
# consumator.
#
# Functionalitatea 408/418 pe factura este pastrata integral in parinte.
