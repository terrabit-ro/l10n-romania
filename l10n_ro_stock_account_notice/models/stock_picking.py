# Copyright (C) 2014 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class StockPickingType(models.Model):
    _name = "stock.picking.type"
    _inherit = ["stock.picking.type", "l10n.ro.mixin"]

    l10n_ro_notice_default = fields.Boolean(string="Romania - Is a notice")


# NOTE migrare 18.0 -> 19.0:
# Campul stock.picking.l10n_ro_notice era definit aici in 18.0. In 19.0
# el a fost mutat in modulul parinte l10n_ro_stock_account
# (stock_picking.py), care il deine si il foloseste in
# stock_move._get_l10n_ro_move_type. Pentru a nu dubla definiia campului
# nu il mai redeclaram aici. Ramane unic acestui modul doar
# l10n_ro_notice_default de pe stock.picking.type (setarea implicita a
# avizului pe tipul de operatie), consumat in stock_move si purchase_order.
