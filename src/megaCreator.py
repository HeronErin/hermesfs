import pymailtm, time, string, random, json

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, WebDriverException

from faker import Faker
from mailtm import Email

fake = Faker()

def get_random_string(length):
    """Generate a random string with a given length."""
    lower_letters = string.ascii_lowercase
    upper_letters = string.ascii_uppercase
    numbers = string.digits
    alphabet = lower_letters + upper_letters + numbers

    result_str = "".join(random.choice(alphabet) for _ in range(length))
    return result_str



def waitFor(driver, sel):
	while True:
		try:
			return driver.find_element(By.CSS_SELECTOR, sel)
		except NoSuchElementException:
			time.sleep(0.25)
def run():
	em = Email()


	driver = webdriver.Chrome()
	ename, epass = [get_random_string(15), get_random_string(20)]

	em.register(username=ename, password=epass)


	account = {
		"first name": fake.unique.first_name(),
		"last name": fake.unique.last_name(),
		"email": em.address,
		"email_password": epass,
		"password": get_random_string(25),
	}
	print(account)

	# exit()
	driver.get("https://mega.nz/register")

	waitFor(driver, '[placeholder="First name"]').send_keys(account["first name"])
	time.sleep(0.35)
	driver.execute_script(f"""document.querySelector('[placeholder="First name"]').value = "{ account["first name"] }";""")

	waitFor(driver, '[placeholder="Last name"]').send_keys(account["last name"])
	time.sleep(0.35)
	driver.execute_script(f"""document.querySelector('[placeholder="Last name"]').value = "{ account["last name"] }";""")

	waitFor(driver, '[placeholder="Email"]').send_keys(account["email"])
	time.sleep(0.35)
	driver.execute_script(f"""document.querySelector('[placeholder="Email"]').value = "{ account["email"] }";""")
	waitFor(driver, '[placeholder="Password"]').send_keys(account["password"])
	time.sleep(0.35)
	driver.execute_script(f"""document.querySelector('[placeholder="Password"]').value = "{ account["password"] }";""")
	waitFor(driver, '[placeholder="Retype password"]').send_keys(account["password"])
	time.sleep(0.35)
	driver.execute_script(f"""document.querySelector('[placeholder="Retype password"]').value = "{ account["password"] }";""")

	waitFor(driver, '[tabindex="6"]').click()
	waitFor(driver, '[tabindex="7"]').click()
	time.sleep(0.25)

	waitFor(driver, 'button.branded-red.register-button').click()
	time.sleep(0.25)

	tries = 0
	while True:
		time.sleep(5)
		elist = em.message_list()
		if len(elist) != 0:
			email = em.message(elist[0]["id"])["text"]
			driver.get(email[email.find("https://mega.nz/#confirm"):].split("\n")[0])
			break
		else:
			tries+=1
		if tries == 4:
			return
	time.sleep(0.25)
	waitFor(driver, '#login-password2').send_keys(account["password"])
	time.sleep(0.4)
	waitFor(driver, '.login-button').click()
	while not driver.current_url.endswith("/pro"):
		time.sleep(1)
	time.sleep(2.75)
	waitFor(driver, '#freeStart')
	driver.get("https://mega.nz/fm/")
	time.sleep(5)

	# # execute_script
	f = open("accounts", "a")
	f.write(json.dumps(account) + "\n")
	f.close()
while True:
	try:run()
	except WebDriverException: pass
