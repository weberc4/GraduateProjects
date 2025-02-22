from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
import time
import pandas as pd
from bs4 import BeautifulSoup
import requests
import smtplib
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# important information for apis
my_email = 'charlesjcweber@gmail.com'
password = ''
nellis_url = 'https://www.nellisauction.com/search?Location+Name=Dean+Martin&Suggested+Retail=100'

def get_listings():
    # purpose of this function is to scrape data from the Nellis Auction website
    # used for page information, provided context
    number = 0

    # selenium instantiation
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_experimental_option('detach', True)
    driver = webdriver.Chrome(options=chrome_options)

    # directs web driver to website
    driver.get(nellis_url)

    # waiting for all elements to appear on the page
    wait = WebDriverWait(driver, 10)
    # added as insurance
    wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'h6.text-body-lg.text-gray-900.font-semibold.line-clamp-2')))

    # scrapes information related to the retail price of the item being auctioned
    retail_prices = driver.find_elements(By.CSS_SELECTOR, 'p.text-body-md.leading-4.text-gray-900')
    current_bid = driver.find_elements(By.CSS_SELECTOR, 'div p.text-gray-900.font-semibold.line-clamp-1')

    # creates lists to hold each attribute of a listing
    listings = []
    prices = []
    current_bids = []
    time_until = []

    more_pages = True
    while more_pages:
        try:

            # Grabs name of the item in the listing, accounting for stale reference errors
            listings_count = len(
                driver.find_elements(By.CSS_SELECTOR, 'h6.text-body-lg.text-gray-900.font-semibold.line-clamp-2'))

            # purpose of this for loop is to grab the name of the listing. scraping the listing name is the only element which has
            # produced the stale element error, which is why the other elements don't incorporate the error check.
            try:
                for index in range(listings_count):
                    try:
                        # grabbing the element by index during each iteration
                        name = driver.find_elements(By.CSS_SELECTOR, 'h6.text-body-lg.text-gray-900.font-semibold.line-clamp-2')[index]
                        # print(element.text)
                        listings.append(name.text)

                        #to catch instances of when the element referenced becomes stale
                    except StaleElementReferenceException:
                        # when stale element reference occurs, retry at that index
                        print(f"Element at index {index} became stale. Retrying...")
                        # retry locating the specific element
                        name = driver.find_elements(By.CSS_SELECTOR, 'h6.text-body-lg.text-gray-900.font-semibold.line-clamp-2')[index]
                        listings.append(name.text)
            except:
                print('listings found')

            # grabbing the retail price for each item
            retail_elements = driver.find_elements(By.CSS_SELECTOR, 'p.text-body-md.leading-4.text-gray-900')

            # storing this information into a list
            for i in retail_elements:
                prices.append(i.text)

            # grabbing the current bid for each item
            current_bid = driver.find_elements(By.CSS_SELECTOR, 'div p.text-gray-900.font-semibold.line-clamp-1')

            # due to many elements sharing the same CSS Selector, grabs every 6th element where the price is found
            retail_prices = prices[1::6]

            # similarly, both the current bid and the time until close share the same css selector
            bids = current_bid[1::2]
            # stores the correct bid information into its list
            for i in bids:
                current_bids.append(i.text)

            # stores times into its list
            times = current_bid[0::2]
            for i in times:
                time_until.append(i.text)

            # grabs the next page button
            button = driver.find_element(By.CSS_SELECTOR, '[data-ax="pagination-next-page"]')

            # indicates that the current page has been read
            number += 1
            print(f'Page {number} read')
            # goes to next page until button is grayed out
            button.click()
        except:
            print('All pages found')
            more_pages = False

    # instantiates a dictionary to hold all the lists created throughout the loop
    auction_dict = {}

    # verifies that the list of names matches the list of bids
    print(len(listings))
    print(len(current_bids))

    # when nobody has bid on an item, return 0 for the item
    for i in range(0, len(current_bids)):
        try:
            if current_bids[i][1:] == '' and i < len(listings):
                current_bids[i] = '$0'

            # creates a key for each auctioned item attribute and assigns the previously created lists as the value
            auction_dict[i] = {

                'listing': listings[i],
                'price': float(retail_prices[i][1:]),
                'bid': float(current_bids[i][1:]),
                'time': time_until[i]}
        # for error catching
        except:
            auction_dict[i] = {

                'listing': listings[i],
                'price': float(retail_prices[i][1:]),
                'bid': 0,
                'time': time_until[i]}
    # turns the dictionary into a dataframe
    auction_df = pd.DataFrame.from_dict(auction_dict,orient='index')
    # print(auction_df)
    # returns the dataframe
    return auction_df


