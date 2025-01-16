import pandas as pd
import yfinance as yf
import datetime as dt
import requests
import smtplib
from datetime import timedelta

my_email = 'charlesjcweber@gmail.com'
password = 'sszh iiyc dtze kspf'

# key for news api
api_key = 'eeda485f148042069d3c21a149d6fc0e'

# initialize dates
today = dt.datetime.today()
yesterday = today - timedelta(days=1)

# If today is Monday, yesterday should be Friday
# if today.weekday() == 0:  # Monday
#     yesterday -= timedelta(days=2)

# when yesterday or day before yesterday falls on the weekend(when the stock market is closed), subtract
while yesterday.weekday() in [5, 6]:
    yesterday -= timedelta(days=1)

day_prior = yesterday - timedelta(days=1)
while day_prior.weekday() in [5, 6]:
    day_prior -= timedelta(days=1)

# appropriate datetime formats
today_str = today.strftime('%Y-%m-%d')
yesterday_str = yesterday.strftime('%Y-%m-%d')
day_prior_str = day_prior.strftime('%Y-%m-%d')

# list of specified stocks to watch, mix of magnificent 7 and smaller cap stocks
STOCKS = ['MGM','NIO', 'AAPL', 'META', 'MSFT', 'NVDA', 'TSLA', 'DUK']

# endpoint for the api
NEWS_ENDPOINT = "https://newsapi.org/v2/everything"
close_data = {}


# parses ticker data from yfinance
def parse_data(ticker, data):
    # grabs close data for each stock
    close_prices = data['Close']
    # only grab the keys in the dataframe that match the formatted dates created earlier
    filtered_dates = [d for d in close_prices.keys() if d.strftime('%Y-%m-%d') in [yesterday_str, day_prior_str]]

    # if there aren't two price values, return none
    if len(filtered_dates) < 2:
        return None

    # sorts data, grabs last in the list which is yesterday
    filtered_dates.sort()
    close_yesterday = close_prices[filtered_dates[1]]
    close_day_prior = close_prices[filtered_dates[0]]

    # calculates dollar difference between day yesterday and day before that,
    price_movement = close_yesterday - close_day_prior
    # lift is calculated as percentage increase
    percentage_change = round((price_movement / close_day_prior) * 100, 2)

    # grabs full name
    ticker_info = yf.Ticker(ticker).info
    company_name = ticker_info.get('longName', ticker)

    # return dataframe to be used as the value for the bigger dataframe
    return {
        'long_name': company_name,
        'date': yesterday_str,
        'closing_price': close_yesterday,
        'price_movement': price_movement,
        'movement': f'{percentage_change}%'
    }


# Fetch and process stock data
for stock in STOCKS:
    ticker = yf.Ticker(stock)
    # grabs 5 day history from yfinance
    weekly_data = ticker.history(period='5d').to_dict()
    # passes name of the stock and the yfinance weekly data to the function
    parsed_data = parse_data(stock, weekly_data)

    # assigns the ticker as the key, and the df parsed from the Ticker object is assigned to its associated ticker
    if parsed_data:
        close_data[stock] = parsed_data


# Fetch news for each stock
for stock in close_data:
    # grabs parameters for the news API
    parameters = {
        'q': close_data[stock]['long_name'],
        'apiKey': api_key,
        'language': 'en',
        'sortBy': 'relevancy'
    }
    # initiates call to the API
    news = requests.get(NEWS_ENDPOINT, params=parameters)
    # reads the response json
    news_data = news.json()

    # gets article title, description, and url for each stock in the list
    if 'articles' in news_data and news_data['articles']:
        first_article = news_data['articles'][0]
        close_data[stock]['article'] = first_article.get('title', 'No title')
        close_data[stock]['description'] = first_article.get('description', 'No description')
        close_data[stock]['url'] = first_article.get('url', 'No URL')


# creates email body
body_text = ''
# utilizes loop and f string to create proper text for each stock
for stock, data in close_data.items():
    body_text += (
        f"{stock}: {data['movement']}\n"
        f"{data.get('article', 'No news article')}\n"
        f"{data.get('description', '')}\n"
        f"{data.get('url', '')}\n\n"
    )

# sends email
with smtplib.SMTP('smtp.gmail.com', port=587) as connection:
    connection.starttls()
    connection.login(user=my_email, password=password)
    connection.sendmail(
        from_addr=my_email,
        to_addrs=my_email,
        msg=f'Subject: Daily Stock Movers {today_str}\n\n{body_text}'.encode('ascii', 'ignore').decode('ascii')
    )
print("Email sent successfully.")
