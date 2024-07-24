import requests
from bs4 import BeautifulSoup
import yfinance as yf
import pandas as pd
import numpy as np
from tqdm import tqdm
import time

def read_text_file(file_path):
    with open(file_path, 'r') as file:
        symbols = [line.strip() for line in file.readlines()]
    return symbols

def fetch_data_with_retry(url, retries=3, timeout=10):
    for attempt in range(retries):
        try:
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
            return response
        except (requests.RequestException, requests.Timeout) as e:
            print(f"Attempt {attempt + 1} failed for URL {url}: {e}")
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
        if quarterly_growth is None or quarterly_growth < 25:
            return None
        if annual_growth is None or annual_growth < 25:
            return None
        
        return {
            'Ticker': ticker,
            'Company Name': stock_info.get('shortName', 'N/A'),
            'Stock Price': format_price(stock_info.get('currentPrice', 0)),
            'Market Cap': format_market_cap(stock_info.get('marketCap', 0)),
            'Quarterly EPS (%)': f"{quarterly_growth:.2f}%" if quarterly_growth is not None else 'N/A',
            'Annual EPS (%)': f"{annual_growth:.2f}%" if annual_growth is not None else 'N/A',
            **eps_data
        }
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
    file_path = 'Symbols.txt'
    tickers = read_text_file(file_path)
    analysis_results = []

    with tqdm(total=len(tickers), desc="Analyzing stocks") as pbar:
        for ticker in tickers:
            ticker = ticker.strip().upper()
            print(f"Analyzing ticker: {ticker}")

            result = analyze_stock(ticker)
            if result:
                analysis_results.append(result)
            pbar.update(1)

    df = pd.DataFrame(analysis_results)

    # Remove rows with NaN EPS data
    eps_columns = [col for col in df.columns if col.startswith('EPS')]
    df = df.dropna(subset=eps_columns)

    if not df.empty:
        print(df.to_string(index=False))
    else:
        print("No stocks met the criteria.")

if __name__ == "__main__":
    main()
