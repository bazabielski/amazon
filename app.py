from flask import Flask, redirect, request, jsonify, session, render_template
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup
from requests_html import HTMLSession
import unidecode
import re
from datetime import timedelta
items = []
user_input = ''
app = Flask(__name__, static_url_path='/static', static_folder='static')
app.secret_key = "33d543126-671j0-132-r432-1o9543879"
app.permanent_session_lifetime = timedelta(minutes=30)
@app.route("/", methods=["GET"])
def show_index():
    return render_template('index.html')

@app.route("/", methods=["POST"])
def index():
    global items,nazwa,firma,user_input
    if request.method == "POST":
        nazwa = request.form.get("nazwa")
        user_input = nazwa
        items = []
        s = HTMLSession()
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--headless')

        driver = webdriver.Chrome(options=chrome_options)
        driver.get("https://www.amazon.pl")
        current_url = driver.current_url


        max_retries = 3  # Set the maximum number of retries
        retry_count = 0

        while retry_count < max_retries:
            try:
                search = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.ID, "twotabsearchtextbox"))
                )
                search.send_keys(user_input)
                search.send_keys(Keys.ENTER)
                break  # If the element is found, break out of the loop
            except TimeoutException:
                print("Element not found within the timeout. Refreshing the page and retrying.")
                driver.refresh()
                retry_count += 1
        else:
            print("Reached maximum retries. Element could not be found.")

        page_count = 1

        while True:
            print(f"Scraping data from page {page_count}...")

            # Wait for the page to load and render the content
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "search"))
            )

            # Get the page source with the content
            page_source = driver.page_source

            # Use BeautifulSoup to parse the content
            soup = BeautifulSoup(page_source, 'html.parser')

            elements = [element.text for element in soup.find_all(class_="a-size-base-plus a-color-base a-text-normal")]
            price_whole = price_whole = [element.text.replace(',', '').replace("&nbsp;", "").replace('\xa0', "") for element in soup.find_all(class_="a-price-whole")]
            price_decimal = [element.text for element in soup.find_all(class_="a-price-fraction")]
            a_elements = soup.find_all('a', class_='a-link-normal s-underline-text s-underline-link-text s-link-style a-text-normal')
            links = [a_element.get('href') for a_element in a_elements]
            img_elements = soup.find_all('img', {'class': 's-image'})
            img = [a_element.get('src') for a_element in img_elements]
            for i in range(len(elements)):
                items_from_amazon = {}
                try:
                    items_from_amazon['name'] = elements[i]
                    items_from_amazon['price'] = unidecode.unidecode(f'{price_whole[i]}.{price_decimal[i]}')
                    items_from_amazon['link'] = links[i]
                    items_from_amazon['img'] = img[i]
                except IndexError:
                    continue
                items.append(items_from_amazon)
        
            # Process the data from the current page
            # Add your data scraping and saving code here


            pagination = soup.find('span', class_='s-pagination-strip')
            if pagination:
                next_page = pagination.find('a', class_='s-pagination-item s-pagination-next s-pagination-button s-pagination-separator')
                if next_page:
                    next_page_url = next_page['href']
                    print("Next page URL:", next_page_url)

                    
                    driver.get(f'https://www.amazon.pl/{next_page_url}')
                    page_count += 1
                else:
                    print("No more pages to scrape. Stopping.")
                    break
            else:
                print("No pagination found. Stopping.")
                break
    session['items_from_amazon'] = items
    return redirect("/results")     

def extract_price(item):
    try:
        price = float(item['price'].replace(' ', '').replace(',', '.'))
    except (ValueError, TypeError):
        # Handle cases where price couldn't be converted
        price = float('inf')
    return price
 
@app.route("/results")
def show_results():
    prices = [extract_price(item) for item in items]
    average_price = round(sum(prices) / len(prices), 2)


    checkin = user_input.split()

    filtered_items = [item for item in items if extract_price(item) > 0.2 * average_price and any(word in item['name'].lower() for word in checkin)]
    
    filtered_items.sort(key=lambda item: float(item['price']))
    print(filtered_items)
    return render_template("result.html",filtered_items=filtered_items, average_price=average_price, item_name = user_input.capitalize())
    



if __name__ == "__main__":
    app.run(debug=True)
