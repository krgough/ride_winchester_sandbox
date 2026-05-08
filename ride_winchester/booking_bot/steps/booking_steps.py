from behave import given, when, then
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

# This runs once to setup the browser
@given('I am on the Winchester CTC login page')
def step_open_login(context):
    options = Options()
    options.add_experimental_option("detach", True)
    # We store the driver in 'context' so all steps can use it
    context.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    context.driver.get("https://winchesterctc.org.uk/RW/Dev/user_login.php?")

@when('I log in with username "{user}" and password "{pw}"')
def step_login(context, user, pw):
    """ Login to RW """
    context.driver.find_element(By.NAME, "userid_email").send_keys(user)
    context.driver.find_element(By.NAME, "pwd").send_keys(pw)
    context.driver.find_element(By.NAME, "submitlogin").click()

@when('I navigate to the rides list')
def step_nav_rides(context):
    context.driver.get("https://winchesterctc.org.uk/RW/Dev/rideslist.php?rdetails=1")

@when('I select the "Friday" filter')
def step_filter_friday(context):
    # Find the checkbox for Friday and click it
    friday_check = context.driver.find_element(By.ID, "fri") # Replace with actual ID
    if not friday_check.is_selected():
        friday_check.click()

@then('I should see the Friday rides available')
def step_verify(context):
    assert "Friday" in context.driver.page_source
