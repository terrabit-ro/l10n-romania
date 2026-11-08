# Copyright (C) 2026 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.tools import SQL


def migrate(cr, version):
    # Giurgiu postal codes start with 08, not 87
    cr.execute(
        SQL(
            """
            UPDATE res_country_state
               SET l10n_ro_prefix_zip = '08'
             WHERE id = (
                    SELECT res_id FROM ir_model_data
                     WHERE module = 'base' AND name = 'RO_GR'
                       AND model = 'res.country.state'
                   )
               AND l10n_ro_prefix_zip = '87'
            """
        )
    )
