DELETE FROM `${project}.analytics.customers_by_country` WHERE batch_date = @batch_date;

INSERT INTO `${project}.analytics.customers_by_country`
SELECT @batch_date, country, COUNT(*)
FROM `${project}.staging.customers`
WHERE _batch_date = @batch_date
GROUP BY country;
