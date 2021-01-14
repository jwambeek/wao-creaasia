{
    'name' : 'Tax Reports',
    'version': '2.9',
    'Summary': 'Tax Report Prints',
    'description': 'To print the new report',
    'license': 'LGPL-3',
    'depends': [
        'sale_management','website','account_accountant'
    ],    
    'data': [
        'reports/custom_header1.xml',
        'reports/report_tax_invoice1.xml',
        'reports/custom_header_copy.xml',
        'reports/report_tax_invoice_copy1.xml',
        'reports/custom_header_creditnote',
        'reports/report_credit_note',
        'reports/reports.xml',
        'views/app_report_testview.xml',

    ],
    'installable': True,
    'application':True,
    'auto_install':False
}