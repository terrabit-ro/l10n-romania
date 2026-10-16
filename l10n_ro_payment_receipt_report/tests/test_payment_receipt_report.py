# Copyright (C) 2026 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestPaymentReceiptReport(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.l10n_ro_accounting = True
        cls.partner_a.function = "Cashier assistant"
        cls.journal_cash = cls.company_data["default_journal_cash"]

    def _render(self, report_name, records):
        html, _report_type = self.env["ir.actions.report"]._render_qweb_html(
            report_name, records.ids
        )
        return html.decode() if isinstance(html, bytes) else str(html)

    def _create_payment(self, amount=250.0):
        payment = self.env["account.payment"].create(
            {
                "payment_type": "inbound",
                "partner_type": "customer",
                "partner_id": self.partner_a.id,
                "amount": amount,
                "journal_id": self.company_data["default_journal_bank"].id,
                "memo": "RO-RECEIPT-MEMO",
            }
        )
        payment.action_post()
        return payment

    def _create_statement_line(self, amount, ref):
        return self.env["account.bank.statement.line"].create(
            {
                "journal_id": self.journal_cash.id,
                "date": "2026-01-05",
                "payment_ref": ref,
                "amount": amount,
                "partner_id": self.partner_a.id,
            }
        )

    def test_payment_receipt_romanian_layout(self):
        payment = self._create_payment()
        self.assertTrue(payment.is_l10n_ro_record)
        html = self._render(
            "l10n_ro_payment_receipt_report.report_payment_receipt", payment
        )
        self.assertIn("We received from", html)
        self.assertIn(self.partner_a.name, html)
        self.assertIn("Signature and stamp", html)

    def test_payment_receipt_non_romanian_uses_standard(self):
        self.env.company.l10n_ro_accounting = False
        payment = self._create_payment()
        self.assertFalse(payment.is_l10n_ro_record)
        html = self._render(
            "l10n_ro_payment_receipt_report.report_payment_receipt", payment
        )
        self.assertNotIn("We received from", html)
        self.assertIn(payment.name, html)

    def test_statement_line_reception_and_disposal(self):
        reception = self._create_statement_line(120.0, "RO-CASH-IN")
        disposal = self._create_statement_line(-80.0, "RO-CASH-OUT")
        report_name = (
            "l10n_ro_payment_receipt_report.report_bank_statement_line_payment_template"
        )
        html = self._render(report_name, reception)
        self.assertIn("Payment Reception", html)
        self.assertIn("RO-CASH-IN", html)
        self.assertIn("Cashier assistant", html)
        html = self._render(report_name, disposal)
        self.assertIn("Payment Disposal", html)
        self.assertIn("RO-CASH-OUT", html)
