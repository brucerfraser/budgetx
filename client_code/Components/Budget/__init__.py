from ._anvil_designer import BudgetTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from .Category_holder import Category_holder


class Budget(BudgetTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    inc_d = {}
    self.category_right = ""
    self.period_right = None
    for inc in app_tables.categories.search(name='Income'):
      inc_d = dict(inc)
    self.card_2.add_component(Category_holder(item=inc_d))
    # self.income_holder.my_identity = app_tables.categories.search(name='Income')
    cats = []
    for cat in app_tables.categories.search(tables.order_by('order')):
      cat_d = {}
      cat_d = dict(cat)
      if cat_d['name'] != 'Income':
        cats.append(cat_d)
  
    self.expense_categories.items = cats
    

  def add_category_click(self, **event_args):
    from ...Pop_menus.work_a_category import work_a_category
    c = work_a_category()
    result = alert(c,title="Add a category",buttons=[],large=True)
    # print(result)
    if result:
      cat_d = {}
      app_tables.categories.add_row(**result)
      for cat in app_tables.categories.search(q.not_(name='Income')):
        cat_d = dict(cat)
        self.card_expenses.add_component(Category_holder(my_identity=cat_d))
    
  def test_me(self, **event_args):
    print("works!")

  def load_category_right(self,cat,period,big_cat=False, **event_args):
    self.category_right,self.period_right = cat,period
    if not big_cat:
      nts = None
      try:
        nts = app_tables.budgets.get(period=period,
                              belongs_to=cat)['notes']
      except Exception as e:
        print("error:",e)
        
      sc = app_tables.sub_categories.get(sub_category_id=cat)['name']
      c_id = app_tables.sub_categories.get(sub_category_id=cat)['belongs_to']
      c = app_tables.categories.get(category_id=c_id)['name']
      self.label_2.text = c + " - " + sc
      self.notes.text = nts
      self.column_panel_2.visible = True
    else:
      self.label_2.text = app_tables.categories.get(category_id=self.category_right)['name']
      self.column_panel_2.visible = False
      

  def reset_sub_categories(self,cat,**event_args):
    for category in self.expense_categories.get_components():
      # print(category)
      if category.link_1.icon == "fa:angle-down":
        #sub-cates are open
        for sub_cat in category.repeating_panel_1.get_components():
          if sub_cat.item["sub_category_id"] != cat:
            sub_cat.edit_column_panel.visible = False
            sub_cat.link_1.visible = True
        

  def update_notes(self, **event_args):
    app_tables.budgets.get(belongs_to=self.category_right,
                           period=self.period_right)['notes'] = self.notes.text
    
    
