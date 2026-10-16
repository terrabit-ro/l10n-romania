# Copyright (C) 2026 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestStatementReport(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.l10n_ro_accounting = True
        cls.journal_cash = cls.company_data["default_journal_cash"]
        cls.report = cls.env.ref(
            "l10n_ro_account_bank_statement_report."
            "action_report_l10n_ro_account_statement"
        )

    def _create_statement(self, date, lines):
        return self.env["account.bank.statement"].create(
            {
                "date": date,
                "journal_id": self.journal_cash.id,
                "company_id": self.env.company.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "date": date,
                            "payment_ref": ref,
                            "amount": amount,
                            "partner_id": self.partner_a.id,
                            "journal_id": self.journal_cash.id,
                        },
                    )
                    for ref, amount in lines
                ],
            }
        )

    def _render(self, statements):
        html, _report_type = self.env["ir.actions.report"]._render_qweb_html(
            self.report.report_name, statements.ids
        )
        return html.decode() if isinstance(html, bytes) else str(html)

    def test_report_daily_single_statement(self):
        statement = self._create_statement(
            "2026-01-05", [("RO-RECEIPT-001", 150.0), ("RO-PAYMENT-001", -40.0)]
        )
        self.assertTrue(statement.is_l10n_ro_record)
        html = self._render(statement)
        self.assertIn("Cash Statement", html)
        self.assertIn("Total Balance", html)
        self.assertIn("Cashier", html)
        self.assertIn("RO-RECEIPT-001", html)
        self.assertIn("RO-PAYMENT-001", html)

    def test_report_period_multiple_statements(self):
        statements = self._create_statement(
            "2026-01-05", [("RO-PERIOD-001", 100.0)]
        ) | self._create_statement("2026-01-06", [("RO-PERIOD-002", -25.0)])
        html = self._render(statements)
        self.assertIn("Total Balance", html)
        self.assertIn("RO-PERIOD-001", html)
        self.assertIn("RO-PERIOD-002", html)

    def test_report_non_romanian_company_uses_standard_report(self):
        self.env.company.l10n_ro_accounting = False
        statement = self._create_statement("2026-01-05", [("STD-LINE-001", 75.0)])
        self.assertFalse(statement.is_l10n_ro_record)
        html = self._render(statement)
        self.assertIn("STD-LINE-001", html)
        self.assertNotIn("Total Balance", html)
