{
    'name' : 'Tax Reports',
    'version': '4.1.1',
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
        'reports/custom_header_creditnote.xml',
        'reports/report_credit_note.xml',
        'reports/reports.xml',
        'views/app_report_testview.xml',
    ],
    'installable': True,
    'application':True,
    'auto_install':False
}