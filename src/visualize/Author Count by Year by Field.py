import pandas as pd
import matplotlib.pyplot as plt

# Load the data
data = pd.read_csv('C:/Users/griff/OneDrive/Desktop/Research/Data Collection/Datasets/primary_df.csv')

# Exclude rows where Number of Pages is 0
data = data[data['Number of Authors'] != 0]

# Group data by Year and Term, then sum Number of Authors
authors_by_year_term = data.groupby(['Year', 'term'])['Number of Authors'].mean().unstack()

# Plot Number of Authors by Year for each Term
plt.figure(figsize=(12, 8))
authors_by_year_term.plot(ax=plt.gca(), marker='o')
plt.title('Number of Authors by Year (Separated by Field)')
plt.xlabel('Year')
plt.ylabel('Number of Authors')
plt.legend(title='Field', bbox_to_anchor=(1.05, 1), loc='upper left')
plt.grid(True)
plt.tight_layout()
plt.show()
