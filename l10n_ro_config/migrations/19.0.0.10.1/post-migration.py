# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import SUPERUSER_ID, api

BATCH = 1000


def migrate(cr, version):
    """Restore the CUI in company_registry where it was overwritten with the nrc.

    Only partners with a VAT number are touched: the standard l10n_ro compute
    derives the CUI from it. Partners without a VAT keep their value.
    """
    cr.execute(
        """
        SELECT p.id
          FROM res_partner p
          JOIN res_country c ON c.id = p.country_id
         WHERE c.code = 'RO'
           AND p.vat IS NOT NULL AND p.vat <> ''
           AND p.nrc IS NOT NULL AND p.nrc <> ''
           AND p.company_registry = p.nrc
        """
    )
    ids = [row[0] for row in cr.fetchall()]
    env = api.Environment(cr, SUPERUSER_ID, {"active_test": False})
    for start in range(0, len(ids), BATCH):
        partners = env["res.partner"].browse(ids[start : start + BATCH])
        partners._compute_company_registry()
        env.flush_all()
        env.invalidate_all()
