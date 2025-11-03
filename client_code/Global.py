import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import uuid
from datetime import date

global ACCOUNTS
ACCOUNTS = []

global CATEGORIES
CATEGORIES = {}


global PERIOD
PERIOD = (0,0)

accounts = anvil.server.call('get_accounts')
keys = list(accounts.keys())
ACCOUNTS = [(accounts[k],k) for k in keys]

def all_categories():
  global CATEGORIES
  cats = {}
  for row in app_tables.categories.search():
    cats[row['category_id']] = [row['name'],row['colour_back'],row['colour_text']]
  for row in app_tables.sub_categories.search():
    display = cats[row['belongs_to']][0] + " - " + row['name']
    CATEGORIES[row['sub_category_id']] = {'display':display,'colour':cats[row['belongs_to']][1]}
    

def new_id_needed():
  return str(uuid.uuid4())

def make_date(m=None,y=None,custom=False):
  global PERIOD
  if custom:
    PERIOD = (m,y,True)
  else:
    if m:
      PERIOD = (m,y,False)
    else:
      t = date.today()
      PERIOD = (t.month,t.year,False)

all_categories()



