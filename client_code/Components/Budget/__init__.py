from ._anvil_designer import BudgetTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from .Category_holder import Category_holder
import calendar
from datetime import date, datetime, timedelta
from ... import Global


class Budget(BudgetTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    
    self.category_right = ""
    self.period_right = None
    self.cat_sub_cat = None
    self.which_form = 'budget'
    self.drop_down_1.selected_value = None
    """
    METHOD SERVER
    """
    self.all_cats, self.all_sub_cats, self.all_budgets = anvil.server.call('load_budget_data')
    
    inc_d = {}
    cats = []
    """
    METHOD LOCAL with backup
    """
    try:
      inc_d = [c for c in self.all_cats if c['name'] == "Income"][0]
    except Exception as e:
      for inc in app_tables.categories.search(name='Income'):
        inc_d = dict(inc)
      print("Budget form: Income backup table search use because of \n",e)
    self.card_2.add_component(Category_holder(item=inc_d))
    try:
      cats = sorted([c for c in self.all_cats if not c['name'] == "Income" and not c['order'] == -1],
                    key = lambda x: x['order'])
    except Exception as e:
      for cat in app_tables.categories.search(tables.order_by('order')):
        cat_d = {}
        cat_d = dict(cat)
        if cat_d['name'] != 'Income' and cat_d['order'] != -1:
          cats.append(cat_d)
      print("Budget form: Expesnse backup table search use because of \n",e)
    """
    END local load methods
    """
    self.expense_categories.items = cats
    self.update_numbers()

  def form_show(self,**event_args):
    self.load_me(False)

  def smart_cat_update(self,**event_args):
    Global.Transactions_Form.smart_cat_update()

  def load_me(self,dash,**event_args):
    # this happens after date selection changes at top
    # get date
    fd,ld = self.date_me(dash)
    self.month_label.text = fd.strftime("%B %Y")
    
    # go through cats and update any open sub_cats
    self.update_numbers()
    for inc in self.card_2.get_components()[-1].repeating_panel_1.get_components():
      inc.form_show()
    for category in self.expense_categories.get_components():
      if category.link_1.icon == "fa:angle-down":
        #sub-cats are open
        for sub_cat in category.repeating_panel_1.get_components():
          sub_cat.form_show()
    
  def get_actual(self,id,period=None,**event_args):
    if not period:
      fd,ld = self.date_me(False)
    else:
      fd,ld = period[0],period[1]
    trans_list = [
      t for t in Global.Transactions_Form.all_transactions if t['date'] >= fd and t['date'] <= ld and t['category'] == id
    ]
    a = 0.0
    for t in trans_list:
      a += t['amount']
    return a/100

  def neg_pos(self,amount,b_to,**event_args):
    i = True if [c for c in self.all_cats if c['category_id'] == b_to][0]['name'] == "Income" else False
    if i and amount < 0:
      amount = -1 * amount
    elif not i and amount >0:
      amount = -1 * amount
    return amount

  def is_income(self,b_to,**event_args):
    return [c for c in self.all_cats if c['name'] == 'Income'][0]['category_id'] == b_to

  def date_me(self,dash,**event_args):
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
  
  def add_category_click(self, **event_args):
    from ...Pop_menus.work_a_category import work_a_category
    c = work_a_category()
    result = alert(c,title="Add a category",buttons=[],large=True)
    # print(result)
    if result:
      # we need an order first
      print(max(self.all_cats, key=lambda x: x["order"]))
      result['order'] = max(self.all_cats, key=lambda x: x["order"])['order'] + 1
      app_tables.categories.add_row(**result)
      self.all_cats.append(result)
      self.expense_categories.items = sorted([c for c in self.all_cats if not c['name'] == "Income" and not c['order'] == -1],
                                             key = lambda x: x['order'])
      # for cat in app_tables.categories.search(q.not_(name='Income')):
      #   cat_d = dict(cat)
      #   self.card_expenses.add_component(Category_holder(my_identity=cat_d))

  
    
  def get_me_max_order(self,res, **event_args):
    if len([s for s in self.all_sub_cats if s['belongs_to'] == res['belongs_to']]) > 0:
      res['order'] = max([s for s in self.all_sub_cats if s['belongs_to'] == res['belongs_to']], 
                        key=lambda x: x["order"])['order'] + 1
    else:
      res['order'] = 0
    self.all_sub_cats.append(res)
    return res


  def load_category_right(self,cat,period,big_cat=False,b_to='', **event_args):
    self.category_right,self.period_right = cat,period
    self.cat_sub_cat = b_to
    if not big_cat:
      nts = None
      try:
        nts = app_tables.budgets.get(period=period,
                              belongs_to=cat)['notes']
      except Exception as e:
        print("error:",e)
        
      sc = app_tables.sub_categories.get(sub_category_id=cat)['name']
      c = app_tables.categories.get(category_id=b_to)['name']
      self.label_2.text = c + " - " + sc
      self.notes.text = nts
      self.column_panel_2.visible = True
      self.edit_card.visible = True
      self.edit_name.text = app_tables.sub_categories.get(sub_category_id=self.category_right)['name']
    else:
      self.label_2.text = app_tables.categories.get(category_id=self.category_right)['name']
      self.column_panel_2.visible = False
      if not self.label_2.text == "Income":
        self.edit_card.visible = True
        self.edit_name.text = app_tables.categories.get(category_id=self.category_right)['name']
      else:
        self.edit_card.visible = False
    self.edit_details.visible,self.edit_switch.checked,self.drop_down_1.visible = False,False,False
    self.drop_down_1.selected_value = None
    self.close_cat.visible = True
      

  def reset_sub_categories(self,cat,**event_args):
    for category in self.expense_categories.get_components():
      # print(category)
      if category.link_1.icon == "fa:angle-down":
        #sub-cats are open
        for sub_cat in category.repeating_panel_1.get_components():
          if sub_cat.item["sub_category_id"] != cat:
            sub_cat.edit_column_panel.visible = False
            sub_cat.link_1.visible = True
    for inc in self.card_2.get_components()[-1].repeating_panel_1.get_components():
      # print(inc.item)
      if inc.item["sub_category_id"] != cat:
        inc.edit_column_panel.visible = False
        inc.link_1.visible = True
        

  def update_notes(self, **event_args):
    if not self.notes.text == '':
      try:
        app_tables.budgets.get(belongs_to=self.category_right,
                            period=self.period_right)['notes'] = self.notes.text
      except:
        app_tables.budgets.add_row(belongs_to=self.category_right,
                                   period=self.period_right,budget_amount=0,
                                  notes=self.notes.text)

  def edit_switch_change(self, **event_args):
    if self.edit_switch.checked:
      if self.cat_sub_cat:
        self.roll_over.enabled = True
        self.drop_down_1.items = self.date_picker_bruce_1.drop_down_1.items
        self.roll_over.checked = [s for s in self.all_sub_cats if s['sub_category_id'] == self.category_right][0]['roll_over']
        # self.roll_over.checked = app_tables.sub_categories.get(sub_category_id=self.category_right)['roll_over']
        if self.roll_over.checked:
          r_o_d = [s for s in self.all_sub_cats if s['sub_category_id'] == self.category_right][0]['roll_over_date']
          if r_o_d:
            m = r_o_d.month
            y = r_o_d.year
            self.drop_down_1.selected_value = (m,y)
          self.drop_down_1.visible = True
        self.colours.visible = False
      else:
        self.roll_over.enabled,self.roll_over.checked = False,False
        self.bg_colour.set_color([c for c in self.all_cats if c['category_id'] == self.category_right][0]['colour_back'])
        self.text_colour.set_color([c for c in self.all_cats if c['category_id'] == self.category_right][0]['colour_text'])
        self.colours.visible = True
      self.edit_details.visible = True
      self.edit_name.select()
    else:
      self.edit_details.visible = False

  def change_order(self, **event_args):
    up = None
    if event_args['sender'].icon == "fa:angle-up":
      up = True
    else:
      up = False
      
    ret = anvil.server.call('order_change',up=up,cat_id=self.category_right)
      #run a refresh of categories
      # ret = 'cat' means it's a category, 'uy2346iuy...' = sub_category belongs_to, None means do noting
    if ret == 'cat':
      cats = []
      for cat in app_tables.categories.search(q.not_(order=-1),tables.order_by('order')):
        cat_d = {}
        cat_d = dict(cat)
        if cat_d['name'] != 'Income':
          cats.append(cat_d)
      open = False
      for category in self.expense_categories.get_components():
        #find if opened or not:
        
        if category.link_1.icon == "fa:angle-down" and category.item['category_id'] == self.category_right:
          open = True
      self.expense_categories.items = []
      self.expense_categories.items = cats
      if open:
        for category in self.expense_categories.get_components():
          if category.item['category_id'] == self.category_right:
            category.link_1_click()
    else:
      #ret is belongs_to. Find object and reload.
      for category in self.expense_categories.get_components():
        if category.item['category_id'] == ret:
          category.refresh_sub_cats()
          for sub_cat in category.repeating_panel_1.get_components():
            if sub_cat.item['sub_category_id'] == self.category_right:
              sub_cat.link_1_click()
              break

  def name_change(self, **event_args):
    ret = anvil.server.call('name_change',cat_id=self.category_right,
                     new_name=self.edit_name.text)
    

  def live_name_update(self, **event_args):
    if self.cat_sub_cat == '':
      #update the category
      for category in self.expense_categories.get_components():
        if category.item['category_id'] == self.category_right:
          category.link_1.text = self.edit_name.text
          break
    else:
      #update the sub_category
      for category in self.expense_categories.get_components():
        if category.item['category_id'] == self.cat_sub_cat:
          for sub_cat in category.repeating_panel_1.get_components():
            if sub_cat.item['sub_category_id'] == self.category_right:
              sub_cat.sub_cat_name_edit.text = self.edit_name.text
              break

  def close_cat_click(self, **event_args):
    self.reset_sub_categories(cat='')
    self.close_cat.visible = False
    self.label_2.text = ""
    self.column_panel_2.visible = False
    self.edit_card.visible = False

  def archive_click(self, **event_args):
    if alert("Archive {c}? You can undo this in settings later.".format(c=self.label_2.text),
              title="Archive a category",buttons=[("Cancel",False),("Archive",True)]):
      anvil.server.call('archive',b_to=self.cat_sub_cat,cat_id=self.category_right)
      self.close_cat_click()
      #run a refresh of categories
      # use cat_sub_cat for knowing if cat or sub_cat
      if self.cat_sub_cat == '':
        cats = []
        for cat in app_tables.categories.search(q.not_(order=-1),tables.order_by('order')):
          cat_d = {}
          cat_d = dict(cat)
          if cat_d['name'] != 'Income':
            cats.append(cat_d)
        open = False
        for category in self.expense_categories.get_components():
          #find if opened or not:
          if category.link_1.icon == "fa:angle-down" and category.item['category_id'] == self.category_right:
            open = True
        self.expense_categories.items = []
        self.expense_categories.items = cats
        if open:
          for category in self.expense_categories.get_components():
            if category.item['category_id'] == self.category_right:
              category.link_1_click()
      else:
        # Sub_cat. Find it and reload.
        for category in self.expense_categories.get_components():
          if category.item['category_id'] == self.cat_sub_cat:
            category.refresh_sub_cats()

  def roll_over_change(self, **event_args):
    app_tables.sub_categories.get(sub_category_id=self.category_right)['roll_over'] = self.roll_over.checked
    if self.roll_over.checked:
      self.drop_down_1.visible = True
      self.drop_down_1.selected_value = None
    else:
      self.drop_down_1.visible = False
      app_tables.sub_categories.get(sub_category_id=self.category_right)['roll_over_date'] = None

  def drop_down_1_change(self, **event_args):
    r_o_d = date(self.drop_down_1.selected_value[1],self.drop_down_1.selected_value[0],1)
    app_tables.sub_categories.get(sub_category_id=self.category_right)['roll_over_date'] = r_o_d

  def update_a_budget(self,amount,period,id,**event_args):
    try:
      i = self.all_budgets.index([b for b in self.all_budgets if b['period'] == period and b['belongs_to'] == id][0])
      self.all_budgets[i]['budget_amount'] = amount
    except:
      self.all_budgets.append({'belongs_to':id,
                              'budget_amount':amount,
                              'period':period,
                              'notes':None})
  
  def update_numbers(self,**event_args):
    """
    Called when needed - budget updated etc
    1. Goes through each cat holder and works out:
      a. Actual spent/earned
      b. Total budget
      c. Adjusts total budget for any roll-overs
      d. Updates category prog bar
    """
    fd,ld = self.date_me(False)
    cat = self.card_2.get_components()[-1]
    a,b = 0,0
    income_budget,income_actual = 0,0
    for sub_cat in [s for s in self.all_sub_cats if s['belongs_to'] == cat.item['category_id']]:
      a += self.get_actual(id=sub_cat['sub_category_id'])
      try:
        b += [budget for budget in self.all_budgets if budget['period'] == fd and budget['belongs_to'] == sub_cat['sub_category_id']][0]['budget_amount']
        # roll-over function. Nah - not sure what to do with roll_over on income
      except:
        b += 0
    income_actual += a
    income_budget += b
    
    self.update_number_writer(b/100,a,cat)

    expense_budget,expense_actual = 0,0
    for cat in self.expense_categories.get_components():
      a,b = 0,0
      for sub_cat in [s for s in self.all_sub_cats if s['belongs_to'] == cat.item['category_id']]:
        a += self.get_actual(id=sub_cat['sub_category_id'])
        try:
          """
          We go straight to roll-over function
          this function checks if it's roll-over and calcs the whole line. if it is not RO,
          just returns current period budget.
          """
          b += self.roll_over_calc(id=sub_cat['sub_category_id'])
        except Exception as e:
          b += 0
          print(e,"\non line 372 of Budget form (roll_over_calc function error)")
      expense_actual += a
      expense_budget += b
      self.update_number_writer(b/100,a,cat)
    self.update_rh_header(income_actual,income_budget,expense_actual,expense_budget)
    self.update_cat_warning()

  def update_cat_warning(self,**event_args):
    fd,ld = self.date_me(False)
    un_cat = len([t for t in Global.Transactions_Form.all_transactions if t['date'] >= fd and t['date'] <= ld and t['category'] == None])
    warning = "{n} uncategorised transactions for this month".format(n=un_cat)
    self.label_uncat.text = "All transactions categorised!" if un_cat == 0 else warning
    self.label_uncat.foreground = 'theme:Amount Negative' if un_cat > 0 else 'theme:Primary'
    self.fix_it.foreground = 'theme:Amount Negative' if un_cat > 0 else 'theme:Primary'
    self.fix_it.enabled = True if un_cat > 0 else False

  def update_rh_header(self,i_a,i_b,e_a,e_b,**event_args):
    e_v = e_a - (e_b/100)
    i_v = i_a - (i_b/100)
    self.budget_in.text = "(R{b:,.2f})".format(b=-i_b/100) if i_b < 0 else "R{b:,.2f}".format(b=i_b/100)
    self.variance_in.text = "(R{b:,.2f})".format(b=-i_v) if i_v < 0 else "R{b:,.2f}".format(b=i_v)
    self.actual_in.text = "(R{b:,.2f})".format(b=-i_a) if i_a < 0 else "R{b:,.2f}".format(b=i_a)
    self.variance_in.foreground = 'theme:Amount Negative' if i_v < 0 else 'theme:Primary'
    
    self.budget_out.text = "(R{b:,.2f})".format(b=-e_b/100) if e_b < 0 else "R{b:,.2f}".format(b=e_b/100)
    self.variance_out.text = "(R{b:,.2f})".format(b=-e_v) if e_v < 0 else "R{b:,.2f}".format(b=e_v)
    self.actual_out.text = "(R{b:,.2f})".format(b=-e_a) if e_a < 0 else "R{b:,.2f}".format(b=e_a)
    self.budget_out.foreground = 'theme:Amount Negative' if e_b < 0 else 'theme:Primary'
    self.variance_out.foreground = 'theme:Amount Negative' if e_v < 0 else 'theme:Primary'
    self.actual_out.foreground = 'theme:Amount Negative' if e_a < 0 else 'theme:Primary'
    
     
  def update_number_writer(self,b,a,comp,**event_args):
    """
    Writes a Category holders header bar
    comp is the actual instance of the category bar
    a is the total actual spent/earned for the cat
    b is the total budgeted for the cat
    """
    comp.actual.text = "(R {actual:.2f})".format(actual=-a) if a < 0 else "R {actual:.2f}".format(actual=a)
    comp.budget.text = "({b:.2f})".format(b=-b) if b < 0 else "{b:.2f}".format(b=b)
    #income bars are different
    maxi,min,v = 0,0,0
    if self.is_income(comp.item['category_id']):
      comp.progress_bar_1.min_value = 0
      comp.progress_bar_1.max_value = max(b,a)
      comp.progress_bar_1.value = a
    else:
      # if still have budget, set a standard zero point at 25% of the bar.
      # if budget exceeded, set equal min point to max, zero halfway
      # if spend exceeds double of budget, set zero at 75%
      if a >= b and b != 0:
        maxi = -b
        min = b/4
        v = -(b-a)
      elif a < b and a >= 2*b:
        maxi = -b
        min = b
        v = a - b
      elif a < b and a < 2*b:
        maxi = -a/4
        min = a
        v = a
      elif a == 0 and b == 0:
        maxi = 10.0
        min = -10.0
        v = 0.0
      else:
        maxi = 10.0
        min = -10.0
        v = 0.0
      comp.progress_bar_1.min_value = min
      comp.progress_bar_1.max_value = maxi
      comp.progress_bar_1.value = v
    
  def roll_over_calc(self,id,**event_args):
    """
    Takes a sub cat and works out:
    1. if roll-over budget: accumulation as a total amount to be returned.
    2. if not roll-over, returns current period (as per Global) budget, or 0 if none saved.
    3. Works from main form or from sub-cat. 
    """
    sub_cat = [s for s in self.all_sub_cats if s['sub_category_id'] == id][0]
    if sub_cat['roll_over']:
      # make list of dates to check
      date_list = self.roll_date_list(fd=sub_cat['roll_over_date'])
      b = 0 
      for period in date_list:
        a = 0
        try:
          # this amount is int (ie x 100)
          b += [budget for budget in self.all_budgets if budget['belongs_to'] == id and budget['period'] == period[0]][0]['budget_amount']
        except:
          b += 0
        # this amount is actual float
        a = self.get_actual(id=id,period=period)*100
        #MAGIC
        if b < 0: #we have budget, either this month or cumulative
          if b < a: # we have leftover
            b = b - a
          else: #nothing left over, overspent whatever - goes to zero
            b = 0
        elif b > 0: #we have an income
          pass # what do we actually do here???
        # print("...Roll-over Budget for next month: {bud}.\n________________________".format(bud=b))
      
      return b + (self.get_actual(id=id,period=date_list[-1])*100)
    else:
      try:
        fd = date(Global.PERIOD[1],Global.PERIOD[0],1)
        return [budget for budget in self.all_budgets if budget['period'] == fd and budget['belongs_to'] == sub_cat['sub_category_id']][0]['budget_amount']
      except:
        return 0
            
          
  def roll_date_list(self,fd,**event_args):
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

  def a_colour_change(self, **event_args):
    for cat in self.expense_categories.get_components():
      if cat.item['category_id'] == self.category_right:
        #we have our category
        new = {'colour_text':self.text_colour.get_color(),
              'colour_back':self.bg_colour.get_color()}
        app_tables.categories.get(category_id=self.category_right).update(**new)
        cat.item['colour_back'] = new['colour_back']
        cat.item['colour_text'] = new['colour_text']
        cat.form_show()
        i = self.all_cats.index([c for c in self.all_cats if c['category_id'] == self.category_right][0])
        self.all_cats[i]['colour_back'] = new['colour_back']
        self.all_cats[i]['colour_text'] = new['colour_text']
        break
    
