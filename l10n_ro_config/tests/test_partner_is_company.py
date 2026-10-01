# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPartnerIsCompany(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # no_vat_validation: skip the ANAF VAT-on-payment lookup done on create
        # by l10n_ro_vat_on_payment, when installed.
        cls.Partner = cls.env["res.partner"].with_context(no_vat_validation=True)
        cls.ro = cls.env.ref("base.ro")
        cls.company = cls.Partner.create(
            {
                "name": "RO Company SRL",
                "country_id": cls.ro.id,
                "vat": "RO12345674",
            }
        )

    def test_ro_company_with_valid_cui(self):
        self.assertTrue(self.company.is_company)

    def test_ro_contact_of_company(self):
        contact = self.Partner.create(
            {
                "name": "Ion Popescu",
                "parent_id": self.company.id,
                "type": "contact",
            }
        )
        # the contact inherits the CUI of its company
        self.assertEqual(contact.vat, self.company.vat)
        self.assertEqual(contact.country_id, self.ro)
        self.assertFalse(contact.is_company)

        # a contact created with the CUI and the country in its values (import,
        # create by VAT, ...) is computed after both are set
        contact_2 = self.Partner.create(
            {
                "name": "Elena Popescu",
                "parent_id": self.company.id,
                "country_id": self.ro.id,
                "vat": self.company.vat,
            }
        )
        self.assertFalse(contact_2.is_company)

        # any later recomputation (VAT change, migration, ...) keeps them out
        contacts = contact | contact_2
        self.env.add_to_compute(contacts._fields["is_company"], contacts)
        contacts._recompute_recordset(["is_company"])
        self.assertFalse(contact.is_company)
        self.assertFalse(contact_2.is_company)

        # detaching the contact makes it its own commercial entity again
        contact.parent_id = False
        self.assertTrue(contact.is_company)

    def test_ro_natural_person(self):
        person_cnp = self.Partner.create(
            {
                "name": "Maria Ionescu",
                "country_id": self.ro.id,
                "vat": "1800101420010",
            }
        )
        self.assertFalse(person_cnp.is_company)
        person_no_vat = self.Partner.create(
            {"name": "Vasile Georgescu", "country_id": self.ro.id}
        )
        self.assertFalse(person_no_vat.is_company)

    def test_foreign_partner_base_behaviour(self):
        be_company = self.Partner.create(
            {
                "name": "BE Company",
                "country_id": self.env.ref("base.be").id,
                "vat": "BE0477472701",
            }
        )
        self.assertTrue(be_company.is_company)
        be_contact = self.Partner.create(
            {"name": "BE Contact", "parent_id": be_company.id}
        )
        self.assertFalse(be_contact.is_company)
        be_person = self.Partner.create(
            {"name": "BE Person", "country_id": self.env.ref("base.be").id}
        )
        self.assertFalse(be_person.is_company)
