{
    'name': 'Medical Lens Shop',
    'version': '17.0.9.0.0',
    'category': 'Website/eCommerce',
    'summary': 'Professional Medical Lens Selector (Spanish)',
    'description': 'Advanced module for selling medical lenses with matrix selection, dynamic pricing, and prescription handling.',
    'depends': ['website_sale', 'product', 'sale', 'account'],
    'data': [
        'views/product_view.xml',
        'views/website_templates.xml',
        'reports/medical_report.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'medical_lens2/static/src/scss/medical_lens.scss',
            'medical_lens2/static/src/js/medical_lens.js',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}