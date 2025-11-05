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

global SMART
SMART = {}

global PERIOD
PERIOD = (0,0)

global CUSTOM
CUSTOM = (None,None)

accounts = anvil.server.call('get_accounts')
keys = list(accounts.keys())
ACCOUNTS = [(accounts[k],k) for k in keys]

# for row in app_tables.transactions.search():
#   row['category'] = None

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
  global PERIOD,CUSTOM
  if custom:
    PERIOD = (0,0)
    CUSTOM = (m,y)
  else:
    if m:
      PERIOD = (m,y)
    else:
      t = date.today()
      PERIOD = (t.month,t.year)

def smarter(first=True,update=None):
  """
  first used during app startup
  update is tuple:
  (category id,description of transaction)
  """
  global SMART
  if first:
    for row in app_tables.transactions.search(q.not_(category=None)):
      words = row['description'].split()
      if row['category'] not in SMART:
        SMART[row['category']] = []
      for word in words:
        if word not in SMART[row['category']]:
          SMART[row['category']].append(word)
  else:
    words = update[1].split()
    if update[0] not in SMART:
      SMART[update[0]] = []
    for word in words:
      if word not in SMART[update[0]]:
        SMART[update[0]].append(word)

def is_it_smart(description):
  """
  SOMETHING WRONG in here.
  Allocating a category when no words match. Maybe restrict words that make it
  into the match lists? Maybe the match algorithm not working?
  """
  
  global SMART
  words = description.split()
  leader = {}
  for k,v in SMART.items():
    m = 0
    for word in words:
      if word in v:
        m += 1
    if m > 0:
      if k not in leader:
        leader[k] = 0
      leader[k] += 1
  if leader:
    return max(leader, key=leader.get)
  else:
    return None
  

# all_categories()
# smarter()



