import requests
from bs4 import BeautifulSoup
import yfinance as yf
import pandas as pd
from tqdm import tqdm

def read_text_file(file_path):
    with open(file_path, 'r') as file:
        symbols = [line.strip() for line in file.readlines()]
    return symbols

def fetch_eps_data(ticker):
    try:
        url = f"https://stockanalysis.com/stocks/{ticker}/financials/?p=quarterly"
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        eps_rows = soup.find_all('div', class_='row')[1:]
        eps_data = {}
        for row in eps_rows[:4]:
            columns = row.find_all('div')
            quarter = columns[0].text.strip()
            eps = columns[2].text.strip()
            eps_data[f'EPS {quarter}'] = eps
        return eps_data
    except Exception as e:
        print(f"Error fetching EPS data for {ticker}: {e}")
        return {}

def fetch_etf_count(ticker):
    try:
        url = f"https://www.etf.com/{ticker}"
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        etf_div = soup.find('div', class_="stock-information__data--main")
        etf_count = int(etf_div.text) if etf_div else 0
        return etf_count
    except Exception as e:
        print(f"Error fetching ETF count for {ticker}: {e}")
        return 0

def analyze_stock(ticker):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="2y", interval="1wk")
        current_price = hist['Close'].iloc[-1]

        # Calculate weekly percentage changes
        hist['PriceChange'] = hist['Close'].pct_change()
        percent_3wt = (hist['PriceChange'].rolling(window=3).sum() == 3).mean() * 100

        # Conditions for Cup and Handle detection (simplified for this example)
        is_cup = hist['PriceChange'].rolling(window=13).sum() < 0.1  # 3 months for cup
        is_handle = hist['PriceChange'].rolling(window=3).sum() < 0.02  # 3 weeks for handle

        # Check for uptrend after the handle
        uptrend_post_handle = hist['PriceChange'].rolling(window=4).sum() > 0.05

        meets_cup_handle_criteria = is_cup.iloc[-1] and is_handle.iloc[-1] and uptrend_post_handle.iloc[-1]
        return meets_cup_handle_criteria, percent_3wt
    except Exception as e:
        print(f"Error analyzing {ticker}: {e}")
        return False, 0

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

def format_3wt(percent_3wt):
    return f"{percent_3wt:.2f}%"

def main():
    file_path = 'Symbols.txt'
    tickers = read_text_file(file_path)
    analysis_results = []

    with tqdm(total=len(tickers), desc="Analyzing stocks") as pbar:
        for ticker in tickers:
            ticker = ticker.strip().upper()
            print(f"Analyzing ticker: {ticker}")

            meets_cup_handle_criteria, percent_3wt = analyze_stock(ticker)
            if meets_cup_handle_criteria:
                eps_data = fetch_eps_data(ticker)
                etf_count = fetch_etf_count(ticker)
                stock_info = yf.Ticker(ticker).info
                analysis_results.append({
                    'Ticker': ticker,
                    'Company Name': stock_info.get('shortName', 'N/A'),
                    'Stock Price': format_price(stock_info.get('currentPrice', 0)),
                    'Market Cap': format_market_cap(stock_info.get('marketCap', 0)),
                    '3WT %': format_3wt(percent_3wt),
                    '# ETFs Holding': etf_count,
                    'Link': f"[View Ticker](https://stockanalysis.com/stocks/{ticker.lower()}/)",
                    **eps_data
                })
            pbar.update(1)

    df = pd.DataFrame(analysis_results)
    if not df.empty:
        print(df.to_string(index=False))
    else:
        print("No stocks met the criteria.")

if __name__ == "__main__":
    main()
