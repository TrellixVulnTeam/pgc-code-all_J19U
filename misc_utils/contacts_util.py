# -*- coding: utf-8 -*-
"""
Created on Wed Jan  9 10:03:43 2019

@author: disbr007
"""

import calendar
import datetime
import pandas as pd
import numpy as np
import os
import shutil


def emailByRegion(contacts_xl, region):
    '''Generate list of contact emails only for selected region, writes to txt file'''
    df = pd.read_excel(contacts_xl, header=0)
    emails = df[df['Region']==region]['Email'].tolist()
    emails = ', '.join(emails)
    out_dir = os.path.dirname(contacts_xl)
    outpath = os.path.join(out_dir, '{}_emails.txt'.format(region))
    with open(outpath, 'w') as email_txt:
        email_txt.write(r'{}'.format(emails))
    return emails

   
def contacts_update(contacts_xl, new_contacts_xl):
    project_dir = os.path.dirname(contacts_xl)
    
    # For naming outputs
    date = str(datetime.date.today())
    year, month, day = date.split('-')
    date_words = r'{}{}{}'.format(year, str.lower(calendar.month_abbr[int(month)]), day)
    
    # Read the new contacts csv in
    new_contacts = pd.read_csv(new_contacts_xl, sep=',', encoding = "ISO-8859-1")
    # Create a columns to align with contacts formatting
    new_contacts['Region'] = np.NaN
    new_contacts['Old/New'] = 'New'
    
    # Create copy of old contacts sheet
    copy_contacts_xl = os.path.join(project_dir, r'contacts_{}.xlsx'.format(date_words))
    shutil.copyfile(contacts_xl, copy_contacts_xl)
    
    # Read in the new copy
    contacts = pd.read_excel(copy_contacts_xl)
    
    # Set all old contacts as 'Old'
    contacts['Old/New'] = 'Old'
    # Add new contacts
    contacts = contacts.append(new_contacts)
    # Drop duplicate contacts by Name, keep the first (old) row
    contacts.drop_duplicates(subset='Name', keep='first', inplace=True)
    # Reorder columns
    cols = ['Name', 'Email', 'Phone', 'Affiliation', 'City', 'State', 'Projects', 'Awards',
            'Contact No Longer Active?', 'Arctic Tasking Solicitation Recipient',
             'Antarctic Tasking Solicitation Recipient', 'Old/New', 'Region']
    contacts = contacts[cols]
    
    # Write out the updated sheet
    writer = pd.ExcelWriter(copy_contacts_xl, engine='xlsxwriter')
    contacts.to_excel(writer, header=True, index=False, sheet_name='Sheet1')
    writer.save()
    
    return contacts


working_dir = r'E:\disbr007\UserServicesRequests\contacts'
contacts_path = os.path.join(working_dir, 'contacts.xlsx')
new_contacts_path = os.path.join(working_dir, 'Contacts_2019may23.csv')

updated_contacts = contacts_update(contacts_path, new_contacts_path)

antartic_emails = emailByRegion(r"E:\disbr007\UserServicesRequests\contacts\contacts_2019may23.xlsx", 'Arctic')
arctic_emails = emailByRegion(r"E:\disbr007\UserServicesRequests\contacts\contacts_2019may23.xlsx", 'Antarctic')