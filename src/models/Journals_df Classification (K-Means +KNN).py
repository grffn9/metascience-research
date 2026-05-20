import pandas as pd
from sklearn.cluster import KMeans
from sklearn.neighbors import KNeighborsClassifier
import numpy as np

# Load your dataset
# Replace 'path_to_your_file.csv' with the actual path to your CSV file
journals_df = pd.read_csv('journals_df.csv')

# Ensure SJR column is numeric
journals_df['SJR'] = pd.to_numeric(journals_df['SJR'], errors='coerce')

# Drop rows with missing SJR values
journals_df = journals_df.dropna(subset=['SJR'])

# Outlier handling using the Interquartile Range (IQR) method
Q1 = journals_df['SJR'].quantile(0.25)  # First quartile (25th percentile)
Q3 = journals_df['SJR'].quantile(0.75)  # Third quartile (75th percentile)
IQR = Q3 - Q1  # Interquartile range

# Define outlier thresholds
lower_bound = Q1 - 1.5 * IQR
upper_bound = Q3 + 1.5 * IQR

# Filter inliers and outliers
inliers = journals_df[(journals_df['SJR'] >= lower_bound) & (journals_df['SJR'] <= upper_bound)].copy()
outliers = journals_df[(journals_df['SJR'] < lower_bound) | (journals_df['SJR'] > upper_bound)].copy()

# Reshape the SJR column for K-means clustering
inlier_sjr_values = inliers['SJR'].values.reshape(-1, 1)

# Apply K-means clustering on inliers
kmeans = KMeans(n_clusters=3, random_state=42)
inliers['SJR_Group'] = kmeans.fit_predict(inlier_sjr_values)

# Map cluster labels to 'Low', 'Medium', 'High' based on SJR means
cluster_centers = kmeans.cluster_centers_.flatten()
sorted_clusters = np.argsort(cluster_centers)  # Sort clusters by SJR value
cluster_mapping = {sorted_clusters[0]: 'Low', sorted_clusters[1]: 'Medium', sorted_clusters[2]: 'High'}
inliers['SJR_Category'] = inliers['SJR_Group'].map(cluster_mapping)

# Train a K-Nearest Neighbors model on inliers
knn = KNeighborsClassifier(n_neighbors=3)
knn.fit(inlier_sjr_values, inliers['SJR_Group'])

# Predict cluster for outliers
outlier_sjr_values = outliers['SJR'].values.reshape(-1, 1)
outliers['SJR_Group'] = knn.predict(outlier_sjr_values)
outliers['SJR_Category'] = outliers['SJR_Group'].map(cluster_mapping)

# Combine inliers and outliers back together
journals_df = pd.concat([inliers, outliers]).sort_index()

# Drop the 'SJR_Group' column and save the output
journals_df.drop(columns=['SJR_Group'], inplace=True)

# Save or display results
print(journals_df[['Title', 'SJR', 'SJR_Category']])

# Save to a CSV, excluding the SJR_Group column
journals_df[['ISSN', 'Rank', 'Title', 'SJR', 'H index', 'Country', 'Region',
             'Coverage', 'Categories', 'Areas', 'SJR_Category']].to_csv(
    'journals_df.csv', index=False
)
