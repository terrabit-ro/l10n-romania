# Copyright (C) 2020 Terrabit
# Copyright (C) 2025 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo.tests import tagged

from .common import TestROStockCommon

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestFIFOInternalTransfer(TestROStockCommon):
    def test_fifo_internal_transfer_sublocation(self):
        putaway = self.env["stock.putaway.rule"].create(
            {
                "product_id": self.product_fifo.id,
                "location_in_id": self.location.id,
                "location_out_id": self.location_sub_1.id,
            }
        )
        self.location.write(
            {
                "putaway_rule_ids": [(4, putaway.id, 0)],
            }
        )
        case = {
            "name": "transfer intern direct sublocatie",
            "code": "1",
            "steps": [
                {
                    "case_no": "1",
                    "type": "purchase",
                    "currency_id": self.env.company.currency_id,
                    "partner_id": self.supplier_1,
                    "product_id": self.product_fifo,
                    "step": 1,
                    "qty": 10.0,
                    "stock_qty": 10.0,
                    "inv_qty": 10.0,
                    "price": 100.0,
                    "inv_price": 100.0,
                    "checks": {
                        "stock": {
                            "product_fifo": [
                                {"location": "location_sub_1", "qty": 10, "value": 1000}
                            ]
                        },
                        "account": {"371000": 1000},
                    },
                    "name": "transfer intern direct sublocatie",
                },
                {
                    "case_no": "1",
                    "type": "transfer_direct",
                    "currency_id": self.env.company.currency_id,
                    "location": self.location_sub_1,
                    "location1": self.location_sub_2,
                    "product_id": self.product_fifo,
                    "step": 1,
                    "qty": 6.0,
                    "stock_qty": 6.0,
                    "checks": {
                        "stock": {
                            "product_fifo": [
                                {"location": "location_sub_1", "qty": 4, "value": 400},
                                {"location": "location_sub_2", "qty": 6, "value": 600},
                            ]
                        },
                        "account": {"371000": 1000},
                    },
                    "name": "transfer intern direct sublocatie",
                },
            ],
        }
        self.test_case(case)

    def test_fifo_internal_transfer_no_account_change(self):
        """An internal transfer must not post on the expense account when the
        category does not change accounts per location.

        With ``l10n_ro_stock_account_change`` unset the expense account used to
        stay 607, so each valued transfer posted Dr 482 / Cr 371 and
        Dr 607 / Cr 482 - net Dr 607 / Cr 371 - and the stock account drifted
        away from the stock valuation.
        """
        self.category_marfa_fifo.l10n_ro_stock_account_change = False
        expense_account = self.product_fifo.product_tmpl_id._get_product_accounts()[
            "expense"
        ]
        stock_account = self.category_marfa_fifo.property_stock_valuation_account_id
        self.assertNotEqual(expense_account, stock_account)
        putaway = self.env["stock.putaway.rule"].create(
            {
                "product_id": self.product_fifo.id,
                "location_in_id": self.location.id,
                "location_out_id": self.location_sub_1.id,
            }
        )
        self.location.write({"putaway_rule_ids": [(4, putaway.id, 0)]})
        case = {
            "name": "transfer intern fara schimbare cont",
            "code": "1",
            "steps": [
                {
                    "case_no": "1",
                    "type": "purchase",
                    "currency_id": self.env.company.currency_id,
                    "partner_id": self.supplier_1,
                    "product_id": self.product_fifo,
                    "step": 1,
                    "qty": 10.0,
                    "stock_qty": 10.0,
                    "inv_qty": 10.0,
                    "price": 100.0,
                    "inv_price": 100.0,
                    "checks": {"account": {"371000": 1000}},
                    "name": "transfer intern fara schimbare cont",
                },
                {
                    "case_no": "1",
                    "type": "transfer_direct",
                    "currency_id": self.env.company.currency_id,
                    "location": self.location_sub_1,
                    "location1": self.location_sub_2,
                    "product_id": self.product_fifo,
                    "step": 1,
                    "qty": 6.0,
                    "stock_qty": 6.0,
                    "checks": {
                        "stock": {
                            "product_fifo": [
                                {"location": "location_sub_1", "qty": 4, "value": 400},
                                {"location": "location_sub_2", "qty": 6, "value": 600},
                            ]
                        },
                        "account": {"371000": 1000},
                    },
                    "name": "transfer intern fara schimbare cont",
                },
            ],
        }
        self.test_case(case)
        expense_lines = self.env["account.move.line"].search(
            [
                ("account_id", "=", expense_account.id),
                ("company_id", "=", self.env.company.id),
                ("parent_state", "=", "posted"),
            ]
        )
        self.assertFalse(expense_lines)
