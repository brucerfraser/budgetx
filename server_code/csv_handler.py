import anvil.files
from anvil.files import data_files
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server
import csv
import re
import uuid
from dateutil.parser import parse
from datetime import date, datetime
import math

transaction_keys = {'date':'Value Date','description':'Description','amount':'Amount'}
all_trans_keys = ['date','description','amount','account','notes','hash']
# Hash will be a unique id to detect duplicates: daymonthyearamountaccount

@anvil.server.callable
def read_file(fn):
  mBytes = fn.get_bytes()

  # Convert bytes to a string.
  mString = str(mBytes, "utf-8")
  # Create a list of lines split on \n
  line_list = mString.split('\n')
  # which line is the header?
  head_line = header_line(line_list)
  # find alphanumeric words in the account header
  key_words = header_words(line_list,head_line)
  # do we know the account name?
  found, acc_id,accounts = account_finder(key_words)
  # comvert text file transaction body to list of lists and load transactions. 
  ready, raw = load_transactions(line_list,acc_id,head_line,accounts)
  # If there's no account, we did not hash or make a ready list of dicts. 
  # Time to go back to client.
  return acc_id, ready, raw, accounts
  
  
  

def header_line(file):
  header_triggers = ["date","amount","description","details","debits","credits","balance"]
  r = 0
  for l in file:
    r += 1
    triggers = 0
    for t in header_triggers:
      if t in l.lower():
        triggers += 1
    # print(l)
    if triggers > 2:
      break
  return r-1

def header_words(csv_output, header):
  # find all alphanum string-parts in the csv rows before the ehader row
  word_list = []
  for l in csv_output[0:header]:
    for word in re.findall(r'[a-zA-Z0-9]+', l):
      word_list.append(word.lower())
  return word_list

@anvil.server.callable
def need_an_id():
  return str(uuid.uuid4())

def account_finder(keys=None,match=True):
  # get all the accounts
  accounts = []
  for row in app_tables.accounts.search():
    row_dict = dict(row)
    accounts.append(row_dict)
  if match:
    found = False
    match = True
    acc_id = ''
    for acc in accounts:
      match = True
      if len(acc['acc_keywords']) > 0:
        for key in acc['acc_keywords']:
          if key.lower() not in keys:
            match = False
        if match:
          acc_id = acc['acc_id']
          found = True
          break
    return found, acc_id,accounts
  else:
    return accounts

def load_transactions(file,account,head_line,accounts):
  # first we get a list of lists
  sep,quote = find_sep_quote(file)
  new = file[head_line].replace("\r","")
  new = new.replace(" ","")
  if quote:
    new=new.replace(quote,"")
  header_list = new.split(sep)
  # print(header_list)
  raw_list = []
  for line in file[head_line+1:]:
    new = line.replace("\r","")
    # new = new.replace(" ","")
    try:
      if new[-1] == ',':
        new = new[0:-1]
    except:
      pass
    if new:
      raw_list.append(new.split(sep))
  # first we check head_line for debits/credits or amount
  if not 'Amount' in header_list:
    dbt = header_list.index("Debits")
    crt = header_list.index("Credits")
    header_list.append("Amount")
    for t in raw_list:
      c = float(t[crt]) if t[crt] else 0.0
      d = float(t[dbt]) if t[dbt] else 0.0
      t.append(str(c-d))
  # Now we make a transaction dictionary
  trans_list = []
  for t in raw_list:
    d = dict(zip(header_list,t))
    trans_list.append(d)
  # this dictionary is still based on the CSV file. We have to get it into BudgetX language keys
  # Here's where we split to make efficient!
  r,t = make_ready(account,trans_list,accounts)
  print(len(r),len(t))
  return r,t

@anvil.server.callable
def make_ready(account,trans_list,accounts=None):
  if not accounts:
    accounts = account_finder(None,False)
  if account:
    print("account good")
    # try:
    deets = list(filter(lambda d: d['acc_id'] == account, accounts))      
    ready_transactions = []
    # print(len(trans_list))
    t1 = 0
    for t in trans_list:
      d = {}
      t2 = 0
      for key in all_trans_keys:
        if key in deets[0]['key_map']:
          d[key] = t[deets[0]['key_map'][key]]
        t2 += 1
        if t2 == 2000:
          print('t2 auto stop')
          break
      d['account'] = account
      # daymonthyearamountaccount
      try:
        d['amount'] = int(math.trunc(d['amount']*100))
      except:
        d['amount'] = float(d['amount'])*100
        d['amount'] = int(math.trunc(d['amount']))
      d['hash'] = str(parse(d['date']).day) + str(parse(d['date']).month) + str(parse(d['date']).year) + str(d['amount']) + d['account']
      d['transaction_id'] = need_an_id()
      d['date'] = parse(d['date']).date()
      ready_transactions.append(d)
      t1 += 1
      if t1 == 2000:
        print('t1 auto stop')
        break
      # ready for transport back to client
    return ready_transactions,trans_list
    # except:
    #   # ready for transport back to client
    #   return [],trans_list
  else:
    # ready for transport back to client
    return [],trans_list

@anvil.server.callable
def duplicate_check(hash_list):
  i = 0
  for hash in hash_list:
    for row in app_tables.transactions.search(hash=hash):
      i += 1
      break
  return i
  
@anvil.server.callable
def save_transactions(ready_list):
  for t in ready_list:
    if len(list(app_tables.transactions.search(hash=t['hash']))) == 0:
      # t['date'] = parse(t['date']).date()
      t['amount'] = update_numbers(float(t['amount']))
      app_tables.transactions.add_row(**t)

def update_numbers(num):
  return int(math.trunc(num*100))

def find_sep_quote(list_obj):
  s_c = 0
  l_c = 0
  d_q = 0
  s_q = 0
  for line in list_obj:
    s_c += line.count(',')
    l_c += line.count(';')
    d_q += line.count('"')
    s_q += line.count("'")
  if s_c > l_c:
    sep = ','
  else:
    sep = ';'
  if d_q > s_q:
    quo = '"'
  elif s_q > d_q:
    quo = "'"
  else:
    quo = ''
  return sep, quo