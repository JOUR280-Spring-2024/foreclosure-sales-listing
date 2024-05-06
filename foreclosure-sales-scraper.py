import requests

session = requests.Session()
url = "https://salesweb.civilview.com/Sales/SalesSearch?countyId=42"
headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
}
response = session.get(url, headers=headers)
print(response.text)

