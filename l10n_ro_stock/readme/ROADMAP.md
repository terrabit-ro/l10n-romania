## Retire `l10n_ro_net_weight`

The field duplicates the Odoo model: `product.weight` is the weight of the product (net) and the gross
weight is net + packaging (`stock.package.shipping_weight`). Nothing in Odoo Community/Enterprise
(including `l10n_ro_edi_stock`, which declares `product.weight` as net weight) reads the field.

1. Before removing it, make sure no module in the customer's database reads it
   (`deltatech_invoice_weight`, `deltatech_cmr_document`, `l10n_ro_hide_net_weight` are being cleaned up).
2. Remove `l10n_ro_net_weight`, `l10n_ro_net_weight_uom_name`, the computes/inverse on
   `product.template` and the field on `product.product` (`models/product_template.py`), the product
   form view `views/product_template_view.xml` and the assertions in `tests/test_stock_warehouse_creation.py`.
3. Migration: if values differ from `weight` on a database, decide per customer (move the difference to
   the package type `base_weight`, or keep the column with an `openupgrade.drop_columns` only after
   confirmation); the field is not part of any declaration sent to ANAF.
4. Remove `l10n_ro_hide_net_weight` once the field is gone.
