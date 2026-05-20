import pandas as pd
import matplotlib.pyplot as plt

# Load the data
data = pd.read_csv('C:/Users/griff/OneDrive/Desktop/Research/Data Collection/Datasets/primary_df.csv')

# Exclude rows where Number of Pages is 0
data = data[data['Number of Pages'] != 0]

# Group data by Year and SJR IF, then calculate the mean of Number of Pages
pages_by_year_sjr = data.groupby(['Year', 'SJR IF'])['Number of Pages'].mean().unstack()

# Plot Number of Pages by Year for each SJR IF
plt.figure(figsize=(12, 8))
pages_by_year_sjr.plot(ax=plt.gca(), marker='o')
plt.title('Mean Number of Pages by Year (Separated by SJR IF)')
plt.xlabel('Year')
plt.ylabel('Mean Number of Pages')
plt.legend(title='SJR IF', bbox_to_anchor=(1.05, 1), loc='upper left')
plt.grid(True)
plt.tight_layout()
plt.show()