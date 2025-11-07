import anvil.files
from anvil.files import data_files
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server
from datetime import datetime,date

@anvil.server.callable
def order_change(up,cat_id):
  order = None
  count = 0
  try:
    order = app_tables.categories.get(category_id=cat_id)['order']
    count = -1
    for row in app_tables.categories.search(q.not_(order=-1)):
      count += 1
    if count == 1:
      # don't bother running refresh on client
      return None
    else:
      if order == 1 and up:
        # first cat, pressed up: order = count now
        app_tables.categories.get(category_id=cat_id)['order'] = count
        for row in app_tables.categories.search(q.not_(category_id=cat_id),
                                                q.not_(name="Income"),
                                               q.not_(order=-1)):
          row['order'] -= 1
      elif order == count and not up:
        # last cat, pressed down: order = 1 now
        app_tables.categories.get(category_id=cat_id)['order'] = 1
        for row in app_tables.categories.search(q.not_(category_id=cat_id),
                                                q.not_(name="Income"),
                                               q.not_(order=-1)):
          row['order'] += 1
      else:
        # any cat moving into middle of cats
        new = order - 1 if up else order + 1
        app_tables.categories.get(category_id=cat_id)['order'] = new
        app_tables.categories.get(q.not_(category_id=cat_id),order=new)['order'] = order
    return 'cat'
  except:
    order = app_tables.sub_categories.get(sub_category_id=cat_id)['order']
    b_to = app_tables.sub_categories.get(sub_category_id=cat_id)['belongs_to']
    count = 0
    for row in app_tables.sub_categories.search(q.not_(order=-1),belongs_to=b_to):
      count += 1
    if count == 1:
      # don't bother running refresh on client
      return None
    else:
      # print(order,up)
      if order == 0 and up:
        # first sub-cat, pressed up: order = count now
        app_tables.sub_categories.get(sub_category_id=cat_id)['order'] = count - 1
        for row in app_tables.sub_categories.search(q.not_(sub_category_id=cat_id),
                                                    q.not_(order=-1),belongs_to=b_to):
          row['order'] -= 1
      elif order == count - 1 and not up:
        # last cat, pressed down: order = 1 now
        app_tables.sub_categories.get(sub_category_id=cat_id)['order'] = 0
        for row in app_tables.sub_categories.search(q.not_(sub_category_id=cat_id),
                                                    q.not_(order=-1),belongs_to=b_to):
          row['order'] += 1
      else:
        # any cat moving into middle of cats
        new = order - 1 if up else order + 1
        app_tables.sub_categories.get(sub_category_id=cat_id)['order'] = new
        app_tables.sub_categories.get(q.not_(sub_category_id=cat_id),order=new,belongs_to=b_to)['order'] = order
    return b_to

@anvil.server.callable
def name_change(cat_id,new_name):
  try:
    app_tables.categories.get(category_id=cat_id)['name'] = new_name
    return 'cat'
  except:
    app_tables.sub_categories.get(sub_category_id=cat_id)['name'] = new_name
    b_to = app_tables.sub_categories.get(sub_category_id=cat_id)['belongs_to']
    return b_to

@anvil.server.callable
def archive(b_to,cat_id):
  if b_to == '':
    ord = app_tables.categories.get(category_id=cat_id)['order']
    app_tables.categories.get(category_id=cat_id)['order'] = -1
    for cat in app_tables.categories.search(order=q.greater_than(ord)):
      cat['order'] -= 1
  else:
    ord = app_tables.sub_categories.get(sub_category_id=cat_id)['order']
    app_tables.sub_categories.get(sub_category_id=cat_id)['order'] = -1
    for cat in app_tables.sub_categories.search(order=q.greater_than(ord),
                                               belongs_to=b_to):
      cat['order'] -= 1

@anvil.server.callable
def load_budget_data():
  # if new month and no entries, copy prev month entries
  today = date.today()
  period = date(today.year,today.month,1)
  if len(app_tables.budgets.search(period=period)) == 0:
    # we must copy
    m = today.month - 1
    y = today.year
    if m == 0:
      m = 12
      y -= 1
    last_month = date(y,m,1)
    for row in app_tables.budgets.search(period=last_month):
      app_tables.budgets.add_row(period=period,budget_amount=row['budget_amount'],belongs_to=row['belongs_to'])
  
  t = app_tables.transactions.search()
  c = app_tables.categories.search()
  s = app_tables.sub_categories.search()
  b = app_tables.budgets.search()
  all_trans, all_cats, all_sub_cats, all_budgets = [],[],[],[]
  for row in t:
    all_trans.append(dict(row))
  for row in c:
    all_cats.append(dict(row))
  for row in s:
    all_sub_cats.append(dict(row))
  for row in b:
    all_budgets.append(dict(row))
  
  return all_trans, all_cats, all_sub_cats, all_budgets