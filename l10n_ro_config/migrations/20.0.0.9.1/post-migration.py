# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Recompute ``is_company`` on contacts wrongly flagged as companies.

    ``l10n_ro_edi`` marked every Romanian partner with a valid company CUI as a
    company, including the contacts of a company (they inherit its CUI).
    """
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    partners = (
        env["res.partner"]
        .with_context(active_test=False)
        .search([("parent_id", "!=", False), ("is_company", "=", True)])
    )
    if not partners:
        return
    _logger.info("Recomputing is_company on %s contact(s)", len(partners))
    env.add_to_compute(partners._fields["is_company"], partners)
    partners._recompute_recordset(["is_company"])
    env.flush_all()
