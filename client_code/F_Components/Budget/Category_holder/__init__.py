from ._anvil_designer import Category_holderTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from datetime import date
from ....F_Global_Logic import BUDGET


class Category_holder(Category_holderTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    
  def link_2_click(self, **event_args):
    from ....F_PopUps.work_a_category import work_a_category
    c = work_a_category(cat=False)
    result = alert(c,title="Add a sub-category to {cat}".format(cat=self.item['name']),
                  buttons=[],large=True)
    if result:
      result['belongs_to'] = self.item['category_id']
      print(self.item['category_id'])
      for a in ['colour_back','colour_text']:
        del result[a]
      # add sub_cat with global update function
      BUDGET.update_budget('add_sub_cat',result)
      if self.link_1.icon == 'fa:angle-down':
        self.repeating_panel_1.items = sorted([sc for sc in BUDGET.all_sub_cats if sc['belongs_to'] == self.item['category_id'] and sc['order'] >= 0],
                                              key=lambda x: x['order'])
        odd = False
        for sc in self.repeating_panel_1.get_components():
          if odd:
            sc.background = 'grey'
          odd = not odd

  def refresh_sub_cats(self, **event_args):
    frm = get_open_form().content_panel.get_components()[0].edit_budget
    edit, edit_id = False,None
    for sc in self.repeating_panel_1.get_components():
      edit = True if sc.item['sub_category_id'] == frm.category else False
      if edit:
        edit_id = frm.category
        break
    item_list = []
    for line in BUDGET.all_sub_cats:
      try:
        if line['order'] >= 0:
          if line['belongs_to'] == self.item['category_id']:
            item_list.append(line)
      except Exception as e:
        print("cat holder line 55",line,e)
    item_list = sorted(item_list,key = lambda i: i['order'])
    self.repeating_panel_1.items = item_list
    odd = False
    for sc in self.repeating_panel_1.get_components():
      if odd:
        sc.background = 'grey'
      odd = not odd
    
  def link_1_click(self, **event_args):
    if self.link_1.icon == 'fa:angle-right':
      self.repeating_panel_1.items = sorted([sc for sc in BUDGET.all_sub_cats if sc['belongs_to'] == self.item['category_id'] and sc['order'] >= 0],
                                            key=lambda x: x['order'])
      self.link_1.icon = 'fa:angle-down'
      self.repeating_panel_1.visible = True
    else:
      self.link_1.icon = 'fa:angle-right'
      self.repeating_panel_1.visible = False

    # Send detail to RH Panel
    frame = anvil.get_open_form()
    budg = frame.content_panel.get_components()[0]
    today = date.today()
    period = date(today.year, today.month, 1)
    budg.edit_budget.load_for_edit(self.item['category_id'],period,True)
    # Make all other sub_cats clickable again (links vis, edit invis)
    budg.reset_sub_categories("") #empty sub-category because a catgeory has been clicked, not a sub-cat

  def calculate_me(self,info,**event_args):
    pass

  def form_show(self, **event_args):
    for obj in [self.name_label,self.budget,self.actual]:
      obj.foreground = self.item['colour_text']
      self.link_1.background = self.item['colour_back']


