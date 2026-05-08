CREATE OR REPLACE FUNCTION create_partition_for_date(target_date DATE)
RETURNS VOID AS $$
DECLARE
    partition_name TEXT;
    end_date DATE;
BEGIN
    partition_name := 'sales_' || to_char(target_date, 'YYYY_MM_DD');
    end_date := target_date + INTERVAL '1 day';

    EXECUTE format(
        'CREATE TABLE IF NOT EXISTS %I PARTITION OF sales FOR VALUES FROM (%L) TO (%L)',
        partition_name, target_date, end_date
    );
END;
$$ LANGUAGE plpgsql;