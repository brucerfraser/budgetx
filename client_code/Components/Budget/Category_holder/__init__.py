from ._anvil_designer import Category_holderTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from datetime import date


class Category_holder(Category_holderTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    

  def link_2_click(self, **event_args):
    from ....Pop_menus.work_a_category import work_a_category
    c = work_a_category(cat=False)
    result = alert(c,title="Add a sub-category to {cat}".format(cat=self.item['name']),
                  buttons=[],large=True)
    if result:
      result['belongs_to'] = self.item['category_id']
      for a in ['colour_back','colour_text']:
        del result[a]
      # find the max order in this category, add to result, add to all_sub_cats in main form
      frm = get_open_form().content_panel.get_components()[0]
      result = frm.get_me_max_order(res=result)
      app_tables.sub_categories.add_row(**result)
      # both app_tables and all_sub_cats updated
      if self.link_1.icon == 'fa:angle-down':
        self.repeating_panel_1.items = app_tables.sub_categories.search(q.not_(order=-1),tables.order_by("order"),
                                                                        belongs_to=self.item['category_id'])
        odd = False
        for sc in self.repeating_panel_1.get_components():
          if odd:
            sc.background = 'grey'
          odd = not odd

  def refresh_sub_cats(self, **event_args):
    self.repeating_panel_1.items = app_tables.sub_categories.search(q.not_(order=-1),
                                                                    tables.order_by('order'),
                                                                    belongs_to=self.item['category_id'])
    odd = False
    total_b,total_a = 0,0
    for sc in self.repeating_panel_1.get_components():
      if odd:
        sc.background = 'grey'
      odd = not odd
      total_a += sc.a
      total_b += sc.b
    self.budget.text = "({b:.2f})".format(b=total_b/100) if total_b < 0 else "{b:.2f}".format(b=total_b/100)
    self.budget.foreground = 'theme:Amount Negative' if total_b < 0 else ''
    self.actual.text = "R {actual:.2f}".format(actual=total_a)
    self.actual.foreground = 'theme:Amount Negative' if total_a < 0 else ''
    self.update_bars(total_b,total_a)

  def update_bars(self,b,a,**event_args):
    #income bars are different
    maxi,min,v = 0,0,0
    if get_open_form().content_panel.get_components()[0].is_income(self.item['belongs_to']):
      self.progress_bar_1.min_value = 0
      self.progress_bar_1_edit.min_value = 0
      self.progress_bar_1.max_value = max(b,a)
      self.progress_bar_1_edit.max_value = max(b,a)
      self.progress_bar_1.value = a
      self.progress_bar_1_edit.value = a
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
      self.progress_bar_1.min_value,self.progress_bar_1_edit.min_value = min,min
      self.progress_bar_1.max_value,self.progress_bar_1_edit._max_value = maxi,maxi
      self.progress_bar_1.value,self.progress_bar_1_edit.value = v,v
      self.progress_bar_1.refresh_data_bindings()
  
  def link_1_click(self, **event_args):
    if self.link_1.icon == 'fa:angle-right':
      self.repeating_panel_1.items = app_tables.sub_categories.search(q.not_(order=-1),tables.order_by('order'),
                                                                      belongs_to=self.item['category_id'])
      
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
    budg.load_category_right(self.item['category_id'],period,True)
    # Make all other sub_cats clickable again (links vis, edit invis)
    budg.reset_sub_categories("")

  def calculate_me(self,info,**event_args):
    pass