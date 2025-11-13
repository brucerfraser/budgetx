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

global Transactions_Form
Transactions_Form = None

accounts = anvil.server.call('get_accounts')
keys = list(accounts.keys())
ACCOUNTS = [(accounts[k],k) for k in keys]

def open_transactions_instance():
  global Transactions_Form
  from .Components.Transactions import Transactions
  Transactions_Form = Transactions(dash=True)

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
      words = [word for word in words if len(word) >= 3]
      if row['category'] not in SMART:
        SMART[row['category']] = []
      for word in words:
        if word not in SMART[row['category']]:
          SMART[row['category']].append(word)
  else:
    words = update[1].split()
    words = [word for word in words if len(word) >= 3]
    if update[0] not in SMART:
      SMART[update[0]] = []
    for word in words:
      if word not in SMART[update[0]]:
        SMART[update[0]].append(word)

def is_it_smart(description):
  """
  Description string as input
  Splits description into separate words, compares each word in the SMART dict,
  Gets the max occurrence key out of another dict, returns the key.
  """
  
  global SMART
  words = description.split()
  words = [word for word in words if len(word) >= 3]
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
  

def change_order_controller(up,id,the_list_o_d):
  order = None
  count = 0
  try:
    # find the current order of cat
    order = [l for l in the_list_o_d if l['category_id'] == id][0]['order']
    count = -1
    for row in [l for l in the_list_o_d if l['order'] != -1]:
      count += 1
    if count == 1:
      # don't bother running refresh on client or server
      return None,None
    else:
      idx = the_list_o_d.index([l for l in the_list_o_d if l['category_id'] == id][0])
      if order == 1 and up:
        # first cat, pressed up: order = count now
        app_tables.categories.get(category_id=id)['order'] = count
        the_list_o_d[idx]['order'] = count
        for row in app_tables.categories.search(q.not_(category_id=id),
                                                q.not_(name="Income"),
                                                q.not_(order=-1)):
          row['order'] -= 1
        for row in [l for l in the_list_o_d if l['order'] != -1] and l['name'] != "Income" and l['category_id'] != id:
          row_idx = the_list_o_d.index(row)
          the_list_o_d[row_idx]['order'] -= 1
      elif order == count and not up:
        # last cat, pressed down: order = 1 now
        app_tables.categories.get(category_id=cat_id)['order'] = 1
        the_list_o_d[idx]['order'] = 1
        for row in app_tables.categories.search(q.not_(category_id=id),
                                                q.not_(name="Income"),
                                                q.not_(order=-1)):
          row['order'] += 1
        for row in [l for l in the_list_o_d if l['order'] != -1 and l['name'] != "Income" and l['category_id'] != id]:
          row_idx = the_list_o_d.index(row)
          the_list_o_d[row_idx]['order'] -= 1
      else:
        # any cat moving into middle of cats
        new = order - 1 if up else order + 1
        app_tables.categories.get(category_id=id)['order'] = new
        the_list_o_d[idx]['order'] = new
        app_tables.categories.get(q.not_(category_id=id),order=new)['order'] = order
        row_idx = the_list_o_d.index([l for l in the_list_o_d if l['order'] == new][0])
        the_list_o_d[row_idx]['order'] = order
    return 'cat',the_list_o_d
  except:
    order = [l for l in the_list_o_d if l['sub_category_id'] == id][0]['order']
    b_to = [l for l in the_list_o_d if l['sub_category_id'] == id][0]['belongs_to']
    count = 0
    for row in [l for l in the_list_o_d if l['order'] != -1 and l['belongs_to'] == b_to]:
      count += 1
    if count == 1:
      # don't bother running refresh on client
      return None,None
    else:
      idx = the_list_o_d.index([l for l in the_list_o_d if l['sub_category_id'] == id][0])
      if order == 0 and up:
        # first sub-cat, pressed up: order = count now
        app_tables.sub_categories.get(sub_category_id=id)['order'] = count - 1
        the_list_o_d[idx]['order'] = count - 1
        for row in app_tables.sub_categories.search(q.not_(sub_category_id=id),
                                                    q.not_(order=-1),belongs_to=b_to):
          row['order'] -= 1
        for row in [l for l in the_list_o_d if l['sub_category_id'] != id and l['order'] != -1 and l['belongs_to'] == b_to]:
          row_idx = the_list_o_d.index(row)
          the_list_o_d[row_idx]['order'] -= 1
      elif order == count - 1 and not up:
        # last cat, pressed down: order = 1 now
        app_tables.sub_categories.get(sub_category_id=id)['order'] = 0
        the_list_o_d[idx]['order'] = 0
        for row in app_tables.sub_categories.search(q.not_(sub_category_id=id),
                                                    q.not_(order=-1),belongs_to=b_to):
          row['order'] += 1
        for row in [l for l in the_list_o_d if l['sub_category_id'] != id and l['order'] != -1 and l['belongs_to'] == b_to]:
          row_idx = the_list_o_d.index(row)
          the_list_o_d[row_idx]['order'] += 1
      else:
        # any cat moving into middle of cats
        new = order - 1 if up else order + 1
        app_tables.sub_categories.get(sub_category_id=id)['order'] = new
        the_list_o_d[idx]['order'] = new
        app_tables.sub_categories.get(q.not_(sub_category_id=id),order=new,belongs_to=b_to)['order'] = order
        row_idx = the_list_o_d.index([l for l in the_list_o_d if l['sub_category_id'] != id and l['order'] == new and l['belongs_to'] == b_to][0])
        the_list_o_d[row_idx] = order
    return b_to,the_list_o_d



