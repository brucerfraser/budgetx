import anvil.files
from anvil.files import data_files
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server
from dateutil.parser import parse
from datetime import date, datetime
import math

@anvil.server.callable
def get_hash_date(date):
  return str(parse(date).day) + str(parse(date).month) + str(parse(date).year)

@anvil.server.callable
def clear_cats():
  for row in app_tables.transactions.search():
    row['category'] = None

@anvil.server.callable
def clean_hash():
  for row in app_tables.transactions.search():
    row['hash'] = str(row['date'].day) + str(row['date'].month) + str(row['date'].year) + str(row['amount']) + row['account']



@anvil.server.callable
def clean_dups():
  quick_trans = []
  for row in app_tables.transactions.search():
    quick_trans.append(dict(row))
  dup_list = []
  for t in quick_trans:
    id = t['transaction_id']
    hash = str(t['date'].day) + str(t['date'].month) + str(t['date'].year) + str(t['amount']) + t['account']
    for tr in quick_trans:
      h = str(tr['date'].day) + str(tr['date'].month) + str(tr['date'].year) + str(tr['amount']) + tr['account']
      if hash == h and tr['transaction_id'] != id:
        # we have a duplicate
        already = False
        for p in dup_list:
          if id in p:
            already = True
            break
        if not already:
          dup_list.append((id,tr['transaction_id']))
          break
  # print("There are {n} flagged duplicates".format(n=len(dup_list)))
  # dup_list_delete = []
  for pair in dup_list:
    if app_tables.transactions.get(transaction_id=pair[0])['category']:
      # first of the pairs has been categorised
      app_tables.transactions.get(transaction_id=pair[1]).delete()
      # cat = app_tables.transactions.get(transaction_id=pair[0])['category']
      # cat_str = 'No cat' if not cat else cat
      # dup_list_delete.append((app_tables.transactions.get(transaction_id=pair[0])['description'] + cat_str,
      #                         dict(app_tables.transactions.get(transaction_id=pair[1]))))
    else:
      app_tables.transactions.get(transaction_id=pair[0]).delete()
      # cat = app_tables.transactions.get(transaction_id=pair[1])['category']
      # cat_str = 'No cat' if not cat else cat
      # dup_list_delete.append((app_tables.transactions.get(transaction_id=pair[1])['description'] + cat_str,
      #                         dict(app_tables.transactions.get(transaction_id=pair[0]))))
  # for del_pair in dup_list_delete:
  #   print(del_pair[0],'\n',del_pair[1],'\n_________________')