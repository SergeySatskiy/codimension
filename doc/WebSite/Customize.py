# encoding: utf-8

import re


for test_string in ['555-1212', 'ILL-EGAL']:
    # cml 1 rt text="Match regular expr"
    if re.match(
        r'^\d{3}-\d{4}$', test_string):
        # cml 1 rt text="Valid"
        # cml 1 cc background=#00ff00
        print test_string, \
              'is a valid US local phone number'
    else:
        # cml 1 rt text="Rejected"
        # cml 1 cc background=#ff0000
        # cml+ foreground=#ffffff
        print test_string, 'rejected'