def standardize_time(df):
    # function is used to standardize all the time formats used on the website
    # get string matches ready for regex
    hours = ['hour','hours']
    minutes = ['minute','minutes']
    minsec = ['m ','s ']
    seconds = ['seconds']

    # preparing strings for use in regex expression
    pattern_hr = '|'.join(hours)
    pattern_mins = '|'.join(minutes)
    pattern_mnsc = '|'.join(minsec)
    pattern_secs = '|'.join(seconds)

    # checking if any part of the 'time left' attribute contains any of the substrings
    # assigns True/False based on regex check
    df['contains_hours'] = df['time'].str.contains(pattern_hr, regex=True)
    df['contains_minutes'] = df['time'].str.contains(pattern_mins,regex=True)
    df['contains_mnsec'] = df['time'].str.contains(pattern_mnsc,regex=True)
    df['contains_secs'] = df['time'].str.contains(pattern_secs,regex=True)
    df['has_ended'] = df['time'] == 'ENDED'

    # iterating over rows in the dataframe
    for idx, row in df.iterrows():
        try:
            # applies formula to time value based on the relevant format used
            if row['contains_secs']:
                if isinstance(row['time'], str) and 'seconds' in row['time']:
                    # uses regex to grab the numerical value
                    # \d catches digits used
                    match = re.match(r'(\d+)\s*seconds', row['time'])
                    if match:
                        # takes second value as given, casts as int for mathematical operation
                        seconds = int(match.group(1))
                        df.at[idx, 'time_left'] = seconds
                    else:
                        df.at[idx, 'time_left'] = None

            # applies function for rows where 'contains_minutes' is true
            elif row['contains_minutes']:
                if isinstance(row['time'], str) and 'minutes' in row['time']:
                    # uses regex to grab the numerical value
                    match = re.match(r'(\d+)\s*minutes', row['time'])
                    if match:
                        minutes = int(match.group(1))
                        # convert minutes to seconds by multiplying by 60
                        df.at[idx, 'time_left'] = minutes * 60
                    else:
                        df.at[idx, 'time_left'] = None

            # applies function for rows where 'contains_hours' is true
            elif row['contains_hours']:
                if isinstance(row['time'], str) and 'hour' in row['time']:
                    # uses regex to grab the numerical value
                    match = re.match(r'(\d+)\s*hour', row['time'])
                    if match:
                        hours = int(match.group(1))
                        # converts hours to seconds by multiplying by 3600
                        df.at[idx, 'time_left'] = hours * 3600
                    else:
                        df.at[idx, 'time_left'] = None

            # applies function for rows where 'contains_mnsec' is true
            elif row['contains_mnsec'] and not row['has_ended']:
                if isinstance(row['time'], str) and 'm' in row['time'] and 's' in row['time']:
                    match = re.match(r'(\d+)m\s*(\d+)s', row['time'])
                    if match:
                        minutes = int(match.group(1))
                        seconds = int(match.group(2))
                        # converts min/sec to seconds by multiplying minutes by 60 and adding seconds
                        df.at[idx, 'time_left'] = minutes * 60 + seconds
                    else:
                        df.at[idx, 'time_left'] = None

        except Exception as e:
            # Log the error for debugging
            print(f"Error processing row {idx}: {row['time']} -> {e}")
    # returns dataframe with the standardized time format
    return df

def send_email(auction_data):

    # for ease of reading, create a list of formatted strings to use in the email
    formatted_listings = []
    for _, row in auction_data.iterrows():
        listing = row['listing']
        retail = row['price']
        bid = row['bid']
        time_left = row['time']

        first_part = listing[:50]
        remaining_part = listing[30:]
        formatted_listings.append(
            # f"Listing: {first_part}...{remaining_part}\n"
            listing + '\n'
            f"Bid: ${bid} | Retail: ${retail} | Time Left: {time_left}\n"
        )
    print(formatted_listings)

    # combines all listings into a single email, separated by two newlines
    formatted_listings_str = "\n\n".join(formatted_listings)

    # creates body for the email
    body = (
            "Here are the auction items with bids under 25% retail and ending in the next 10 minutes:\n\n"
            + formatted_listings_str)

    # gets current time
    current_time = datetime.now()
    formatted_time = current_time.strftime("%H:%M:%S")

    # email subject
    subject = f"Auction Value Finds at {formatted_time}"

    #creating email parameters
    msg = MIMEMultipart()
    msg['From'] = my_email
    msg['To'] = "charlesjcweber@gmail.com"  # Replace with the recipient's email
    msg['Subject'] = subject

    #attaching the body to the email
    msg.attach(MIMEText(body, 'plain', 'utf-8'))

    # sending the email
    with smtplib.SMTP('smtp.gmail.com', port=587) as connection:
        connection.starttls()
        connection.login(user=my_email, password=password)
        print("Sending email...")
        connection.sendmail(from_addr=my_email, to_addrs="charlesjcweber@gmail.com", msg=msg.as_string())
    # to display in the console to keep track of
    print(f"Email sent successfully at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

def run_auction_checker():
    # purpose of the function is to begin the process of scraping, for the three hours where auctions are held
    # can be run either manually or on a schedule
    end_time = datetime.now() + timedelta(hours=3)

    # for 3 hours, run this loop
    while datetime.now() < end_time:
        try:
            # for
            print(f"Running auction checker at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

            # gets dataframe from function
            auction_df = get_listings()

            # provides a measure of how the bid compares to the retail price relatively speaking
            auction_df['bid_pct'] = auction_df['bid'] / auction_df['price']

            # uses function to standardize time
            df = standardize_time(auction_df)
            # df.to_csv('testing.csv')

            # filters dataframe to only the bids which are less than a quarter of their retail price, and ending in 15 min
            df = df[(df['bid_pct'] <= 0.25) & (df['time_left'] < 900)]
            df=df[df['time_left'] < 900]
            # df.to_csv('newdata.csv')

            # sorts based on time left, so that the auctions ending the soonest are shown first
            auction_data = df.sort_values('time_left', ascending=True)

            # trims to only the relevant columns
            auction_data = auction_data[['listing', 'price', 'bid', 'time','time_left']]

            # calls function which handles sending the finalized information
            if len(auction_data) > 0:
                send_email(auction_data)
            else:
                print('No matching items')

        # to catch any errors that might occur
        except Exception as e:
            print(f"An error occurred: {e}")

        # waits 10 minutes before sending the next update
        print("Waiting 10 minutes before the next check...")
        time.sleep(600)

    print("Finished running the auction checker for 3 hours.")


# begins program
run_auction_checker()
