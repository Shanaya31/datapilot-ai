DELETE FROM `${project}.analytics.inventory_daily` WHERE batch_date = @batch_date;

INSERT INTO `${project}.analytics.inventory_daily`
SELECT @batch_date, COUNT(*), COUNTIF(stock_level < reorder_level), SUM(stock_level)
FROM `${project}.staging.inventory`
WHERE _batch_date = @batch_date;
