# Copyright (C) 2026 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests import tagged

from .common import TestROStockCommon


@tagged("post_install", "-at_install")
class TestROStockFifoProductValue(TestROStockCommon):
    """With FIFO per location, the value of the product is the sum of the
    values of its stock in each location."""

    def _receive(self, location, qty, price):
        self.test_case(
            {
                "steps": [
                    {
                        "type": "purchase",
                        "currency_id": self.env.company.currency_id,
                        "partner_id": self.supplier_1,
                        "product_id": self.product_fifo,
                        "location": location,
                        "step": 1,
                        "qty": qty,
                        "stock_qty": qty,
                        "inv_qty": qty,
                        "price": price,
                        "inv_price": price,
                    }
                ]
            }
        )

    def _deliver(self, location, qty):
        move = self.env["stock.move"].create(
            {
                "company_id": self.env.company.id,
                "location_id": location.id,
                "location_dest_id": self.env.ref("stock.stock_location_customers").id,
                "product_id": self.product_fifo.id,
                "product_uom": self.product_fifo.uom_id.id,
                "product_uom_qty": qty,
            }
        )
        move._action_confirm()
        move._action_assign()
        move._set_quantity_done(qty)
        move.picked = True
        move._action_done()
        return move

    def test_product_value_is_sum_of_locations(self):
        self._receive(self.location1, 10, 10)
        self._receive(self.location2, 10, 20)
        # The later, dearer layer leaves; what is left is the cheaper one.
        self._deliver(self.location2, 10)
        quants = self.env["stock.quant"].search(
            [
                ("product_id", "=", self.product_fifo.id),
                ("location_id.usage", "=", "internal"),
            ]
        )
        self.assertAlmostEqual(sum(quants.mapped("value")), 100.0)
        product = self.product_fifo
        product.invalidate_recordset(["total_value"])
        self.assertAlmostEqual(product.total_value, 100.0)
