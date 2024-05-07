import requests
from bs4 import BeautifulSoup
import datetime
from sqlalchemy import create_engine
from sqlalchemy import MetaData, Table, Column, String, Float, Boolean
from sqlalchemy.dialects.sqlite import insert

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
            all_links.append({'link': f"{base_url}{link['href']}", 'open': True})
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
            all_links.append({'link': f"{base_url}{link['href']}", 'open': False})
    else:
        print("No table found on the page")
else:
    print(f"Failed to retrieve content, status code: {response.status_code}")

engine = create_engine('sqlite:///foreclosure_sales_data.sqlite')
metadata = MetaData()
sales_listing_detail = Table('SalesListingDetail', metadata,
                             Column('SheriffNumber', String, primary_key=True),
                             Column('JudgmentValue', Float),
                             Column('CourtCaseNumber', String),
                             Column('SalesDate', String),
                             Column('Plaintiff', String),
                             Column('Defendant', String),
                             Column('ParcelNumber', String),
                             Column('Address', String),
                             Column('Attorney', String),
                             Column('Open', Boolean),
                             Column('CreatedAt', String),
                             Column('LastUpdate', String))
status_history = Table('StatusHistory', metadata,
                       Column('SheriffNumber', String, primary_key=True),
                       Column('Status', String, primary_key=True),
                       Column('Date', String, primary_key=True),
                       Column('Amount', Float),
                       Column('Name', String),
                       Column('CreatedAt', String),
                       Column('LastUpdate', String))
metadata.create_all(engine)

# Get the current date and time
current_time = datetime.datetime.now()
# Format the timestamp as a string
created_at = current_time.strftime('%Y-%m-%d %H:%M:%S')

# Scrape each detail link
num_link = 1
for link in all_links:
    print(f"{num_link}/{len(all_links)}: {link['link']}")
    num_link = num_link + 1
    response = session.get(link['link'])
    detail_soup = BeautifulSoup(response.text, 'html.parser')

    # Safely extract data from detail page using checks for None
    sheriff_no_elem = detail_soup.select_one('table:nth-of-type(1) tr:nth-of-type(1) td:nth-of-type(2)')
    judgment_value_elem = detail_soup.select_one('tr:nth-of-type(2) td:nth-of-type(2)')
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
    judgment_value = judgment_value_elem.text.strip() if judgment_value_elem else None
    court_case_no = court_case_no_elem.text.strip() if court_case_no_elem else None
    if sales_date_elem is not None:
        sales_date = sales_date_elem.text.strip()
        sales_date = datetime.datetime.strptime(sales_date, '%m/%d/%Y').strftime('%Y-%m-%d')
    else:
        sales_date = None
    plaintiff = plaintiff_elem.text.strip() if plaintiff_elem else None
    defendant = defendant_elem.text.strip() if defendant_elem else None
    parcel = parcel_elem.text.strip() if parcel_elem else None
    address = address_elem.text.strip() if address_elem else None
    attorney = attorney_elem.text.strip() if attorney_elem else None

    with engine.connect() as connection:
        insert_query = insert(sales_listing_detail).values(SheriffNumber=sheriff_no,
                                                           JudgmentValue=float(
                                                               judgment_value.replace("$", "").replace(",", "")),
                                                           CourtCaseNumber=court_case_no,
                                                           SalesDate=sales_date,
                                                           Plaintiff=plaintiff,
                                                           Defendant=defendant,
                                                           ParcelNumber=parcel,
                                                           Address=address,
                                                           Attorney=attorney,
                                                           Open=link['open'],
                                                           CreatedAt=created_at,
                                                           LastUpdate=created_at)
        connection.execute(insert_query.on_conflict_do_update(
            index_elements=['SheriffNumber'],
            set_=dict(
                JudgmentValue=insert_query.excluded.JudgmentValue,
                CourtCaseNumber=insert_query.excluded.CourtCaseNumber,
                SalesDate=insert_query.excluded.SalesDate,
                Plaintiff=insert_query.excluded.Plaintiff,
                Defendant=insert_query.excluded.Defendant,
                ParcelNumber=insert_query.excluded.ParcelNumber,
                Address=insert_query.excluded.Address,
                Attorney=insert_query.excluded.Attorney,
                Open=insert_query.excluded.Open,
                LastUpdate=insert_query.excluded.LastUpdate
            )
        ))

        history = detail_soup.select_one('table:nth-of-type(2)')
        history_rows = history.select('tr:not(:first-child)')
        for row in history_rows:
            columns = row.select('td')
            status = columns[0].text.strip()
            date = columns[1].text.strip()
            date = datetime.datetime.strptime(date, '%m/%d/%Y').strftime('%Y-%m-%d')

            if len(columns) == 4:
                amount = float(columns[2].text.strip().replace("$", "").replace(",", ""))
                name = columns[3].text.strip()
            else:
                amount = None
                name = None
            insert_query = insert(status_history).values(SheriffNumber=sheriff_no,
                                                         Status=status,
                                                         Date=date,
                                                         Amount=amount,
                                                         Name=name,
                                                         CreatedAt=created_at,
                                                         LastUpdate=created_at)
            connection.execute(insert_query.on_conflict_do_update(
                index_elements=['SheriffNumber', 'Status', 'Date'],
                set_=dict(
                    Status=insert_query.excluded.Status,
                    Date=insert_query.excluded.Date,
                    Amount=insert_query.excluded.Amount,
                    Name=insert_query.excluded.Name,
                    LastUpdate=insert_query.excluded.LastUpdate
                )
            ))

        connection.commit()
