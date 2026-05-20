import ethnicolr
import pandas as pd

# Load your author DataFrame
author_df = pd.read_csv('author_df.csv')

# Predict race using ethnicolr
author_df = ethnicolr.pred_fl_reg_name(author_df, 'Last Name', 'First Name')

# Drop the unnecessary columns
columns_to_drop = ['asian', 'hispanic', 'nh_black', 'nh_white']
author_df.drop(columns=columns_to_drop, inplace=True, axis=1)

# Rename the 'race' column to 'Ethnicity' and remove 'nh_' prefix
author_df.rename(columns={'race': 'Ethnicity'}, inplace=True)
author_df['Ethnicity'] = author_df['Ethnicity'].str.replace('nh_', '')

# Save the updated DataFrame to a new CSV
author_df.to_csv('author_df.csv', index=False)
