# Copyright (C) 2026 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.tools import SQL

# Towns added in this version: SIRUTA code, county, name
NEW_TOWNS = [
    ("131103", "RO_PH", "Breaza"),
    ("167641", "RO_VL", "Băile Govora"),
    ("167696", "RO_VL", "Băile Olănești"),
    ("168130", "RO_VL", "Ocnele Mari"),
    ("60455", "RO_CT", "Eforie"),
]


def migrate(cr, version):
    # A town created by hand gets the external id of the new record,
    # so that the data file updates it instead of adding a duplicate.
    for siruta, state, name in NEW_TOWNS:
        cr.execute(
            SQL(
                """
                INSERT INTO ir_model_data (module, name, model, res_id, noupdate)
                SELECT 'l10n_ro_city', %(xmlid)s, 'res.city', MIN(c.id), FALSE
                  FROM res_city c
                  JOIN ir_model_data s
                    ON s.module = 'base' AND s.name = %(state)s
                   AND s.model = 'res.country.state' AND s.res_id = c.state_id
                 WHERE c.name->>'en_US' = %(name)s
                   AND NOT EXISTS (
                        SELECT 1 FROM ir_model_data d
                         WHERE d.model = 'res.city' AND d.res_id = c.id
                       )
                   AND NOT EXISTS (
                        SELECT 1 FROM ir_model_data d
                         WHERE d.module = 'l10n_ro_city' AND d.name = %(xmlid)s
                       )
                HAVING MIN(c.id) IS NOT NULL
                """,
                xmlid=f"RO_{siruta}",
                state=state,
                name=name,
            )
        )
