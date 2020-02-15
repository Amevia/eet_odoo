# -*- coding: utf-8 -*-
##############################################################################
#    Copyright (C) 2020 Amevia s.r.o. (<https://amevia.eu/sluzby).
##############################################################################
{
    'name': 'EET (CZ)',
    'version': '1.0',
    'summary': 'Registration of Sales',
    'description': """
Registration of Sales
=====================
The module registers sales with Czech Republic authority, and fetches FIK in order to set
on the printed receipt.

Install the following python package:
    1. pyOpenSSL (pip3 install pyOpenSSL)
    
Configure the absolute path as value showing location of the certificate situated in server into the system parameter with key pkcs12.
    """,
    'author': 'PERLUR Group and Optimal4',
    'price': '50',
    'currency': 'EUR',
    'website': 'https://amevia.eu',
    'category': 'Point Of Sale',
    'depends': ['point_of_sale', 'purchase'],
    'data': [
        'security/revenue_data_message_security.xml',
        'security/ir.model.access.csv',
        'wizard/connection_test_view.xml',
        'views/connection_test_menuitem.xml',
        'views/account_tax_view.xml',
        'views/product_view.xml',
        'views/res_partner_view.xml',
        'views/res_company_view.xml',
        'views/data_message_menuitem.xml',
        'views/data_message_view.xml',
        'views/point_of_sale.xml',
        'data/payment_data.xml',
        'data/certificate_details.xml',
    ],
    'qweb': ['static/src/xml/pos.xml'],
    'external_dependencies': {'python': ['OpenSSL']},
    'installable': True,
    'application': True,
    'auto_install': False
}

