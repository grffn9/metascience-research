import pandas as pd

# Load the datasets
# Replace 'journals_file.csv' and 'primary_file.csv' with your file paths
journals_df = pd.read_csv('journals_df.csv')
primary_df = pd.read_csv('primary_df.csv')

# Ensure the ISSN columns are consistent in both datasets (e.g., strings)
journals_df['ISSN'] = journals_df['ISSN'].astype(str)
primary_df['ISSN'] = primary_df['ISSN'].astype(str)

# Select only relevant columns from journals_df to avoid duplication
journals_df = journals_df[['ISSN', 'SJR_Category']]

# Merge the datasets on the ISSN column
primary_df = primary_df.merge(journals_df, on='ISSN', how='left')

# Rename the SJR_Category column in primary_df to 'SJR IF'
primary_df.rename(columns={'SJR_Category': 'SJR IF'}, inplace=True)

# Save or display the updated primary_df
print(primary_df.head())

# Optionally save to a new CSV
primary_df.to_csv('primary_df.csv', index=False)
