DELETE FROM `${project}.staging.customers` WHERE _batch_date = @batch_date;

INSERT INTO `${project}.staging.customers`
SELECT customer_id, name, LOWER(email) AS email, country, signup_ts, segment, _batch_date
FROM `${project}.raw.customers`
WHERE _batch_date = @batch_date AND customer_id IS NOT NULL
QUALIFY ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY _ingested_at DESC) = 1;
