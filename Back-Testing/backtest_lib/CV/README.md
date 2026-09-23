Combinatorial Purged Cross-Validation (CPCV): Allows the evaluation of models on multiple combinations of training and test sets, ensuring no data leakage due to overlapping samples.

Purged K-Fold Cross-Validation: Standard K-Fold cross-validation, with an additional purging mechanism to avoid look-ahead bias in time-series data.

# Combinatorial Purged Cross-Validation (CPCV):
CPCV is a cross-validation technique that allows the evaluation of models on multiple combinations of training and test sets, ensuring no data leakage due to overlapping samples. This is particularly useful in time-series data, where the order of observations matters and there may be dependencies between samples.

The idea behind CPCV is to generate all possible combinations of training and test sets, ensuring that no two sets share any samples. This way, the model is evaluated on a wide range of scenarios, providing a more robust estimate of its performance.

## parameters:
- n_splits: int
    Number of splits in the cross-validation
- n_combinations: int
    Number of combinations to generate
- purge_gap: int
    Number of observations to exclude before and after each test set


# PurgedKFold:
This method provides a purged version of K-Fold cross-validation, where overlapping data between train and test sets is removed using a purge gap.

The purge gap is a parameter that specifies the number of observations to exclude before and after each test set. This ensures that there is no look-ahead bias in the evaluation of the model, as it prevents the model from using information from the future to predict the past.

## parameters:
- n_splits: int
    Number of splits in the cross-validation
- purge_gap: int
    Number of observations to exclude before and after each test set

# cvrunner.py
This package serves as a wrapper around the cross-validation techniques, allowing users to define a custom training pipeline. The pipeline can be used to train models, evaluate them, and metrics.

## parameters:
- cv_splitter: object
    Cross-validation splitter object
- model_training_opipeline: object
    Training pipeline object

# Output:
The FinancialMLCV from cvrunner package automatically aggregates evaluation metrics across cross-validation folds. The output is a dictionary containing the aggregated metrics for each fold, as well as the overall mean of the metrics.


# Example of a user-defined training pipeline function
def my_training_pipeline(X_train, X_test, y_train, y_test):
    # Example: training a machine learning model (e.g., XGBoost)
    model = MyModel()
    model.fit(X_train, y_train)
    
    predictions = model.predict(X_test)
    
    # Calculate custom metrics 
    metrics = {
        
    }
    
    return metrics

## Example usage with Purged K-Fold CV
cv_splitter = PurgedKFoldCV(n_splits=5, purge_gap=1) or use CPCV
financial_cv = FinancialMLCV(cv_splitter=cv_splitter, model_training_pipeline=my_training_pipeline)

## Running cross-validation on data
X, y = load_financial_data()  # User loads their own dataset
cv_results = financial_cv.run(X, y)



