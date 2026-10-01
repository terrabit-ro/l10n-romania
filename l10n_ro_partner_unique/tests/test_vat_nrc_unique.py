# Copyright (C) 2017 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

# Odoo 20: ``res.partner.is_company`` is computed and stored
# (``commercial_partner_id == partner and has_vat``, refined by ``l10n_ro_edi``
# for Romanian partners: a CNP of a natural person is not a company). It can no
# longer be written, so the tests build companies / persons / contacts through
# ``vat``, ``country_id`` and ``parent_id`` and assert the computed flag.

from odoo.exceptions import ValidationError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon

CUI = "RO30834857"
NRC = "J35/2622/2012"
CNP = "1800101420010"


@tagged("post_install", "-at_install")
class TestVatUnique(AccountTestInvoicingCommon):
    @classmethod
    @AccountTestInvoicingCommon.setup_country("ro")
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.l10n_ro_accounting = True
        cls.Partner = cls.env["res.partner"]
        cls.country_ro = cls.env.ref("base.ro")
        cls.partner = cls.Partner.create(
            {"name": "Test partner", "vat": CUI, "nrc": NRC}
        )

    def _set_mode(self, mode):
        self.env["ir.config_parameter"].sudo().set_str(
            "l10n_ro_partner_unique.vat_nrc_unique", mode
        )

    def test_company_setup(self):
        """A partner without parent and with a CUI is a company."""
        self.assertTrue(self.partner.is_company)
        self.assertTrue(self.partner.is_l10n_ro_record)

    # ------------------------------------------------------------------
    # CUI duplicates
    # ------------------------------------------------------------------
    def test_duplicated_vat_nrc_creation(self):
        """Mode ``vat_nrc``: the (CUI, NRC) pair must be unique."""
        self._set_mode("vat_nrc")
        with self.assertRaises(ValidationError):
            self.Partner.create({"name": "Second partner", "vat": CUI, "nrc": NRC})
        # same CUI, other NRC -> allowed
        second = self.Partner.create(
            {"name": "Second partner", "vat": CUI, "nrc": "J2012002622359"}
        )
        self.assertTrue(second.is_company)
        # same CUI, without NRC -> allowed (no partner with an empty NRC matches)
        self.Partner.create({"name": "Third partner", "vat": CUI})

    def test_duplicated_vat_nrc_existing_without_nrc(self):
        """Mode ``vat_nrc``: a company with the same CUI and no NRC blocks the
        creation whatever the new NRC is."""
        self._set_mode("vat_nrc")
        self.partner.nrc = False
        with self.assertRaises(ValidationError):
            self.Partner.create(
                {"name": "Second partner", "vat": CUI, "nrc": "J2012002622359"}
            )

    def test_duplicated_vat_creation(self):
        """Mode ``vat`` (default): the CUI must be unique, whatever the NRC."""
        self._set_mode("vat")
        with self.assertRaises(ValidationError):
            self.Partner.create({"name": "Second partner", "vat": CUI, "nrc": NRC})
        with self.assertRaises(ValidationError):
            self.Partner.create(
                {"name": "Second partner", "vat": CUI, "nrc": "J2012002622359"}
            )
        with self.assertRaises(ValidationError):
            self.Partner.create({"name": "Second partner", "vat": CUI})

    def test_duplicated_vat_creation_default_mode(self):
        """Without the parameter the mode is ``vat``."""
        self.env["ir.config_parameter"].sudo().search(
            [("key", "=", "l10n_ro_partner_unique.vat_nrc_unique")]
        ).unlink()
        with self.assertRaises(ValidationError):
            self.Partner.create(
                {"name": "Second partner", "vat": CUI, "nrc": "J2012002622359"}
            )

    def test_duplicated_vat_creation_without_prefix(self):
        """The CUI is compared with and without the ``RO`` prefix."""
        with self.assertRaises(ValidationError):
            self.Partner.create(
                {"name": "Second partner", "vat": "30834857", "nrc": NRC}
            )
        with self.assertRaises(ValidationError):
            self.Partner.create(
                {
                    "name": "Second partner",
                    "vat": "30834857",
                    "country_id": self.country_ro.id,
                }
            )

    def test_duplicated_vat_case_insensitive(self):
        """The CUI prefix is compared case-insensitively."""
        with self.assertRaises(ValidationError):
            self.Partner.create({"name": "Second partner", "vat": "ro30834857"})

    def test_partial_vat_creation(self):
        """A partner with a partial CUI can be created, but not corrected
        into an existing CUI."""
        partner = self.Partner.create({"name": "Test partner 1", "vat": "RO308"})
        with self.assertRaises(ValidationError):
            partner.vat = CUI  # try to fix vat

        partner = self.Partner.create(
            {"name": "Test partner 1", "vat": "RO3083485789", "nrc": NRC}
        )
        with self.assertRaises(ValidationError):
            partner.vat = CUI  # try to fix vat

    def test_write_nrc_vat_nrc_mode(self):
        """Mode ``vat_nrc``: changing the NRC into an existing pair is blocked."""
        self._set_mode("vat_nrc")
        second = self.Partner.create(
            {"name": "Second partner", "vat": CUI, "nrc": "J2012002622359"}
        )
        with self.assertRaises(ValidationError):
            second.nrc = NRC

    # ------------------------------------------------------------------
    # CNP (natural persons)
    # ------------------------------------------------------------------
    def _require_l10n_ro_edi(self):
        if "l10n_ro_edi" not in self.env.registry._init_modules:
            self.skipTest("l10n_ro_edi (auto-installed) defines CNP persons")

    def test_duplicated_cnp_natural_person(self):
        """Romanian natural persons (CNP) are not companies, so two persons
        with the same CNP are allowed, as persons were in 19.0."""
        self._require_l10n_ro_edi()
        vals = {"vat": CNP, "country_id": self.country_ro.id}
        person_1 = self.Partner.create(dict(vals, name="Person 1"))
        person_2 = self.Partner.create(dict(vals, name="Person 2"))
        self.assertFalse(person_1.is_company)
        self.assertFalse(person_2.is_company)

    def test_duplicated_cnp_as_company(self):
        """A CNP on a partner that Odoo considers a company (no Romanian
        country, so the ``l10n_ro_edi`` person rule does not apply) is checked
        like any CUI, as a company with a CNP was in 19.0."""
        company_1 = self.Partner.create({"name": "PFA 1", "vat": CNP})
        self.assertTrue(company_1.is_company)
        with self.assertRaises(ValidationError):
            self.Partner.create({"name": "PFA 2", "vat": CNP})

    def test_cnp_person_same_as_company(self):
        """A natural person may share the CNP of a company partner."""
        self._require_l10n_ro_edi()
        self.Partner.create({"name": "PFA", "vat": CNP})
        person = self.Partner.create(
            {"name": "Person", "vat": CNP, "country_id": self.country_ro.id}
        )
        self.assertFalse(person.is_company)

    # ------------------------------------------------------------------
    # Child contacts
    # ------------------------------------------------------------------
    def test_contact_vat_creation(self):
        """Contacts of a company share its CUI without error."""
        child_1 = self.Partner.create(
            {
                "name": "Test partner 1 - child",
                "parent_id": self.partner.id,
                "vat": CUI,
                "nrc": NRC,
            }
        )
        child_2 = self.Partner.create(
            {
                "name": "Test partner 2 - child",
                "parent_id": self.partner.id,
                "type": "invoice",
            }
        )
        self.assertEqual(child_1.commercial_partner_id, self.partner)
        self.assertEqual(child_2.commercial_partner_id, self.partner)
        self._set_mode("vat_nrc")
        self.Partner.create(
            {
                "name": "Test partner 3 - child",
                "parent_id": self.partner.id,
                "vat": CUI,
                "nrc": NRC,
            }
        )

    def test_contact_detached_becomes_company(self):
        """A contact detached from its parent becomes a company (Odoo 20
        equivalent of setting ``is_company`` on a person in 19.0) and is
        checked."""
        child = self.Partner.create(
            {"name": "Test partner - child", "parent_id": self.partner.id}
        )
        self.assertEqual(child.vat, self.partner.vat)
        with self.assertRaises(ValidationError):
            child.parent_id = False

    # ------------------------------------------------------------------
    # Companies
    # ------------------------------------------------------------------
    def test_different_companies(self):
        """Uniqueness is checked per ``company_id`` (shared partners apart)."""
        company_2 = self.setup_other_company(name="company RO 2")["company"]
        company_2.l10n_ro_accounting = True
        own = self.env.company
        # a partner restricted to a company does not clash with a shared one
        partner_c1 = self.Partner.create(
            {"name": "Partner company 1", "vat": CUI, "company_id": own.id}
        )
        partner_c2 = self.Partner.create(
            {"name": "Partner company 2", "vat": CUI, "company_id": company_2.id}
        )
        self.assertTrue(partner_c1.is_company and partner_c2.is_company)
        # but inside the same company it does
        with self.assertRaises(ValidationError):
            self.Partner.create(
                {"name": "Partner company 1 bis", "vat": CUI, "company_id": own.id}
            )
        with self.assertRaises(ValidationError):
            self.Partner.create(
                {
                    "name": "Partner company 2 bis",
                    "vat": CUI,
                    "company_id": company_2.id,
                }
            )

    def test_non_romanian_company(self):
        """Partners of a company without Romanian accounting are not checked."""
        company_2 = self.setup_other_company(name="company non RO")["company"]
        company_2.l10n_ro_accounting = False
        vals = {"vat": CUI, "company_id": company_2.id}
        partner_1 = self.Partner.create(dict(vals, name="Partner 1"))
        self.Partner.create(dict(vals, name="Partner 2"))
        self.assertFalse(partner_1.is_l10n_ro_record)

    # ------------------------------------------------------------------
    # Merge
    # ------------------------------------------------------------------
    def test_partner_merge_context(self):
        """The ``partner_merge`` context skips the check."""
        duplicate = self.Partner.with_context(partner_merge=True).create(
            {"name": "Duplicate partner", "vat": CUI, "nrc": NRC}
        )
        self.assertTrue(duplicate.is_company)

    def test_partner_merge_wizard(self):
        """Merging duplicated partners is not blocked by the constraint."""
        duplicate = self.Partner.with_context(partner_merge=True).create(
            {"name": "Duplicate partner", "vat": CUI, "nrc": NRC}
        )
        wizard = self.env["base.partner.merge.automatic.wizard"]
        wizard._merge((self.partner + duplicate).ids, dst_partner=self.partner)
        self.assertFalse(duplicate.exists())
        self.assertTrue(self.partner.exists())

        duplicate = self.Partner.with_context(partner_merge=True).create(
            {"name": "Duplicate partner", "vat": CUI, "nrc": NRC}
        )
        wizard._merge((self.partner + duplicate).ids)
        self.assertEqual(len((self.partner + duplicate).exists()), 1)
