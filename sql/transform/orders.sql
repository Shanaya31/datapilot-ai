DELETE FROM `${project}.staging.orders` WHERE _batch_date = @batch_date;

INSERT INTO `${project}.staging.orders`
SELECT order_id, customer_id, product_id, order_ts, quantity, amount, UPPER(status) AS status, _batch_date
FROM `${project}.raw.orders`
WHERE _batch_date = @batch_date AND order_id IS NOT NULL
QUALIFY ROW_NUMBER() OVER (PARTITION BY order_id ORDER BY _ingested_at DESC) = 1;
