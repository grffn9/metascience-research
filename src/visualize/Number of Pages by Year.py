import pandas as pd
import matplotlib.pyplot as plt

# Load the data
data = pd.read_csv('C:/Users/griff/OneDrive/Desktop/Research/Data Collection/Datasets/primary_df.csv')

# Exclude rows where Number of Pages is 0
data = data[data['Number of Pages'] != 0]

# Group data by Year and calculate the sum of Number of Pages
pages_by_year = data.groupby('Year')['Number of Pages'].mean()

# Plot Number of Pages by Year
plt.figure(figsize=(10, 6))
pages_by_year.plot(kind='line', marker='o')
plt.title('Number of Pages by Year')
plt.xlabel('Year')
plt.ylabel('Number of Pages')
plt.grid(True)
plt.show()
