import pandas as pd

# Replace 'your_file.csv' with the actual filename
input_file = 'scimagojr 2023.csv'
output_file = 'scimagojr 2023.csv'

# Read the semicolon-separated file
df = pd.read_csv(input_file, sep=';')

# Save the file with commas as separators
df.to_csv(output_file, index=False, sep=',')