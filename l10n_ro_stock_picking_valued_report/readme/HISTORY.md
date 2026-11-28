## 20.0.0.1.0

- Migration to 20.0: the valued delivery slip uses `t-out` (server-side `t-esc` is ignored in 20) and the 20.0 keys of the aggregated lines (`qty_ordered`, `uom_id`).
- `_get_aggregated_product_quantities` skips the move lines left out by the standard aggregation (e.g. `except_package`) instead of raising a `KeyError`.
