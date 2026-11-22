# Copyright (C) 2026 NextERP Romania SRL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests import tagged

from .common import TestROStockCommon


@tagged("post_install", "-at_install")
class TestROStockFifoZeroValue(TestROStockCommon):
    """An outgoing move consuming a FIFO layer worth zero (goods received free
    of charge) must be valued at zero, from the stack of its source location."""

    def _receive(self, qty, price, index):
        self.create_purchase(
            {
                "currency_id": self.ron,
                "partner_id": self.supplier_1,
                "product_id": self.product_fifo,
                "qty": qty,
                "stock_qty": qty,
                "inv_qty": qty,
                "price": price,
                "inv_price": price,
                "index": index,
            }
        )

    def _deliver(self, qty, index):
        sale = self.create_sale_order(
            {
                "currency_id": self.ron,
                "partner_id": self.customer_1,
                "product_id": self.product_fifo,
                "qty": qty,
                "stock_qty": qty,
                "inv_qty": qty,
                "price": 150,
                "inv_price": 150,
                "advance": 0,
                "discount": 0,
                "index": index,
            }
        )
        return sale.picking_ids.move_ids.filtered(
            lambda m: m.product_id == self.product_fifo and m.state == "done"
        )

    def test_fifo_out_of_zero_value_layer(self):
        self._receive(10, 100, "zv_po1")
        first_out = self._deliver(10, "zv_so1")
        self.assertAlmostEqual(sum(abs(v) for v in first_out.mapped("value")), 1000)
        self._receive(5, 0, "zv_po2")
        second_out = self._deliver(5, "zv_so2")
        self.assertAlmostEqual(sum(abs(v) for v in second_out.mapped("value")), 0)
