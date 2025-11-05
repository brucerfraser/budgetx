from ._anvil_designer import one_transactionTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from .... import Global
from datetime import date, datetime
import math



class one_transaction(one_transactionTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.dd_list = Global.ACCOUNTS
    self.init_components(**properties)
    self.date.tag = 'date'
    self.account_name = ''
    # date checker for when date drop down is "changed"...it still fires even if the date 
    # comes back the same, which would waste time refreshing the page
    self.check_date_change = date(2000,1,1)
    for f in self.dd_list:
      if self.item['account'] == f[1]:
        self.account_name = f[0]
        break
    self.account.text = self.account_name
    self.categorise()
    # self.am_i_smart()
    

    
  def categorise(self,**event_args):
    names_list = sorted(list(map(lambda x: x['display'], Global.CATEGORIES.values())))
    self.autocomplete_1.suggestions = names_list
    if self.item['category'] == None:
      self.category.text = "None"
    else:
      # print(Global.CATEGORIES[self.item['category']])
      self.category.text = Global.CATEGORIES[self.item['category']]['display']
      self.category.background = Global.CATEGORIES[self.item['category']]['colour']
      self.autocomplete_1.text = self.category.text
    
  def set_bg(self,odd,**event_args):
    objs = [self.account,self.date,self.amount,self.category,self.description,self.card_1,
           self.card_2,self.card_3,self.card_4,self.card_5,self.card_6]
    for obj in objs:
      if odd:
        obj.background = "#2B383E"
      else:
        obj.background = "#595A3B"
    if self.item['amount'] < 0:
      self.amount.foreground = 'theme:Amount Negative'
    if self.item['category'] == None:
      self.category.background = 'theme:Amount Negative'
    else:
      self.category.background = Global.CATEGORIES[self.item['category']]['colour']

  def click_date(self, **event_args):
    self.check_date_change = self.item['date']
    self.date_picker_1.visible = True
    self.date_picker_1.focus()
    self.date.visible = False

  def date_picker_1_change(self, **event_args):
    # we should re-load if date has actually changed
    if self.item['date'] != self.check_date_change:
      frame = get_open_form()
      frm = frame.content_panel.get_components()[0]
      frm.load_me(False)
    self.date_picker_1.visible = False
    self.date.visible = True
    

  def click_account(self, **event_args):
    self.drop_down_1.visible = True
    self.drop_down_1.focus()
    # self.drop_down_1.
    self.account.visible = False

  def drop_down_1_change(self, **event_args):
    for f in self.dd_list:
      if self.item['account'] == f[1]:
        self.account_name = f[0]
        break
    self.account.text = self.account_name
    self.account.visible = True
    self.drop_down_1.visible = False
    # have to change the hash here
    self.item['hash'] = str(self.item['date'].day) + str(self.item['date'].month) + str(self.item['date'].year)+ str(self.item['amount']) + self.item['account']
  
  def amount_click(self, **event_args):
    self.text_box_1.visible = True
    self.text_box_1.focus()
    self.amount.visible = False

  def some_lose_focus(self,**event_args):
    # must update here...
    self.item['amount'] = int(math.floor(self.text_box_1.text*100))
    self.amount.visible = True
    self.text_box_1.visible = False

  def description_click(self, **event_args):
    self.text_box_2.visible = True
    self.text_box_2.focus()
    self.description.visible = False

  def desc_lose_focus(self, **event_args):
    self.refresh_data_bindings()
    self.description.visible = True
    self.text_box_2.visible = False

  def category_click(self, **event_args):
    self.autocomplete_1.visible = True
    if self.autocomplete_1.text == '':
      self.autocomplete_1.focus()
    self.category.visible = False

  def category_choose(self,**event_args):
    self.item['category'] = next((k for k, v in Global.CATEGORIES.items() if v.get('display') == self.autocomplete_1.text), None)
    self.category.text = self.autocomplete_1.text
    Global.smarter(first=False,update=(self.item['category'],self.item['description']))
    self.category.background = Global.CATEGORIES[self.item['category']]['colour']
    self.category.visible = True
    self.autocomplete_1.visible = False
    frame = get_open_form()
    frm = frame.content_panel.get_components()[0]
    frm.smart_cat_update()

  def autocomplete_1_lost_focus(self, **event_args):
    if self.item['category']:
      self.autocomplete_1.text = self.category.text
      self.category.visible = True
      self.autocomplete_1.visible = False
    else:
      self.category.text = "None"
      self.category.background = 'theme:Amount Negative'
      self.category.visible = True
      self.autocomplete_1.visible = False

  def am_i_smart(self,**event_args):
    if not self.item['category'] or self.category.border != "":
      #below is a problem - doing a server call regardless of return.
      self.item['category'] = Global.is_it_smart(self.item['description'])
      if self.item['category']:
        #we must outline in correct colour
        c = Global.CATEGORIES[self.item['category']]['colour']
        self.category.border = "solid {b} 1px".format(b=c)
        self.category.text = Global.CATEGORIES[self.item['category']]['display']
  
