class FinancialMLCV:
    def __init__(self, cv_splitter, model_training_pipeline):
        """
        :param cv_splitter: An instance of either PurgedKFoldCV or CPCV
        :param model_training_pipeline: A user-defined function that takes in train and test data
                                         and returns evaluation metrics.
        """
        self.cv_splitter = cv_splitter
        self.model_training_pipeline = model_training_pipeline

    def run(self, X, y=None):
        """
        :param X: Feature data
        :param y: Optional target labels (for supervised learning)
        """
        all_metrics = []
        
        # Loop through splits provided by the splitter
        for train_idx, test_idx in self.cv_splitter.split(X, y):
            X_train, X_test = X[train_idx], X[test_idx]
            if y is not None:
                y_train, y_test = y[train_idx], y[test_idx]
            else:
                y_train, y_test = None, None
            
            # Run the user-defined training pipeline
            metrics = self.model_training_pipeline(X_train, X_test, y_train, y_test)
            all_metrics.append(metrics)
        
        return self.aggregate_metrics(all_metrics)

    def aggregate_metrics(self, metrics_list):
        """
        Aggregates metrics over all CV folds (e.g., averages the Sharpe ratio, accuracy, etc.).
        """
        # Assuming metrics_list is a list of dictionaries with metric names as keys
        aggregate_metrics = {}
        for key in metrics_list[0].keys():
            aggregate_metrics[key] = np.mean([metrics[key] for metrics in metrics_list])
        
        return aggregate_metrics
