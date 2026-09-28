DELETE FROM `${project}.staging.inventory` WHERE _batch_date = @batch_date;

INSERT INTO `${project}.staging.inventory`
SELECT product_id, warehouse_id, stock_level, reorder_level, snapshot_ts, _batch_date
FROM `${project}.raw.inventory`
WHERE _batch_date = @batch_date AND product_id IS NOT NULL AND warehouse_id IS NOT NULL
QUALIFY ROW_NUMBER() OVER (PARTITION BY product_id, warehouse_id ORDER BY _ingested_at DESC) = 1;
