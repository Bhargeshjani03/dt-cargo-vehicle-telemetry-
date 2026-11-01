
import pandas as pd
import numpy as np

from src.preprocessing.common import (
    NumericPreprocessor,
    numeric_feature_frame,
    log1p_nonnegative
)


# Small test dataset
df = pd.DataFrame({
    "speed": [20, 30, np.nan, 50, 60],
    "distance": [10, 20, 30, np.nan, 50],
    "duration": [1, 2, 3, 4, 5]
})

features = ["speed", "distance"]

# 1. Select usable feature rows
X, mask = numeric_feature_frame(df, features)

print("Original rows:", len(df))
print("Usable rows:", len(X))
print("\nSelected features:")
print(X)

# 2. Standard scaling + median imputation
preprocessor = NumericPreprocessor(scaling="standard")

X_processed = preprocessor.fit_transform(X)

print("\nProcessed data:")
print(X_processed)

# 3. Test log transformation
X_log = log1p_nonnegative(
    X[["distance"]],
    ["distance"]
)

print("\nLog transformed distance:")
print(X_log)

# 4. Check missing values
print("\nRemaining missing values:")
print(X_processed.isna().sum())
