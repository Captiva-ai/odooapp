{
    'name': 'MRP Services Cost',
    'version': '18.0.1.0',
    'summary': 'Add service costs to manufacturing orders',
    'description': """
    Calculate and allocate service costs inside MRP manufacturing orders.
    """,
    'category': 'Manufacturing',
    'author': 'Captiva AI',
    'website': 'https://captiva-ai.com',
    'depends': ['mrp', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/mrp_service_views.xml',
    ],
    'license': 'OPL-1',
    'price': 49.0,
    'currency': 'USD',
    'installable': True,
    'application': False,
}
