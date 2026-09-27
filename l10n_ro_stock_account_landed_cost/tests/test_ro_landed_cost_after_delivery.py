# Copyright (C) 2026 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import Command
from odoo.tests import tagged

from odoo.addons.l10n_ro_stock_account.tests.common import TestROStockCommon


@tagged("post_install", "-at_install")
class TestLandedCostAfterDelivery(TestROStockCommon):
    """Landed cost validated after part of the reception was delivered.

    The expected values are the ones produced by 19.0 for the same flow
    (reception 5 x 100 with bill, delivery 2, landed cost 100 split equal):
    the entries must stay the same after the 20.0 migration, where the value
    of the outgoing moves became negative."""

    @TestROStockCommon.setup_country("ro")
    def setUp(cls):
        super().setUp()

    def _receive(self, product, index):
        self.create_purchase(
            {
                "currency_id": self.ron,
                "partner_id": self.supplier_1,
                "product_id": product,
                "qty": 5,
                "stock_qty": 5,
                "inv_qty": 5,
                "price": 100,
                "inv_price": 100,
                "index": index,
            }
        )
        return self.env["purchase.order"].search([], order="id desc", limit=1)

    def _deliver(self, product, qty):
        customer_location = self.env.ref("stock.stock_location_customers")
        picking = self.env["stock.picking"].create(
            {
                "partner_id": self.customer_1.id,
                "picking_type_id": self.location.warehouse_id.out_type_id.id,
                "location_id": self.location.id,
                "location_dest_id": customer_location.id,
                "move_ids": [
                    Command.create(
                        {
                            "product_id": product.id,
                            "product_uom_qty": qty,
                            "uom_id": product.uom_id.id,
                            "location_id": self.location.id,
                            "location_dest_id": customer_location.id,
                        }
                    )
                ],
            }
        )
        picking.action_confirm()
        picking.action_assign()
        picking.move_ids._set_quantity_done(qty)
        picking.move_ids.picked = True
        picking.button_validate()
        return picking

    def _landed_cost(self, product, index, only_on_distributed_lines=False):
        purchase = self._receive(product, index)
        delivery = self._deliver(product, 2)
        journal = self.env["account.journal"].search(
            [("company_id", "=", self.env.company.id), ("type", "=", "general")],
            limit=1,
        )
        landed_cost = self.env["stock.landed.cost"].create(
            {
                "picking_ids": [Command.set(purchase.picking_ids.ids)],
                "account_journal_id": journal.id,
                "cost_lines": [
                    Command.create(
                        {
                            "product_id": self.landed_cost.id,
                            "price_unit": 100,
                            "split_method": "equal",
                            "account_id": self.get_account_by_code("624000").id,
                        }
                    )
                ],
            }
        )
        if only_on_distributed_lines:
            landed_cost.l10n_ro_only_on_distributed_lines = True
        landed_cost.compute_landed_cost()
        landed_cost.button_validate()
        return landed_cost, purchase.picking_ids.move_ids, delivery.move_ids

    def _balances(self):
        amls = self.env["account.move.line"].search(
            [("company_id", "=", self.env.company.id), ("parent_state", "=", "posted")]
        )
        balances = {}
        for aml in amls:
            code = aml.account_id.code
            balances[code] = round(balances.get(code, 0) + aml.balance, 2)
        return {code: value for code, value in balances.items() if value}

    def _quant_value(self, product):
        quants = self.env["stock.quant"].search(
            [("product_id", "=", product.id), ("location_id.usage", "=", "internal")]
        )
        return sum(quants.mapped("value"))

    def test_fifo_landed_cost_after_delivery(self):
        landed_cost, in_move, out_move = self._landed_cost(self.product_fifo, "lc_fifo")
        # the delivered share (2 x 20) is distributed on the delivery
        self.assertRecordValues(
            landed_cost.l10n_ro_distributed_valuation_lines,
            [{"move_id": out_move.id, "quantity": 2.0, "additional_landed_cost": 40}],
        )
        # Dr 371 / Cr 624 on the whole landed cost, then the delivered
        # share discharged Dr 607 / Cr 371
        acc_371 = self.get_account_by_code("371000").id
        acc_607 = self.get_account_by_code("607000").id
        acc_624 = self.get_account_by_code("624000").id
        self.assertRecordValues(
            landed_cost.account_move_id.line_ids.sorted(
                lambda aml: (aml.debit, aml.credit)
            ),
            [
                {"account_id": acc_371, "debit": 0, "credit": 40},
                {"account_id": acc_624, "debit": 0, "credit": 100},
                {"account_id": acc_607, "debit": 40, "credit": 0},
                {"account_id": acc_371, "debit": 100, "credit": 0},
            ],
        )
        self.assertEqual(
            self._balances(),
            {
                "371000": 360.0,
                "401100": -605.0,
                "442600": 105.0,
                "607000": 240.0,
                "624000": -100.0,
            },
        )
        self.assertAlmostEqual(in_move.value, 600)
        # 20.0: the value of the outgoing move is negative
        self.assertAlmostEqual(out_move.value, -240)
        self.assertAlmostEqual(self._quant_value(self.product_fifo), 360)

    def test_avg_landed_cost_after_delivery(self):
        landed_cost, in_move, out_move = self._landed_cost(self.product_avg, "lc_avg")
        self.assertFalse(landed_cost.l10n_ro_distributed_valuation_lines)
        self.assertEqual(
            self._balances(),
            {
                "371000": 400.0,
                "401100": -605.0,
                "442600": 105.0,
                "607000": 200.0,
                "624000": -100.0,
            },
        )
        self.assertAlmostEqual(in_move.value, 600)
        self.assertAlmostEqual(out_move.value, -200)
        self.assertAlmostEqual(self._quant_value(self.product_avg), 360)

    def test_fifo_only_on_distributed_lines(self):
        landed_cost, in_move, out_move = self._landed_cost(
            self.product_fifo, "lc_fifo_dist", only_on_distributed_lines=True
        )
        self.assertRecordValues(
            landed_cost.valuation_adjustment_lines,
            [{"additional_landed_cost": 0, "l10n_ro_not_distributed_amount": 100}],
        )
        self.assertRecordValues(
            landed_cost.l10n_ro_distributed_valuation_lines,
            [{"move_id": out_move.id, "quantity": 2.0, "additional_landed_cost": 40}],
        )
        self.assertEqual(
            self._balances(),
            {
                "371000": 260.0,
                "401100": -605.0,
                "442600": 105.0,
                "607000": 240.0,
            },
        )
        self.assertAlmostEqual(in_move.value, 500)
        self.assertAlmostEqual(out_move.value, -240)
        self.assertAlmostEqual(self._quant_value(self.product_fifo), 300)
