# Champaign County's Foreclosure Sales Listing

This scraper extracts data from the Champaign County's [Foreclosure Sales Listing](https://salesweb.civilview.com/Sales/SalesSearch?countyId=42).

The data is stored as a SQLite database named `foreclosure_sales_data.sqlite`.

The code can be run every day to add new records to the database. Previous records are retained and new
records are added.

If you end up using this database in a news report, please give credit to YiKe Liu.
