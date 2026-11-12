# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import importlib.util
from pathlib import Path

from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestPartnerCompanyRegistry(AccountTestInvoicingCommon):
    @classmethod
    @AccountTestInvoicingCommon.setup_country("ro")
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.l10n_ro_accounting = True
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Test RO SRL",
                "is_company": True,
                "country_id": cls.env.ref("base.ro").id,
                "vat": "RO18547290",
                "nrc": "J2010000026229",
            }
        )

    def test_company_registry_is_cui_not_nrc(self):
        """company_registry keeps the CUI, the J number stays in nrc."""
        self.assertEqual(self.partner.company_registry, "18547290")
        self.assertEqual(self.partner.nrc, "J2010000026229")
        self.partner.nrc = "J2011000000001"
        self.assertEqual(self.partner.company_registry, "18547290")

    def test_migration_restores_cui(self):
        """The migration undoes the old nrc -> company_registry copy."""
        self.env.cr.execute(
            "UPDATE res_partner SET company_registry = nrc WHERE id = %s",
            (self.partner.id,),
        )
        self.partner.invalidate_recordset()
        self.assertEqual(self.partner.company_registry, "J2010000026229")
        path = Path(__file__).parent.parent / "migrations/19.0.0.10.1/post-migration.py"
        spec = importlib.util.spec_from_file_location("post_migration", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.migrate(self.env.cr, None)
        self.partner.invalidate_recordset()
        self.assertEqual(self.partner.company_registry, "18547290")
        self.assertEqual(self.partner.nrc, "J2010000026229")
