# coding: utf-8
# Copyright (C) 2017 Opener B.V. (<https://opener.am>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    'name': 'Pos Rescue Sessions',
    'summary': 'Backport of POS Rescue mechanism from Odoo 9.0',
    'version': '8.0.1.0.0',
    'category': 'Point Of Sale',
    'author': 'Opener B.V., Odoo Community Association (OCA)',
    'website': 'https://github.com/oca/pos',
    'license': 'AGPL-3',
    'depends': [
        'point_of_sale',
    ],
    'data': [
        'views/assets.xml',
        'views/pos_session_opening.xml',
    ],
    'qweb': [
    ],
    'installable': True,
}
