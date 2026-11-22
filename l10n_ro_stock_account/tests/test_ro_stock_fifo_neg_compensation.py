# Copyright (C) 2026 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests import tagged

from .common import TestROStockCommon


@tagged("post_install", "-at_install")
class TestROStockFifoNegCompensation(TestROStockCommon):
    """The negative stock compensation posts on the same accounts as the entry
    of the outgoing move it corrects, not always on the expense account."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.fifo_location_negative_compensation = True
        cls.account_valuation_wh3 = cls.env.company.account_stock_valuation_id.copy(
            {"code": "371003"}
        )
        cls.location2.l10n_ro_property_stock_valuation_account_id = (
            cls.account_valuation_wh3
        )
        cls.product_fifo.standard_price = 80.0

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
        return self.env["stock.move"].search(
            [
                ("product_id", "=", self.product_fifo.id),
                ("is_in", "=", True),
                ("state", "=", "done"),
                ("location_dest_id", "=", location.id),
            ],
            order="id desc",
            limit=1,
        )

    def _transfer(self, location_src, location_dest, qty):
        move = self.env["stock.move"].create(
            {
                "company_id": self.env.company.id,
                "location_id": location_src.id,
                "location_dest_id": location_dest.id,
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

    def test_compensation_of_delivery_on_delivery_accounts(self):
        sale = self.create_sale_order(
            {
                "currency_id": self.ron,
                "partner_id": self.customer_1,
                "product_id": self.product_fifo,
                "qty": 3,
                "stock_qty": 3,
                "inv_qty": 3,
                "price": 150,
                "inv_price": 150,
                "advance": 0,
                "discount": 0,
                "index": "nc_so",
            }
        )
        out_move = sale.picking_ids.move_ids.filtered(
            lambda m: m.product_id == self.product_fifo and m.state == "done"
        )
        self.assertEqual(len(out_move), 1)
        self.assertAlmostEqual(out_move.fifo_neg_pending_qty, 3.0)
        self.assertAlmostEqual(abs(out_move.value), 240.0)
        out_lines = out_move.account_move_id.line_ids
        expense = out_lines.filtered(lambda line: line.debit).account_id
        stock = out_lines.filtered(lambda line: line.credit).account_id

        in_move = self._receive(self.location, 5, 100)

        compensation = in_move.fifo_neg_compensation_move_ids
        self.assertEqual(len(compensation), 1)
        self.assertEqual(compensation.state, "posted")
        lines = compensation.line_ids
        self.assertEqual(lines.account_id, expense | stock)
        self.assertAlmostEqual(
            sum(
                lines.filtered(lambda line: line.account_id == expense).mapped(
                    "balance"
                )
            ),
            60.0,
        )
        self.assertAlmostEqual(
            sum(
                lines.filtered(lambda line: line.account_id == stock).mapped("balance")
            ),
            -60.0,
        )
        self.assertAlmostEqual(abs(out_move.value), 300.0)
        self.assertAlmostEqual(out_move.fifo_neg_pending_qty, 0.0)

    def test_compensation_of_internal_transfer_on_stock_accounts(self):
        """A transfer out of an empty warehouse is corrected between the two
        stock accounts, as its own entry was, not on the expense account."""
        account_src = self.location1.l10n_ro_property_stock_valuation_account_id
        account_dest = self.location2.l10n_ro_property_stock_valuation_account_id
        self.assertTrue(account_src)
        self.assertNotEqual(account_src, account_dest)

        transfer = self._transfer(self.location1, self.location2, 4.0)
        self.assertEqual(transfer.l10n_ro_move_type, "internal_transfer")
        self.assertAlmostEqual(transfer.fifo_neg_pending_qty, 4.0)
        self.assertAlmostEqual(transfer.value, 320.0)

        in_move = self._receive(self.location1, 4, 100)

        compensation = in_move.fifo_neg_compensation_move_ids
        self.assertEqual(len(compensation), 1)
        lines = compensation.line_ids
        expense_accounts = lines.account_id.filtered(
            lambda acc: acc.account_type in ("expense", "expense_direct_cost")
        )
        self.assertFalse(expense_accounts)
        self.assertAlmostEqual(
            sum(
                lines.filtered(lambda line: line.account_id == account_dest).mapped(
                    "balance"
                )
            ),
            80.0,
        )
        self.assertAlmostEqual(
            sum(
                lines.filtered(lambda line: line.account_id == account_src).mapped(
                    "balance"
                )
            ),
            -80.0,
        )
        self.assertAlmostEqual(transfer.value, 400.0)
