from ._anvil_designer import Dashboard_Screen_MobileTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from ...F_Global_Logic import Global
from ...F_Components.Budget_mini import Budget_mini
from ...F_Components.Reports_mini import Reports_mini


class Dashboard_Screen_Mobile(Dashboard_Screen_MobileTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    self.which_form = "dashboard_mobile"
    self.load_everything()
    if app_tables.settings.get(id="budget")["dash_variances"]:
      self.label_1_copy.text = "Chosen budget variances"
    else:
      self.label_1_copy.text = "Top 5 (worst) variances"

  def load_everything(self, **event_args):
    Global.Transactions_Form.dash = True
    Global.Transactions_Form.remove_from_parent()
    self.link_transactions.add_component(Global.Transactions_Form)
    self.link_budget.add_component(Budget_mini())
    self.link_report.add_component(Reports_mini())

  def link_transactions_click(self, **event_args):
    get_open_form().ping_ping("transactions")

  def link_budget_click(self, **event_args):
    get_open_form().ping_ping("budget")

  def link_report_click(self, **event_args):
    get_open_form().ping_ping("reports")

  def smart_cat_update(self, **event_args):
    Global.Transactions_Form.smart_cat_update()
