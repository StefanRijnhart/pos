# coding: utf-8
# Copyright (C) 2017: Opener B.V. (https://opener.amsterdam)
# @author: Stefan Rijnhart <stefan@opener.am>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    'name': 'POS Order history',
    'version': '8.0.1.0.0',
    'author': 'Opener B.V.,Odoo Community Association (OCA)',
    'category': 'Point Of Sale',
    'license': 'AGPL-3',
    'depends': [
        'point_of_sale',
    ],
    'website': 'https://github.com/oca/pos',
    'data': [
        'views/assets.xml',
    ],
    'qweb': [
        'static/src/xml/pos_order_history.xml',
    ],
}
