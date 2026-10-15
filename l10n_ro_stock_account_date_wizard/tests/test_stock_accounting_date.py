# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging
from datetime import timedelta

from lxml import etree

from odoo import fields
from odoo.tests import Form, tagged

from odoo.addons.l10n_ro_stock_account_date.tests.test_stock_accounting_date import (
    TestStockAccountDate,
)

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestStockAccountDateWizard(TestStockAccountDate):
    @TestStockAccountDate.setup_country("ro")
    def setUp(cls):
        super().setUp()

    def make_transfer(self, qty_done=2):
        int_picking_type = self.location.warehouse_id.int_type_id
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": int_picking_type.id,
                "location_id": self.location.id,
                "location_dest_id": self.location1.id,
                "move_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product_fifo.id,
                            "product_uom_qty": 5,
                            "uom_id": self.product_fifo.uom_id.id,
                            "location_id": self.location.id,
                            "location_dest_id": self.location1.id,
                        },
                    )
                ],
            }
        )
        picking.action_confirm()
        picking.action_assign()
        picking.move_ids._set_quantity_done(qty_done)
        return picking

    def _get_backorder_wizard(self, pickings):
        action_data = pickings.button_validate()
        return Form(
            pickings.env["stock.backorder.confirmation"].with_context(
                **action_data.get("context", {})
            )
        )

    def test_transfer_backorder(self):
        self.make_purchase()
        picking = self.make_transfer()
        acc_date = fields.Date.today() - timedelta(days=1)

        action_data = picking.button_validate()
        backorder_wizard = Form(
            self.env["stock.backorder.confirmation"].with_context(
                **action_data.get("context", {})
            )
        ).save()
        backorder_wizard.l10n_ro_accounting_date = acc_date
        backorder_wizard.process()
        stock_move = picking.move_ids
        self.assertEqual(picking.l10n_ro_accounting_date.date(), acc_date)
        self.assertEqual(stock_move.date.date(), acc_date)
        self.assertEqual(
            any(
                move_line.date.date() == acc_date
                for move_line in stock_move.move_line_ids
            ),
            True,
        )
        self.assertTrue(stock_move.account_move_id)
        self.assertEqual(stock_move.account_move_id.date, acc_date)

    def test_transfer_cancel_backorder(self):
        self.make_purchase()
        picking = self.make_transfer()
        acc_date = fields.Date.today() - timedelta(days=1)

        action_data = picking.button_validate()
        backorder_wizard = Form(
            self.env["stock.backorder.confirmation"].with_context(
                **action_data.get("context", {})
            )
        ).save()
        backorder_wizard.l10n_ro_accounting_date = acc_date
        backorder_wizard.process_cancel_backorder()
        stock_move = picking.move_ids.filtered(lambda m: m.state == "done")
        self.assertEqual(picking.l10n_ro_accounting_date.date(), acc_date)
        self.assertEqual(stock_move.date.date(), acc_date)
        self.assertEqual(
            any(
                move_line.date.date() == acc_date
                for move_line in stock_move.move_line_ids
            ),
            True,
        )
        self.assertTrue(stock_move.account_move_id)
        self.assertEqual(stock_move.account_move_id.date, acc_date)

    def test_untouched_date_not_written(self):
        """The wizard must not stamp the current date on the pickings when the
        user does not set an accounting date."""
        self.make_purchase()
        picking = self.make_transfer()
        wizard = self._get_backorder_wizard(picking).save()
        self.assertFalse(wizard.l10n_ro_accounting_date)
        wizard.process()
        self.assertEqual(picking.state, "done")
        self.assertFalse(picking.l10n_ro_accounting_date)

    def test_cleared_date_keeps_picking_date(self):
        """Clearing the proposed date must not erase the picking date."""
        self.make_purchase()
        picking = self.make_transfer()
        acc_date = fields.Datetime.now().replace(microsecond=0) - timedelta(days=1)
        picking.l10n_ro_accounting_date = acc_date
        wizard_form = self._get_backorder_wizard(picking)
        self.assertEqual(wizard_form.l10n_ro_accounting_date, acc_date)
        wizard_form.l10n_ro_accounting_date = False
        wizard_form.save().process()
        self.assertEqual(picking.l10n_ro_accounting_date, acc_date)
        self.assertEqual(picking.move_ids.account_move_id.date, acc_date.date())

    def test_default_date_multiple_pickings(self):
        """The date is proposed only when all pickings share it."""
        self.make_purchase()
        picking1 = self.make_transfer()
        picking2 = self.make_transfer()
        acc_date = fields.Datetime.now().replace(microsecond=0) - timedelta(days=1)
        (picking1 | picking2).l10n_ro_accounting_date = acc_date
        wizard_form = self._get_backorder_wizard(picking1 | picking2)
        self.assertEqual(wizard_form.l10n_ro_accounting_date, acc_date)

        picking1.l10n_ro_accounting_date = False
        wizard_form = self._get_backorder_wizard(picking1 | picking2)
        self.assertFalse(wizard_form.l10n_ro_accounting_date)

        picking1.l10n_ro_accounting_date = acc_date - timedelta(days=1)
        wizard_form = self._get_backorder_wizard(picking1 | picking2)
        self.assertFalse(wizard_form.l10n_ro_accounting_date)

    def _check_date_on_all_validated_pickings(self, method):
        self.make_purchase()
        partial = self.make_transfer()
        full = self.make_transfer(qty_done=5)
        acc_date = fields.Date.today() - timedelta(days=1)
        wizard_form = self._get_backorder_wizard(partial | full)
        wizard_form.l10n_ro_accounting_date = acc_date
        wizard = wizard_form.save()
        self.assertEqual(wizard.pick_ids, partial)
        getattr(wizard, method)()
        for picking in partial | full:
            self.assertEqual(picking.state, "done")
            self.assertEqual(picking.l10n_ro_accounting_date.date(), acc_date)
            done_moves = picking.move_ids.filtered(lambda m: m.state == "done")
            self.assertEqual(done_moves.account_move_id.date, acc_date)

    def test_process_date_on_all_validated_pickings(self):
        self._check_date_on_all_validated_pickings("process")

    def test_cancel_backorder_date_on_all_validated_pickings(self):
        self._check_date_on_all_validated_pickings("process_cancel_backorder")

    def test_non_ro_picking(self):
        """The accounting date is hidden and not written for a picking of a
        non-Romanian company, even when the current company is Romanian."""
        ro_company = self.env.company
        company = self.env["res.company"].create(
            {"name": "Non RO Company", "country_id": self.env.ref("base.us").id}
        )
        self.env.user.company_ids |= company
        self.assertFalse(company._check_is_l10n_ro_record())
        env = self.env(
            context=dict(
                self.env.context, allowed_company_ids=[ro_company.id, company.id]
            )
        )
        self.assertEqual(env.company, ro_company)
        warehouse = env["stock.warehouse"].search(
            [("company_id", "=", company.id)], limit=1
        )
        product = env["product.product"].create(
            {"name": "Non RO product", "is_storable": True}
        )
        env["stock.quant"]._update_available_quantity(
            product, warehouse.lot_stock_id, 10
        )
        picking = env["stock.picking"].create(
            {
                "picking_type_id": warehouse.out_type_id.id,
                "location_id": warehouse.lot_stock_id.id,
                "location_dest_id": self.env.ref("stock.stock_location_customers").id,
                "company_id": company.id,
                "move_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": product.id,
                            "product_uom_qty": 5,
                            "location_id": warehouse.lot_stock_id.id,
                            "location_dest_id": self.env.ref(
                                "stock.stock_location_customers"
                            ).id,
                            "company_id": company.id,
                        },
                    )
                ],
            }
        )
        picking.action_confirm()
        picking.action_assign()
        picking.move_ids._set_quantity_done(2)

        wizard = self._get_backorder_wizard(picking).save()
        wizard.l10n_ro_accounting_date = fields.Date.today() - timedelta(days=1)
        wizard.process()
        self.assertEqual(picking.state, "done")
        self.assertFalse(picking.l10n_ro_accounting_date)
        self.assertFalse(wizard.is_l10n_ro_record)

        arch = env["stock.backorder.confirmation"].get_view(
            env.ref("stock.view_backorder_confirmation").id, "form"
        )["arch"]
        field = etree.fromstring(arch).xpath(
            "//field[@name='l10n_ro_accounting_date']"
        )[0]
        self.assertEqual(field.get("invisible"), "not is_l10n_ro_record")
