from ._anvil_designer import FrameTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
# from .Reports import Reports
# from .Sales import Sales
from ..Pop_menus.csv_confirm import csv_confirm
from .Dashboard_Screen import Dashboard_Screen
from ..Components.Transactions import Transactions
from ..Components.Budget import Budget
from ..Components.Reports import Reports

from .. import Global

#This is your startup form. It has a sidebar with navigation links and a content panel where page content will be added.
class Frame(FrameTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    
    #Present users with a login form with just one line of code:
    #anvil.users.login_with_form()
    
    #When the app starts up, the Dashboard form will be added to the page
    self.dashboard_page_link_click()
    self.paths = {"transactions":self.transactions_page_link,
                 "budget":self.budget_page_link,
                 "reports":self.reports_page_link}
    # self.first_run_income()

  def first_run_income(self,**event_args):
    app_tables.categories.add_row(category_id=Global.new_id_needed(),
                                 order=1,name="Income",colour="#1EB980")

  def budget_page_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    #Clear the content panel and add the Sales Form
    self.content_panel.clear()
    self.content_panel.add_component(Budget())
    #Change the color of the sales_page_link to indicate that the Sales page has been selected
    self.budget_page_link.background = app.theme_colors['Primary Container']
    clear_list = [self.transactions_page_link,self.reports_page_link,self.dashboard_page_link]
    for obj in clear_list:
      obj.background = "transparent"

  def reports_page_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    #Clear the content panel and add the Sales Form
    self.content_panel.clear()
    self.content_panel.add_component(Reports())
    #Change the color of the sales_page_link to indicate that the Sales page has been selected
    self.reports_page_link.background = app.theme_colors['Primary Container']
    clear_list = [self.transactions_page_link,self.budget_page_link,self.dashboard_page_link]
    for obj in clear_list:
      obj.background = "transparent"

  def transactions_page_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    #Clear the content panel and add the Reports Form
    self.content_panel.clear()
    self.content_panel.add_component(Transactions())
    #Change the color of the sales_page_link to indicate that the Reports page has been selected
    self.transactions_page_link.background = app.theme_colors['Primary Container']
    

  def load_transactions(self, **event_args):
    #WILL HAVE to change the transactions here to Transactions_Screen
    self.content_panel.clear()
    # self.content_panel.add_component(Transactions())
    #Change the color of the sales_page_link to indicate that the Reports page has been selected
    self.transactions_page_link.background = app.theme_colors['Primary Container']
    clear_list = [self.sales_page_link,self.reports_page_link,self.transactions_page_link]
    for obj in clear_list:
      obj.background = "transparent"
    self.sales_page_link.background = "transparent"
    self.reports_page_link.background = "transparent"

  #If using the Users service, uncomment this code to log out the user:
  # def signout_link_click(self, **event_args):
  #   """This method is called when the link is clicked"""
  #   anvil.users.logout()
  #   open_form('Logout')

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
    # print(result)

  def dashboard_page_link_click(self, **event_args):
    self.content_panel.clear()
    self.content_panel.add_component(Dashboard_Screen())
    #Change the color of the sales_page_link to indicate that the Reports page has been selected
    self.dashboard_page_link.background = app.theme_colors['Primary Container']
    clear_list = [self.transactions_page_link,self.reports_page_link,self.budget_page_link]
    for obj in clear_list:
      obj.background = "transparent"

  def ping_ping(self,ping,**event_args):
    obj = self.paths[ping]
    obj.raise_event("click")

  def signout_link_click(self, **event_args):
    """This method is called when the button is clicked"""
    pass

  







