import anvil.files
from anvil.files import data_files
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server

@anvil.server.callable
def order_change(up,cat_id):
  order = None
  count = 0
  try:
    order = app_tables.categories.get(category_id=cat_id)['order']
    count = -1
    for row in app_tables.categories.search():
      count += 1
    if count == 1:
      # don't bother running refresh on client
      return None
    else:
      if order == 1 and up:
        # first cat, pressed up: order = count now
        app_tables.categories.get(category_id=cat_id)['order'] = count
        for row in app_tables.categories.search(q.not_(category_id=cat_id),q.not_(name="Income")):
          row['order'] -= 1
      elif order == count and not up:
        # last cat, pressed down: order = 1 now
        app_tables.categories.get(category_id=cat_id)['order'] = 1
        for row in app_tables.categories.search(q.not_(category_id=cat_id),q.not_(name="Income")):
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
    for row in app_tables.sub_categories.search(belongs_to=b_to):
      count += 1
    if count == 1:
      # don't bother running refresh on client
      return None
    else:
      print(order,up)
      if order == 0 and up:
        # first sub-cat, pressed up: order = count now
        app_tables.sub_categories.get(sub_category_id=cat_id)['order'] = count - 1
        for row in app_tables.sub_categories.search(q.not_(sub_category_id=cat_id),belongs_to=b_to):
          row['order'] -= 1
      elif order == count - 1 and not up:
        # last cat, pressed down: order = 1 now
        app_tables.sub_categories.get(sub_category_id=cat_id)['order'] = 0
        for row in app_tables.sub_categories.search(q.not_(sub_category_id=cat_id),belongs_to=b_to):
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