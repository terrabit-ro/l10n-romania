This module adds a stock report according to Romanian requirements (the storage
sheet, *Fișa de magazie*).

**Not needed when `l10n_ro_stock_sheet` is used.** The report is built on the
fields added by `l10n_ro_stock_account` (`l10n_ro_move_type`,
`l10n_ro_account_id`, `l10n_ro_transfer_account_id`), so it works only together
with that module. On a database that determines the stock accounts through OBYC
(`deltatech_obyc`) instead of `l10n_ro_stock_account`, or that uses the storage
sheet (14-3-8) and the analytical stock balance of `l10n_ro_stock_sheet`
(`l10n_ro_ent`, native Odoo 19 valuation, no OCA dependency), this module is not
needed and should not be installed.

Differences to know before replacing it:

* `l10n_ro_stock_sheet` does not split the report by movement type (receipt,
  delivery, inventory plus/minus, consumption, transfer, ...); it groups by
  stock account, product and document.
* it has no filter by valuation area (by location only).
* for stock moves without an accounting entry (for example moves migrated from a
  previous version) the account is the one of the product category.
