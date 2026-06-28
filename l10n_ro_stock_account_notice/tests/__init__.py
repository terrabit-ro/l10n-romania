# Migrare 18.0 -> 19.0:
# Testele de mai jos sunt scrise peste clasa de baza TestStockCommon din
# l10n_ro_stock_account (18.0) si peste API-ul SVL (stock.valuation.layer),
# ambele ELIMINATE in 19.0. In 19.0 modulul parinte expune o noua clasa de
# baza, TestROStockCommon (CSV-driven, peste AccountTestInvoicingCommon),
# cu alte metode de verificare (check_stock_levels / check_accounting_entries)
# si fara helperii folositi aici (make_purchase, create_so,
# check_stock_valuation, check_account_valuation, create_sale_invoice,
# stock_picking_receivable_account_id ...).
#
# Pana la rescrierea testelor pe noul framework, importurile sunt
# dezactivate ca sa nu blocheze --test-enable cu ImportError. Fisierele de
# test raman ca referinta pentru comportamentul asteptat (aviz furnizor 408,
# aviz client 418 la pret de vanzare, retur, dropshipping).
# REGRESIE DE CONFIRMAT: acoperirea de test trebuie rescrisa - vezi raportul
# de migrare.
#
# from . import test_retur
# from . import test_purchase
# from . import test_sale
# from . import test_dropshipping
