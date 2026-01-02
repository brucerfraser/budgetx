from ._anvil_designer import FrameTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import math

from ..F_PopUps.csv_confirm import csv_confirm
from ..F_Components.Dashboard_Screen import Dashboard_Screen
from ..F_Components.Transactions import Transactions
from ..F_Components.Budget import Budget
from ..F_Components.Reports import Reports
from ..F_Components.Settings import Settings
from ..F_Global_Logic import Global


#This is your startup form. It has a sidebar with navigation links and a content panel where page content will be added.
class Frame(FrameTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    
    #Present users with a login form with just one line of code:
    anvil.users.login_with_form()
    Global.make_date()
    Global.all_categories()
    Global.smarter()
    self.content_panel.visible = False
    Global.open_transactions_instance()
    #When the app starts up, the Dashboard form will be added to the page
    self.dashboard_page_link_click()
    self.paths = {"transactions":self.transactions_page_link,
                 "budget":self.budget_page_link,
                 "reports":self.reports_page_link}
    self.content_panel.visible = True
    
  def budget_page_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    #Clear the content panel and add the Sales Form
    self.content_panel.clear()
    self.content_panel.visible = False
    self.content_panel.add_component(Budget())
    #Change the color of the sales_page_link to indicate that the Sales page has been selected
    self.budget_page_link.background = app.theme_colors['Primary Container']
    clear_list = [self.transactions_page_link,self.reports_page_link,
                  self.dashboard_page_link,self.signout_link,
                  self.settings_page_link]
    for obj in clear_list:
      obj.background = "transparent"
    self.content_panel.visible = True

  def reports_page_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    #Clear the content panel and add the Sales Form
    self.content_panel.clear()
    self.content_panel.visible = False
    self.content_panel.add_component(Reports())
    #Change the color of the sales_page_link to indicate that the Sales page has been selected
    self.reports_page_link.background = app.theme_colors['Primary Container']
    clear_list = [self.transactions_page_link,self.dashboard_page_link,
                  self.budget_page_link,self.signout_link,
                  self.settings_page_link]
    for obj in clear_list:
      obj.background = "transparent"
    self.content_panel.visible = True

  def transactions_page_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    #Clear the content panel and add the Transactions Form
    self.content_panel.visible = False
    Global.Transactions_Form.remove_from_parent()
    Global.Transactions_Form.dash = False
    Global.Transactions_Form.sub_cat = None
    self.content_panel.clear()
    self.content_panel.add_component(Global.Transactions_Form)
    #Change the color of the sales_page_link to indicate that the Reports page has been selected
    self.transactions_page_link.background = app.theme_colors['Primary Container']
    clear_list = [self.dashboard_page_link,self.reports_page_link,
                  self.budget_page_link,self.signout_link,
                  self.settings_page_link]
    for obj in clear_list:
      obj.background = "transparent"
    self.content_panel.visible = True
    
  def file_loader_1_change(self, file, **event_args):
    acc_id, ready, raw, accounts = anvil.server.call('read_file',fn=file)
    # csv_confirm time
    result = alert(content=csv_confirm(accounts=accounts,acc_id=acc_id,ready=ready,
                                      trans=raw),
                   title="Confirm CSV Details",
                   large=True,
                   buttons=[])
    if result:
      anvil.server.call('save_transactions',ready_list=result)
      Global.Transactions_Form.reload_from_upload(result)
      self.file_loader_1.clear()
      # we need to refresh whichever page is loaded here.
      clear_list = [self.transactions_page_link,self.reports_page_link,
                    self.budget_page_link,self.signout_link,
                    self.settings_page_link,self.dashboard_page_link]
      for obj in clear_list:
        if obj.background != 'transparent':
          obj.raise_event('click')
    else:
      self.file_loader_1.clear()
   
  def dashboard_page_link_click(self, **event_args):
    self.content_panel.clear()
    self.content_panel.visible = False
    self.content_panel.add_component(Dashboard_Screen())
    #Change the color of the sales_page_link to indicate that the Reports page has been selected
    self.dashboard_page_link.background = app.theme_colors['Primary Container']
    clear_list = [self.transactions_page_link,self.reports_page_link,
                  self.budget_page_link,self.signout_link,
                  self.settings_page_link]
    for obj in clear_list:
      obj.background = "transparent"
    self.content_panel.visible = True

  def ping_ping(self,ping,**event_args):
    obj = self.paths[ping]
    obj.raise_event("click")

  def signout_link_click(self, **event_args):
    clear_list = [self.transactions_page_link,self.reports_page_link,
                  self.budget_page_link,self.dashboard_page_link,
                 self.settings_page_link]
    for obj in clear_list:
      # print(obj.background)
      if obj.background != 'transparent':
        # print("fired")
        obj.raise_event('click')
        break

  def settings_page_link_click(self, **event_args):
    self.content_panel.clear()
    self.content_panel.visible = False
    self.content_panel.add_component(Settings())
    #Change the color of the sales_page_link to indicate that the Sales page has been selected
    self.settings_page_link.background = app.theme_colors['Primary Container']
    clear_list = [self.transactions_page_link,self.reports_page_link,
                  self.dashboard_page_link,self.budget_page_link]
    for obj in clear_list:
      obj.background = "transparent"
    self.content_panel.visible = True

  







