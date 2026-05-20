import pandas as pd
import gender_guesser.detector as gender

# 1. Read your CSV into a DataFrame
#    Suppose your CSV is 'author_df.csv' with column 'First Name'
df = pd.read_csv('author_df.csv')

# 2. Create a gender detector instance
detector = gender.Detector()


# 3. Define a simple function to return "male", "female", or "unknown"
def guess_gender(row):
    # Extract the first token of "First Name" (in case there's a middle initial).
    first_name_raw = row['First Name']
    if pd.isna(first_name_raw) or not str(first_name_raw).strip():
        return 'unknown'
    
    first_name = str(first_name_raw).strip().split()[0]
    guess = detector.get_gender(first_name)

    # Map the raw guess to the simplified gender
    if guess in ['male', 'mostly_male']:
        return 'male'
    elif guess in ['female', 'mostly_female']:
        return 'female'
    else:
        # 'andy' or 'unknown' become "unknown"
        return 'unknown'


# 4. Apply the guess function across rows and store in a single "gender" column
df['gender'] = df.apply(guess_gender, axis=1)

# 5. (Optional) Inspect or export your results
print(df[['First Name', 'gender']].head())
df.to_csv('author_df.csv', index=False)
