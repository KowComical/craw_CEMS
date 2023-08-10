import pandas as pd
import os
from collections import defaultdict

file_path = 'K:\\Github\\craw_CEMS\\test'
out_path = 'K:\\Github\\craw_CEMS\\date\\'


def search_file(file_path):
    import os

    file_name = []
    for parent, surnames, filenames in os.walk(file_path):
        for fn in filenames:
            file_name.append(os.path.join(parent, fn))
    return file_name


all_file = search_file(file_path)

# A dictionary to hold file paths by month
files_dict = defaultdict(list)

for file_path in all_file:
    # Extract the month from the file name
    base_name = os.path.basename(file_path)
    month = os.path.splitext(base_name)[0][:6]  # Assuming file name is YYYYMMDD.csv

    # Append the file path to the list for its month
    files_dict[month].append(file_path)

# Process each month individually
for month, file_paths in files_dict.items():
    # A list to hold dataframes for this month
    dfs = []

    for file_path in file_paths:
        # Extract the company name from the file path
        company_name = os.path.basename(os.path.dirname(file_path))

        try:
            # Load the CSV file into a DataFrame
            df = pd.read_csv(file_path)
        except pd.errors.EmptyDataError:
            # Extract the date from the file name
            base_name = os.path.basename(file_path)
            date = os.path.splitext(base_name)[0]  # Assuming file name is YYYYMMDD.csv

            # Create a DataFrame with one row of NaN values, except for the 'company' and 'date' columns
            df = pd.DataFrame({'company': [company_name], 'day': [date]})

        # Add a 'company' column
        df['company'] = company_name

        # Append the DataFrame to the list for this month
        dfs.append(df)

    # Extract year and month from the month string
    year = month[:4]
    month_only = month[4:6]

    # Make directories for the year and month, if they don't already exist
    year_month_dir = os.path.join(out_path, year)
    os.makedirs(year_month_dir, exist_ok=True)

    # Concatenate all the dataframes for this month
    result = pd.concat(dfs)

    # Write the result to a new CSV file in the year/month directory
    # Format the file name as 'YYYY-MM.csv'
    result.to_csv(os.path.join(year_month_dir, f'{year}-{month_only}.csv'), index=False, encoding='utf_8_sig')

    print(f"Finished processing data for {year}-{month_only}")
