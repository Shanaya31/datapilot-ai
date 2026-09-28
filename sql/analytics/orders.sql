DELETE FROM `${project}.analytics.orders_daily` WHERE batch_date = @batch_date;

INSERT INTO `${project}.analytics.orders_daily`
SELECT @batch_date, COUNT(*), SUM(amount), COUNT(DISTINCT customer_id), COUNTIF(status = 'CANCELLED')
FROM `${project}.staging.orders`
WHERE _batch_date = @batch_date;
