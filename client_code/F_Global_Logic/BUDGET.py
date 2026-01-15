import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import calendar
from datetime import date, datetime, timedelta
from . import Global


global all_cats
all_cats = []

global all_sub_cats
all_sub_cats = []

global all_budgets
all_budgets = []

all_cats,all_sub_cats,all_budgets = anvil.server.call('load_budget_data')

def get_actual(id,period=None):
  if not period:
    fd,ld = date_me(False)
  else:
    fd,ld = period[0],period[1]
  trans_list = [
    t for t in Global.TRANSACTIONS if t['date'] >= fd and t['date'] <= ld and t['category'] == id
  ]
  a = 0.0
  for t in trans_list:
    a += t['amount']
  return a/100

def is_income(b_to):
  global all_cats
  return [c for c in all_cats if c['name'] == 'Income'][0]['category_id'] == b_to

def date_me(dash):
  m,y = None,None
  if dash:
    m = date.today().month
    y = date.today().year
    days_in_month = calendar.monthrange(y, m)[1]
    return date(y,m,1),date(y,m,days_in_month)
  else:
    p = Global.PERIOD
    if p[0] + p[1] == 0:
      #we have a custom
      return Global.CUSTOM[0],Global.CUSTOM[1]
    else:
      m = p[0]
      y = p[1]
      days_in_month = calendar.monthrange(y, m)[1]
      return date(y,m,1),date(y,m,days_in_month)

def roll_over_calc(id):
  """
    Takes a sub cat and works out:
    1. if roll-over budget: accumulation as a total amount to be returned.
    2. if not roll-over, returns current period (as per Global) budget, or 0 if none saved.
    3. Works from main form or from sub-cat. 
    """
  global all_sub_cats, all_budgets
  try:
    sub_cat = [s for s in all_sub_cats if s['sub_category_id'] == id][0]
  except:
    print("BUDGET line 67:",app_tables.sub_categories.get(sub_category_id=id)['name'])
  if sub_cat['roll_over']:
    # make list of dates to check
    date_list = roll_date_list(fd=sub_cat['roll_over_date']) 
    b = 0 
    for period in date_list:
      a = 0
      try:
        # this amount is int (ie x 100)
        b += [budget for budget in all_budgets if budget['belongs_to'] == id and budget['period'] == period[0]][0]['budget_amount']
      except:
        b += 0
        # this amount is actual float
      a = get_actual(id=id,period=period)*100
      #MAGIC
      if b < 0: #we have budget, either this month or cumulative
        if b < a: # we have leftover
          b = b - a
        else: #nothing left over, overspent whatever - goes to zero
          b = 0
      elif b > 0: #we have an income
        pass # what do we actually do here???
        # print("...Roll-over Budget for next month: {bud}.\n________________________".format(bud=b))

    return b + (get_actual(id=id,period=date_list[-1])*100)
  else:
    try:
      fd = date(Global.PERIOD[1],Global.PERIOD[0],1)
      return [budget for budget in all_budgets if budget['period'] == fd and budget['belongs_to'] == sub_cat['sub_category_id']][0]['budget_amount']
    except:
      return 0

def roll_date_list(fd):
  date_list = []
  ld = date(Global.PERIOD[1],Global.PERIOD[0],1)
  cd = fd
  while cd <= ld:
    # Format the string: %B is full month name, %y is two-digit year
    d = calendar.monthrange(cd.year,cd.month)[1]
    date_list.append((cd,date(cd.year,cd.month,d)))
    # Move to the first day of the next month
    next = cd.month + 1
    try:
      #If below doesn't work, we've gone to next year
      cd = date(cd.year, next,1)
    except:
      #go to next year
      next = cd.year + 1
      cd = date(next,1,1)
  return date_list

def neg_pos(amount,b_to):
  global all_cats
  i = True if [c for c in all_cats if c['category_id'] == b_to][0]['name'] == "Income" else False
  if not amount:
    return 0
  elif i and amount < 0:
    amount = -1 * amount
  elif not i and amount > 0:
    amount = -1 * amount
  return amount

def get_max_order(id='',cat=True):
  global all_cats, all_sub_cats
  if cat:
    #main category order search
    return max(all_cats, key=lambda x: x["order"])['order'] + 1
  else:
    #sub category order search
    if len([s for s in all_sub_cats if s['belongs_to'] == id]) > 0:
      return max([s for s in all_sub_cats if s['belongs_to'] == id], 
                         key=lambda x: x["order"])['order'] + 1
    else:
      return 0

def update_budget(steer,package):
  """
  Global update handler, both local and server data
  __steer___________package__
  amount            {'amount':0,'period':date_obj,'id':''}
  add_cat           result (full main cat dict)
  """
  global all_budgets,all_cats,all_sub_cats
  if steer == "amount":
    # Update an amount for period in the budget
    if len([b for b in all_budgets if b['period'] == package['period'] and b['belongs_to'] == package['id']]) > 0:
      [b for b in all_budgets if b['period'] == package['period'] and b['belongs_to'] == package['id']][0]['amount'] = package['amount']
    else:
      all_budgets.append({'belongs_to':package['id'],
                          'budget_amount':package['amount'],
                          'period':package['period'],
                          'notes':None})
    try:
      app_tables.budgets.get(period=package['period'],
                             belongs_to=package['id'])['budget_amount'] = package['amount']
    except:
      app_tables.budgets.add_row(belongs_to=package['id'],
                                 period=package['period'],budget_amount=package['amount'])
  elif steer == 'add_cat':
    package['order'] = get_max_order()
    all_cats.append(package)
    app_tables.categories.add_row(**package)
  elif steer == 'add_sub_cat':
    #first find max order
    package['order'] = get_max_order(id=package['belongs_to'],cat=False)
    all_sub_cats.append(package)
    app_tables.sub_categories.add_row(**package)
    
  
  