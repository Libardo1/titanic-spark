# generated by export.py
# origin: ../../notebooks/features/.ipynb
# date: 2017-04-22 08:13:07.508072

from pyspark.ml.feature import RFormula
from pyspark.ml.regression import LinearRegression
from pyspark.sql.functions import coalesce

from pyspark.sql.functions import udf
from pyspark.sql.types import StringType
# --------------------

def regressors_na(df, colnames):
    na = False
    for colname in colnames:
        null_count = df.where(df[colname].isNull()).count()
        na = na or (null_count>0)
    return na
# --------------------

def inpute_simple(df, colname):
    # which value is the most probable?
    d = df.groupBy(colname).count().toPandas()
    fill_value = d.loc[d['count'].argmax(),colname]
    
    #fill the na
    df = df.fillna(fill_value, 'Embarked')
    
    return df
# --------------------
def feature_vector(df, idcol, colname, regressors):
    formula = RFormula(formula= colname + ' ~ ' + '+'.join(regressors), 
                   labelCol='label', featuresCol='features')
    
    # to dense feature vector
    df_features = formula.fit(df).transform(df).select(idcol,'features', 'label')
    
    return df_features
# --------------------

def impute_lr(df, idcol, colname, regressors):
    assert not regressors_na(df, regressors)
    
    # to vector
    df_features = feature_vector(df, idcol, colname, regressors)  
    
    # create lr estimator
    lr = LinearRegression(maxIter=10, regParam=0.3, elasticNetParam=0.8)

    # Fit the model
    lrModel = lr.fit(df_features.where(df_features.label.isNotNull()))
    
    # Print the coefficients and intercept for linear regression
    print("Coefficients: %s" % str(lrModel.coefficients))
    print("Intercept: %s" % str(lrModel.intercept))

    # Summarize the model over the training set and print out some metrics
    trainingSummary = lrModel.summary
    print("numIterations: %d" % trainingSummary.totalIterations)
    print("objectiveHistory: %s" % str(trainingSummary.objectiveHistory))
    trainingSummary.residuals.show()
    print("RMSE: %f" % trainingSummary.rootMeanSquaredError)
    print("r2: %f" % trainingSummary.r2)
    
    # impute dependent variable
    df_impute = lrModel.transform(df_features)
    
    # join prediction with original dataframe
    df = df.join(df_impute.select('PassengerId','prediction'), 'PassengerId', "leftouter") 
    
    # coalesce null using imputation
    df =  df.withColumn(colname,coalesce(df[colname],df.prediction)).drop('prediction')
    
    return df
# --------------------

## created user defined function to extract title
def feature_title(df):
    getTitle = udf(lambda name: name.split(',')[1].split('.')[0].strip(),StringType())
    df = df.withColumn('Title', getTitle(df['Name']))
    df = df.drop('Name')
    return df
# --------------------