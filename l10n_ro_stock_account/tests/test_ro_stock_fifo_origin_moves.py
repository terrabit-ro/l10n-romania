# Copyright (C) 2026 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests import tagged

from .common import TestROStockCommon


@tagged("post_install", "-at_install")
class TestROStockFifoOriginMoves(TestROStockCommon):
    """A FIFO move valued from its origin moves takes the unit value over all
    of them, not only the first one."""

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
        return self.env["stock.move"].search(
            [
                ("product_id", "=", self.product_fifo.id),
                ("is_in", "=", True),
                ("state", "=", "done"),
            ],
            order="id desc",
            limit=1,
        )

    def test_value_from_several_origin_moves(self):
        origin_1 = self._receive(5, 10, "om_po1")
        origin_2 = self._receive(5, 20, "om_po2")
        self.assertAlmostEqual(origin_1.value, 50.0)
        self.assertAlmostEqual(origin_2.value, 100.0)
        move = self.env["stock.move"].create(
            {
                "company_id": self.env.company.id,
                "location_id": self.location.id,
                "location_dest_id": self.location1.id,
                "product_id": self.product_fifo.id,
                "product_uom": self.product_fifo.uom_id.id,
                "product_uom_qty": 10,
                "move_orig_ids": [(6, 0, (origin_1 | origin_2).ids)],
            }
        )
        data = move._get_value_from_origin_move(10)
        self.assertAlmostEqual(data["value"], 150.0)
        self.assertAlmostEqual(data["quantity"], 10.0)
        self.assertIn(origin_1.reference, data["description"])
        self.assertIn(origin_2.reference, data["description"])
