from odoo import models


class ProductProduct(models.Model):
    _inherit = "product.product"

    def _import_retrieve_product_from_vendor_code(self, product_values):
        vendor_code = product_values.get("l10n_ro_vendor_code")
        if not vendor_code:
            return
        # Odoo 20: UBL import no longer passes ``invoice_predictive`` in the
        # product values; the vendor comes as ``vendor_partner_id`` (the
        # commercial partner of the counterpart).
        partner_id = product_values.get("vendor_partner_id")
        if not partner_id:
            invoice = (product_values.get("invoice_predictive") or {}).get("invoice")
            partner_id = invoice.commercial_partner_id.id if invoice else None
        if partner_id:
            return {
                "criteria": [
                    {
                        "domain": [
                            ("seller_ids.product_code", "=", vendor_code),
                            ("seller_ids.partner_id", "child_of", partner_id),
                        ]
                    },
                    # Fallback: search only by vendor code if partner doesn't match
                    {"domain": [("seller_ids.product_code", "=", vendor_code)]},
                ]
            }
        return {
            "criteria": [{"domain": [("seller_ids.product_code", "=", vendor_code)]}]
        }

    def _get_retrieval_product_search_plan(self):
        # Insert vendor code search with highest priority
        # (lowest number = highest priority)
        return [
            (1, self._import_retrieve_product_from_vendor_code)
        ] + super()._get_retrieval_product_search_plan()
