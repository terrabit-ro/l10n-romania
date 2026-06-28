# Copyright (C) 2014 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

# NOTE migrare 18.0 -> 19.0:
# In 18.0 acest model rescria product.template._get_product_accounts si,
# in functie de context["valued_type"] (mecanism SVL eliminat in 19),
# substituia conturile de stoc/cheltuiala/venit cu 408 / 418
# (l10n_ro_property_stock_picking_payable_account_id /
# l10n_ro_property_stock_picking_receivable_account_id) pentru avize.
#
# In Odoo 19 stock.valuation.layer a fost eliminat si determinarea
# conturilor s-a mutat in modulul parinte l10n_ro_stock_account, in
# product_template.get_product_accounts(), care expune deja cheile
# "l10n_ro_picking_payable" / "l10n_ro_picking_receivable" pe baza
# acelorasi campuri de companie. Consumarea lor pentru avize se face in
# stock_move._get_l10n_ro_move_type_account_list[_extra] si in
# account_move_line._get_l10n_ro_line_account din parinte.
#
# Asadar override-ul de aici nu mai are echivalent (context valued_type
# nu mai exista) si functionalitatea este pastrata integral in parinte.
# Fisierul ramane pentru trasabilitate; nu mai inregistreaza model.
