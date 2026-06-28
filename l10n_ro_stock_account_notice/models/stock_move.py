# Copyright (C) 2014 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import models

_logger = logging.getLogger(__name__)


# NOTE migrare 18.0 -> 19.0:
# Toata logica de valorizare a avizului (reception_notice /
# delivery_notice si returele lor) era construita in 18.0 peste
# stock.valuation.layer (SVL): _get_valued_types, _create_*_svl,
# _account_entry_move(svl_id), _get_accounting_data_for_valuation,
# l10n_ro_valued_type, _create_dropshipped_svl, _l10n_ro_get_sale_price.
# In Odoo 19 modelul stock.valuation.layer a fost ELIMINAT, iar
# valorizarea traieste direct pe stock.move. Modulul parinte
# l10n_ro_stock_account a internalizat in 19.0 tot fluxul de aviz prin
# campul stocat stock.move.l10n_ro_move_type si metodele
# _get_l10n_ro_move_type_account_list[_extra] (vezi tipurile
# reception_notice / reception_notice_return / delivery_notice /
# delivery_notice_return tratate acolo cu conturile
# l10n_ro_picking_payable / l10n_ro_picking_receivable, inclusiv nota
# suplimentara la pret de vanzare pentru livrarea cu aviz).
# Prin urmare metodele SVL de mai sus nu mai au echivalent in 19 si
# nu mai sunt rescrise aici - functionalitatea este pastrata integral
# in parinte. Vezi tabelul de aliniere din raportul de migrare.


class StockMove(models.Model):
    _name = "stock.move"
    _inherit = ["stock.move", "l10n.ro.mixin"]

    def _get_new_picking_values(self):
        # Setarea implicita a avizului pe transferul nou-creat,
        # in functie de tipul de operatie (camp definit in stock_picking.py).
        vals = super()._get_new_picking_values()
        picking_type = self.mapped("picking_type_id")
        if picking_type.l10n_ro_notice_default:
            vals["l10n_ro_notice"] = True
        return vals
