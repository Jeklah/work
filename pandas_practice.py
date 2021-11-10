import pandas as pd

titanic = pd.read_csv('./pandas/doc/data/titanic.csv')
# Prints the first 5 rows from df
titanic.head()

# Assigns the Age column values to ages variable.
ages = titanic['Age']
# Prints the first 5 values of Age column.
ages.head()

# Prints the type of pandas dataframe column...although from the documentation
# it sounds like it a column will always be a pandas.core.series.Series...?
type(titanic['Age'])

# Prints out the 'shape' of a dataframe. This is the dimensions of a dataframe.
# e.g 3 columns 2 rows would return (3,2)
titanic['Age'].shape

# To select multiple columns, use a list of column names.
age_sex = titanic[['Age', 'Sex']]

# Prints the first 5 entries of age and sex.
age_sex.head()

# Prints dimensions of a 2 dimension dataframe
titanic[['Age', 'Sex']].shape

# Searching with a where clause or similar.
above_35 = titanic[titanic['Age'] > 35]
above_35.head()


