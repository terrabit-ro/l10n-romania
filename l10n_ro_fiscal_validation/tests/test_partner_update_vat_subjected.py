# Copyright (C) 2017 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import codecs
import copy
import csv
import os
from unittest.mock import patch

import requests

from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger

from odoo.addons.l10n_ro_partner_create_by_vat.tests.anaf_data import ANAF_TEST_DATA


class TestPartnerUpdateVatSubjectedBase(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_model = cls.env["res.partner"]
        parts = cls.partner_model.search(
            [("country_id", "=", cls.env.ref("base.ro").id)]
        )
        parts.write({"country_id": False})
        data_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples/"
        )
        context = {
            "tracking_disable": True,
            "no_vat_validation": True,
        }

        with open(os.path.join(data_dir, "res.partner.csv"), "rb") as f:
            csvdata = csv.DictReader(codecs.iterdecode(f, "utf-8"))
            lines = [line for line in csvdata if any(line)]
        cls.env.user.company_id.write({"vat_check_vies": False})
        # A single create() for the whole file: the cron is checked against
        # more than one ANAF chunk, so this builds over a thousand partners.
        # Odoo 20: ``is_company`` is computed (own commercial entity with a VAT
        # number), the ``is_company`` column of the file is not written anymore.
        cls.partners = cls.partner_model.with_context(**context).create(
            [
                {
                    "name": line["name"],
                    "vat": line["vat"],
                    "country_id": cls.env.ref("base.ro").id,
                }
                for line in lines
            ]
        )


class TestUpdatePartner(TestPartnerUpdateVatSubjectedBase):
    def _run_cron(self, answer):
        calls = []

        class FakeResponse:
            """Answers without a correlationId, so the cron stays on the direct
            path: no polling sleep and no follow-up request."""

            status_code = 200

            def json(self):
                return {"found": [answer], "notFound": []}

        def post(url, **kwargs):
            calls.append(kwargs.get("json"))
            return FakeResponse()

        with mute_logger("odoo.addons.l10n_ro_fiscal_validation.models.res_partner"):
            with (
                patch.object(requests, "post", post),
                patch.object(requests.Session, "post", post),
            ):
                self.partner_model._update_l10n_ro_vat_subjected_all()
        return calls

    def _answer_for(self, partner, name):
        answer = copy.deepcopy(ANAF_TEST_DATA["4264242"])
        answer["date_generale"]["cui"] = int(partner.l10n_ro_vat_number)
        answer["date_generale"]["denumire"] = name
        answer["inregistrare_scop_Tva"]["scpTVA"] = True
        return answer

    def test_vat_subjected_cron(self):
        """The cron asks ANAF about every Romanian company and writes back."""
        # The company the fake ANAF will answer about.
        partner = self.partners[0]
        cui = int(partner.l10n_ro_vat_number)
        calls = self._run_cron(self._answer_for(partner, "PARTENER VERIFICAT ANAF SRL"))

        self.assertTrue(calls, "the cron must call ANAF")
        self.assertGreater(
            len(calls), 1, "more than a thousand partners must be sent in chunks"
        )
        asked = {item["cui"] for chunk in calls for item in chunk}
        self.assertIn(cui, asked, "the partner must be part of what is asked of ANAF")
        self.assertEqual(partner.name, "PARTENER VERIFICAT ANAF SRL")
        self.assertTrue(partner.l10n_ro_vat_subjected)

    def test_vat_subjected_cron_only_companies(self):
        """Odoo 20: only commercial entities are sent to ANAF and updated,
        not their contacts. ``is_company`` is computed and, with ``l10n_ro_edi``,
        a contact that receives the company CUI is flagged as company too."""
        company = self.partners[0]
        self.assertTrue(company.is_company)
        contact = self.partner_model.with_context(no_vat_validation=True).create(
            {
                "name": "Contact Persoana",
                "parent_id": company.id,
                "type": "contact",
            }
        )
        self.assertEqual(contact.vat, company.vat)
        self.assertEqual(contact.commercial_partner_id, company)

        calls = self._run_cron(self._answer_for(company, "COMPANIE VERIFICATA SRL"))

        asked = [item["cui"] for chunk in calls for item in chunk]
        self.assertEqual(
            asked.count(int(company.l10n_ro_vat_number)),
            1,
            "the contact must not be asked a second time",
        )
        self.assertEqual(company.name, "COMPANIE VERIFICATA SRL")
        self.assertEqual(contact.name, "Contact Persoana")

    def test_vat_subjected_anaf_down(self):
        """An ANAF error is only logged, the partners are left untouched."""
        partner = self.partners[0]
        name = partner.name

        def post(url, **kwargs):
            raise requests.exceptions.ConnectionError("ANAF down")

        with mute_logger("odoo.addons.l10n_ro_fiscal_validation.models.res_partner"):
            with (
                patch.object(requests, "post", post),
                patch.object(requests.Session, "post", post),
            ):
                self.partner_model._update_l10n_ro_vat_subjected_all()
        self.assertEqual(partner.name, name)
