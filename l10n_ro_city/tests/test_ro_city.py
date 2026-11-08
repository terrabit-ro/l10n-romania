# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)


from odoo.exceptions import UserError
from odoo.tests import Form
from odoo.tests.common import TransactionCase


class TestRoCity(TransactionCase):
    def setUp(self):
        super().setUp()

        self.city_1 = self.env.ref("l10n_ro_city.RO_22585")
        self.city_2 = self.env.ref("l10n_ro_city.RO_21588")
        self.city_3 = self.env.ref("l10n_ro_city.RO_6734")
        self.state_bc = self.env.ref("base.RO_BC")
        self.state_b = self.env.ref("base.RO_B")

    def test_city(self):
        self.assertEqual(self.city_1.name, "Filipești")

        display_name = self.city_1.display_name
        self.assertEqual(display_name, "Filipești (BC)")

        display_name = self.city_2.display_name
        self.assertEqual(display_name, "Filipești (Bogdănești) (BC)")

    def test_partner_on_change_city(self):
        city_obj = self.env["res.city"]
        with Form(self.env["res.partner"]) as partner_form:
            partner_form.name = "Test State Onchange"
            partner_form.country_id = self.env.ref("base.ro")
            partner_form.city_id = self.city_3

            # Changes state, which triggers onchange
            partner_form.state_id = self.state_bc

        self.assertEqual(partner_form.city_id, city_obj)

    def test_completare_zip(self):
        partner_form = Form(self.env["res.partner"])
        partner_form.country_id = self.env.ref("base.ro")
        # competare cod postal filipesti
        partner_form.state_id = self.state_bc
        partner_form.zip = "607185"
        self.assertEqual(partner_form.city_id.name, "Filipești")

        partner_form.state_id = self.state_b
        partner_form.zip = "030011"
        self.assertEqual(partner_form.city_id.name, "Sector3")

    def test_onchange_zip_state_mismatch_raises_usererror(self):
        partner_form = Form(self.env["res.partner"])
        partner_form.country_id = self.env.ref("base.ro")
        partner_form.state_id = self.state_b

        with self.assertRaises(UserError):
            # 607185 belongs to BC while the partner state is B.
            partner_form.zip = "607185"

    def test_onchange_zip_bucharest_sector_mismatch_raises_usererror(self):
        partner_form = Form(self.env["res.partner"])
        partner_form.country_id = self.env.ref("base.ro")
        partner_form.state_id = self.state_bc

        with self.assertRaises(UserError):
            # 030011 belongs to Bucharest sectors and requires state B.
            partner_form.zip = "030011"

    def test_state_prefix_zip(self):
        self.assertEqual(self.env.ref("base.RO_GR").l10n_ro_prefix_zip, "08")

    def test_towns_without_same_name_locality(self):
        # These towns have no component locality of the same name
        for xmlid, name, zipcode in [
            ("l10n_ro_city.RO_131103", "Breaza", "105400"),
            ("l10n_ro_city.RO_167641", "Băile Govora", "245200"),
            ("l10n_ro_city.RO_167696", "Băile Olănești", "245300"),
            ("l10n_ro_city.RO_168130", "Ocnele Mari", "245900"),
            ("l10n_ro_city.RO_60455", "Eforie", "905300"),
        ]:
            city = self.env.ref(xmlid)
            self.assertEqual(city.name, name)
            self.assertEqual(city.zipcode, zipcode)
            self.assertEqual(city.l10n_ro_municipality, name)

    def test_city_names(self):
        self.assertEqual(self.env.ref("l10n_ro_city.RO_63401").name, "Sfântu Gheorghe")
        self.assertEqual(
            self.env.ref("l10n_ro_city.RO_179542").name, "Popești-Leordeni"
        )
