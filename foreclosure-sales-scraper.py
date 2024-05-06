import requests
from bs4 import BeautifulSoup
import sqlite3

all_links = []

# Create a session object
session = requests.Session()

# Set the base URL
base_url = "https://salesweb.civilview.com"

# Search URL
search_url = f"{base_url}/Sales/SalesSearch?countyId=42"

# Headers to mimic a browser visit
headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/122.0.0.0 Safari/537.36'
}

# Send GET request to fetch initial page and maintain session
response = session.get(search_url, headers=headers)

# Check if page was loaded successfully
if response.status_code == 200:
    # Use BeautifulSoup to parse HTML content
    soup = BeautifulSoup(response.text, 'html.parser')

    # Find the data table, assuming the data is contained in a table with class 'table'
    open_links = soup.find_all('a')

    if open_links:
        for link in open_links:
            all_links.append(f"{base_url}{link['href']}")
    else:
        print("No links found on the page")
else:
    print(f"Failed to retrieve content, status code: {response.status_code}")

# Define the parameters for POST request
data = {
    'IsOpen': 'false'  # This should match the input field for sold/cancelled properties
}

# POST request to fetch sold/cancelled properties
response = session.post(search_url, headers=headers, data=data)

# Check if the page was loaded successfully
if response.status_code == 200:
    # Use BeautifulSoup to parse the HTML content
    soup = BeautifulSoup(response.text, 'html.parser')

    # Find the data table, assuming the data is contained in a table with class 'table'
    closed_links = soup.find_all('a')

    if closed_links:
        for link in closed_links:
            all_links.append(f"{base_url}{link['href']}")
    else:
        print("No table found on the page")
else:
    print(f"Failed to retrieve content, status code: {response.status_code}")

# Connect to SQLite Database
conn = sqlite3.connect('sales_data.db')
c = conn.cursor()

# Create tables
c.execute('CREATE TABLE IF NOT EXISTS SalesListingDetail (\n'
          '  SheriffNo TEXT PRIMARY KEY,\n'
          '  JudgementValue TEXT,\n'
          '  CourtCaseNo TEXT,\n'
          '  SalesDate TEXT,\n'
          '  Plaintiff TEXT,\n'
          '  Defendant TEXT,\n'
          '  Parcel TEXT,\n'
          '  Address TEXT,\n'
          '  Attorney TEXT)')
# c.execute('''CREATE TABLE IF NOT EXISTS StatusHistory (PropertyId INTEGER, StatusDate TEXT, StatusDescription TEXT, FOREIGN KEY(PropertyId) REFERENCES SalesListingDetail(PropertyId))''')

# Scrape each detail link
for link in all_links:
    response = session.get(link)
    detail_soup = BeautifulSoup(response.text, 'html.parser')

    # Safely extract data from detail page using checks for None
    sheriff_no_elem = detail_soup.select_one('table:nth-of-type(1) tr:nth-of-type(1) td:nth-of-type(2)')
    judgement_value_elem = detail_soup.select_one('tr:nth-of-type(2) td:nth-of-type(2)')
    court_case_no_elem = detail_soup.select_one('tr:nth-of-type(3) td:nth-of-type(2)')
    sales_date_elem = detail_soup.select_one('tr:nth-of-type(4) td:nth-of-type(2)')
    plaintiff_elem = detail_soup.select_one('tr:nth-of-type(5) td:nth-of-type(2)')
    defendant_elem = detail_soup.select_one('tr:nth-of-type(6) td:nth-of-type(2)')
    parcel_elem = detail_soup.select_one('tr:nth-of-type(7) td:nth-of-type(2)')
    address_elem = detail_soup.select_one('tr:nth-of-type(8) td:nth-of-type(2)')
    attorney_elem = detail_soup.select_one('tr:nth-of-type(9) td:nth-of-type(2)')

    if sheriff_no_elem is not None:
        sheriff_no = sheriff_no_elem.text.strip()
    else:
        sheriff_no = None
    judgement_value = judgement_value_elem.text.strip() if judgement_value_elem else None
    court_case_no = court_case_no_elem.text.strip() if court_case_no_elem else None
    sales_date = sales_date_elem.text.strip() if sales_date_elem else None
    plaintiff = plaintiff_elem.text.strip() if plaintiff_elem else None
    defendant = defendant_elem.text.strip() if defendant_elem else None
    parcel = parcel_elem.text.strip() if parcel_elem else None
    address = address_elem.text.strip() if address_elem else None
    attorney = attorney_elem.text.strip() if attorney_elem else None

    print(sheriff_no, judgement_value, court_case_no, sales_date, plaintiff, defendant, parcel, address, attorney)

    # Insert data into SalesListingDetail
    c.execute(
        'INSERT INTO SalesListingDetail (SheriffNo, JudgementValue, CourtCaseNo, SalesDate, Plaintiff, Defendant, Parcel, Address, Attorney) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (sheriff_no, judgement_value, court_case_no, sales_date, plaintiff, defendant, parcel, address, attorney))
    # property_id = c.lastrowid

    # Extracting status history
    # status_history = detail_soup.find_all('selector_for_status_history')
    # for status in status_history:
    #    status_date = status.find('date_selector').text if status.find('date_selector') else 'Unavailable'
    #    status_description = status.find('desc_selector').text if status.find('desc_selector') else 'Unavailable'
    #    c.execute('INSERT INTO StatusHistory (PropertyId, StatusDate, StatusDescription) VALUES (?, ?, ?)', (property_id, status_date, status_description))

    # Commit after each property to save changes
conn.commit()

# Close the database connection
conn.close()
