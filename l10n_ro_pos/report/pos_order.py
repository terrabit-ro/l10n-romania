# ©  2015-2021 Deltatech
#              Dorin Hongu <dhongu(@)gmail(.)com
# See README.rst file on addons root folder for license details

from odoo import api, models
from odoo.fields import Domain


class ReportSaleDetails(models.AbstractModel):
    _inherit = "report.point_of_sale.report_saledetails"

    @api.model
    def get_sale_details(
        self,
        date_start=False,
        date_stop=False,
        config_ids=False,
        session_ids=False,
        **kwargs,
    ):
        res = super().get_sale_details(
            date_start, date_stop, config_ids, session_ids, **kwargs
        )

        # Acelasi domeniu de comenzi ca raportul standard (Odoo 20 expune
        # _get_domain, inclusiv intervalul implicit in fusul orar al
        # utilizatorului); comenzile anulate nu intra in raport.
        domain = self._get_domain(
            date_start, date_stop, config_ids, session_ids, **kwargs
        ) & Domain("state", "!=", "cancel")

        # Valoarea de stoc are sens doar cu valorizarea (stock_account) instalata;
        # campul `value` pe stock.move vine de acolo. Daca lipseste, raportul ramane
        # functional (coloanele afiseaza 0).
        if "value" not in self.env["stock.move"]._fields:
            res["total_stock_amount"] = 0.0
            return res

        orders = self.env["pos.order"].search(domain)

        # In O19 SVL a fost eliminat; valorizarea e pe stock.move (value / quantity).
        # Miscari valorizate = is_in/is_out (transferul intern nu e valorizat nativ).
        # Acumulam valoare/cantitate per produs pentru un cost mediu unitar.
        products_stock = {}
        products_stock_qty = {}

        for order in orders:
            for picking in order.picking_ids:
                for move in picking.move_ids:
                    if not (move.is_in or move.is_out):
                        continue
                    products_stock.setdefault(move.product_id.id, 0.0)
                    products_stock_qty.setdefault(move.product_id.id, 0.0)
                    products_stock[move.product_id.id] += abs(move.value)
                    products_stock_qty[move.product_id.id] += abs(move.quantity)

        def _stock_price(product_id):
            if product_id in products_stock and products_stock_qty.get(product_id):
                return products_stock[product_id] / products_stock_qty[product_id]
            return 0.0

        # In Odoo 19 res["products"] / res["refund_products"] sunt liste de categorii,
        # fiecare cu lista ei de produse. Injectam costul pe fiecare linie.
        total_stock_amount = 0.0
        for category in res.get("products", []):
            for line in category.get("products", []):
                stock_price = _stock_price(line.get("product_id"))
                line["stock_price"] = stock_price
                line["stock_amount"] = stock_price * line.get("quantity", 0.0)
                total_stock_amount += line["stock_amount"]

        for category in res.get("refund_products", []):
            for line in category.get("products", []):
                stock_price = _stock_price(line.get("product_id"))
                line["stock_price"] = stock_price
                line["stock_amount"] = stock_price * line.get("quantity", 0.0)

        res["total_stock_amount"] = total_stock_amount
        return res
