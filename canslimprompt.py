import requests
from bs4 import BeautifulSoup
import yfinance as yf
import pandas as pd
import numpy as np
import time
from fake_useragent import UserAgent
from datetime import datetime

# Initialize the user agent generator
ua = UserAgent()

def get_new_user_agent():
    new_ua = ua.random
    return new_ua

# Define rate limit
RATE_LIMIT = 25  # requests per minute
RATE_LIMIT_INTERVAL = 60 / RATE_LIMIT  # time interval between requests

def read_text_file(file_path):
    with open(file_path, 'r') as file:
        symbols = [line.strip() for line in file.readlines()]
    return symbols

def fetch_data_with_retry(url, retries=3, timeout=10):
    for attempt in range(retries):
        user_agent = get_new_user_agent()
        headers = {
            "User-Agent": user_agent
        }
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            return response
        except (requests.RequestException, requests.Timeout) as e:
            print(f"Attempt {attempt + 1} failed for URL {url} with User-Agent {user_agent}: {e}")
            time.sleep(2)  # Wait before retrying
    print(f"All attempts failed for URL {url}")
    return None

def fetch_eps_data(ticker):
    url = f"https://stockanalysis.com/stocks/{ticker}/financials/?p=quarterly"
    response = fetch_data_with_retry(url)
    if response is None:
        return {}
    soup = BeautifulSoup(response.text, 'html.parser')
    
    table = soup.find('table')
    if not table:
        print(f"No financials table found for {ticker}")
        return {}

    rows = table.find_all('tr')
    eps_data = {}
    for row in rows:
        columns = row.find_all('td')
        if len(columns) < 3:
            continue
        period = columns[0].text.strip()
        if 'EPS' in period:
            for i in range(1, len(columns)):
                eps_data[f'EPS {i}'] = columns[i].text.strip()
            break
    
    return eps_data

def fetch_annual_eps_data(ticker):
    url = f"https://stockanalysis.com/stocks/{ticker}/financials/?p=annual"
    response = fetch_data_with_retry(url)
    if response is None:
        return {}
    soup = BeautifulSoup(response.text, 'html.parser')
    
    table = soup.find('table')
    if not table:
        print(f"No financials table found for {ticker}")
        return {}

    rows = table.find_all('tr')
    eps_data = {}
    for row in rows:
        columns = row.find_all('td')
        if len(columns) < 3:
            continue
        period = columns[0].text.strip()
        if 'EPS' in period:
            for i in range(1, len(columns)):
                eps_data[f'EPS {i}'] = columns[i].text.strip()
            break
    
    return eps_data

def calculate_quarterly_eps_growth(eps_data):
    try:
        eps_values = list(eps_data.values())
        if len(eps_values) < 2:
            print("Insufficient data for quarterly EPS growth calculation.")
            return None
        latest_eps = float(eps_values[0].replace('$', '').replace(',', ''))
        previous_eps = float(eps_values[1].replace('$', '').replace(',', ''))
        if previous_eps == 0:
            print("Previous EPS is zero, cannot calculate growth.")
            return None
        growth = ((latest_eps - previous_eps) / previous_eps) * 100
        return growth
    except Exception as e:
        print(f"Error calculating quarterly EPS growth: {e}")
        return None

def calculate_annual_eps_growth(annual_eps_data):
    try:
        eps_values = list(annual_eps_data.values())
        if len(eps_values) < 3:
            print("Insufficient data for annual EPS growth calculation.")
            return None
        latest_eps = float(eps_values[0].replace('$', '').replace(',', ''))
        three_years_ago_eps = float(eps_values[2].replace('$', '').replace(',', ''))
        if three_years_ago_eps == 0:
            print("Three years ago EPS is zero, cannot calculate growth.")
            return None
        growth = ((latest_eps - three_years_ago_eps) / three_years_ago_eps) * 100
        return growth
    except Exception as e:
        print(f"Error calculating annual EPS growth: {e}")
        return None

def analyze_stock(ticker):
    try:
        stock = yf.Ticker(ticker)
        stock_info = stock.info
        eps_data = fetch_eps_data(ticker)
        annual_eps_data = fetch_annual_eps_data(ticker)
        quarterly_growth = calculate_quarterly_eps_growth(eps_data)
        annual_growth = calculate_annual_eps_growth(annual_eps_data)
        
        # Apply CANSLIM criteria
        meets_criteria = True
        summary = f"Summary for {ticker}:\n"

        if quarterly_growth is None or quarterly_growth <= 25:
            meets_criteria = False
            summary += f"- Does not meet quarterly EPS growth criteria (<= 25%): {quarterly_growth}%\n"
        else:
            summary += f"- Meets quarterly EPS growth criteria (> 25%): {quarterly_growth}%\n"

        if annual_growth is None or annual_growth <= 25:
            meets_criteria = False
            summary += f"- Does not meet annual EPS growth criteria (<= 25%): {annual_growth}%\n"
        else:
            summary += f"- Meets annual EPS growth criteria (> 25%): {annual_growth}%\n"
        
        result = {
            'Ticker': ticker,
            'Company Name': stock_info.get('shortName', 'N/A'),
            'Stock Price': stock_info.get('currentPrice', 0),
            'Formatted Stock Price': format_price(stock_info.get('currentPrice', 0)),
            'Market Cap': format_market_cap(stock_info.get('marketCap', 0)),
            'Quarterly EPS (%)': f"{quarterly_growth:.2f}%" if quarterly_growth is not None else 'N/A',
            'Annual EPS (%)': f"{annual_growth:.2f}%" if annual_growth is not None else 'N/A',
            **eps_data
        }

        summary += "\nCANSLIM Criteria:\n"
        if meets_criteria:
            summary += "This stock meets the CANSLIM criteria.\n"
        else:
            summary += "This stock does not meet the CANSLIM criteria.\n"

        result['Summary'] = summary

        return result
    except Exception as e:
        print(f"Error analyzing {ticker}: {e}")
        return None

def format_price(price):
    return f"${price:,.2f}"

def format_market_cap(cap):
    if cap >= 1_000_000_000:
        return f"${cap / 1_000_000_000:.1f}B"
    elif cap >= 1_000_000:
        return f"${cap / 1_000_000:.1f}M"
    elif cap >= 1_000:
        return f"${cap / 1_000:.1f}K"
    else:
        return f"${cap}"

def main():
    ticker = input("Enter the ticker symbol to analyze: ").strip().upper()
    print(f"Analyzing ticker: {ticker}")

    result = analyze_stock(ticker)
    
    if result:
        df = pd.DataFrame([result])
        df = df.sort_values(by='Stock Price')
        print(result['Summary'])
        print(df.drop(columns=['Stock Price', 'Summary']).to_string(index=False))

        # Output results to CANSLIM_{ticker}_{timestamp}.txt
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"CANSLIM_{ticker}_{timestamp}.txt"
        with open(output_filename, 'w') as output_file:
            output_file.write(result['Summary'])
            output_file.write(df.drop(columns=['Stock Price', 'Summary']).to_string(index=False))

        print(f"Results written to {output_filename}")
    else:
        print("No stocks met the criteria.")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"CANSLIM_{ticker}_{timestamp}.txt"
        with open(output_filename, 'w') as output_file:
            output_file.write("No stocks met the criteria.\n")

if __name__ == "__main__":
    main()
