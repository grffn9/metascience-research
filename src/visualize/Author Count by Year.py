import pandas as pd
import matplotlib.pyplot as plt

# Load the data
data = pd.read_csv('C:/Users/griff/OneDrive/Desktop/Research/Data Collection/Datasets/primary_df.csv')

# Exclude rows where Number of Pages is 0
data = data[data['Number of Authors'] != 0]

# Group data by Year and calculate the sum of Number of Authors
authors_by_year = data.groupby('Year')['Number of Authors'].mean()

# Plot Number of Authors by Year
plt.figure(figsize=(10, 6))
authors_by_year.plot(kind='line', marker='o', color='orange')
plt.title('Number of Authors by Year')
plt.xlabel('Year')
plt.ylabel('Number of Authors')
plt.grid(True)
plt.show()
