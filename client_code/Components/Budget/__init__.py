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
    #get data
    # start_time = datetime.now()
    # print("local start:",start_time)
    """
    METHOD SERVER
    """
    self.all_trans, self.all_cats, self.all_sub_cats, self.all_budgets = anvil.server.call('load_budget_data')
    # end_time = datetime.now()
    # print("local duration:",end_time - start_time)
    
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
    METHOD SERVER
    """
    # for inc in app_tables.categories.search(name='Income'):
    #   inc_d = dict(inc)
    # self.card_2.add_component(Category_holder(item=inc_d))
    # for cat in app_tables.categories.search(tables.order_by('order')):
    #   cat_d = {}
    #   cat_d = dict(cat)
    #   if cat_d['name'] != 'Income' and cat_d['order'] != -1:
    #     cats.append(cat_d)
    """
    END local load methods
    """
    self.expense_categories.items = cats
    # real_end = datetime.now()
    # print("local load duration:",real_end - end_time)
    
    
  def load_me(self,dash,**event_args):
    # get date
    fd,ld = self.date_me(dash)
    # go through cats and update any open sub_cats
    

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
        self.roll_over.checked = app_tables.sub_categories.get(sub_category_id=self.category_right)['roll_over']
        if self.roll_over.checked:
          r_o_d = app_tables.sub_categories.get(sub_category_id=self.category_right)['roll_over_date']
          if r_o_d:
            m = r_o_d.month
            y = r_o_d.year
            self.drop_down_1.selected_value = (m,y)
          self.drop_down_1.visible = True
      else:
        self.roll_over.enabled,self.roll_over.checked = False,False
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
    else:
      self.drop_down_1.visible = False
      app_tables.sub_categories.get(sub_category_id=self.category_right)['roll_over_date'] = None

  def drop_down_1_change(self, **event_args):
    r_o_d = date(self.drop_down_1.selected_value[1],self.drop_down_1.selected_value[0],1)
    app_tables.sub_categories.get(sub_category_id=self.category_right)['roll_over_date'] = r_o_d

  

  
            
          
          
    
