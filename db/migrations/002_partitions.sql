CREATE OR REPLACE FUNCTION create_partitions_for_year(year INTEGER)
RETURNS VOID AS $$
DECLARE
    start_date DATE;
    end_date DATE;
    partition_name TEXT;
BEGIN
    FOR month IN 1..12 LOOP
        FOR day IN 1..31 LOOP
            BEGIN
                start_date := make_date(year, month, day);
            EXCEPTION WHEN others THEN
                CONTINUE;
            END;

            partition_name := 'sales_' || to_char(start_date, 'YYYY_MM_DD');
            end_date := start_date + INTERVAL '1 day';

            EXECUTE format(
                'CREATE TABLE IF NOT EXISTS %I PARTITION OF sales FOR VALUES FROM (%L) TO (%L)',
                partition_name, start_date, end_date
            );
        END LOOP;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

SELECT create_partitions_for_year(2026);
SELECT create_partitions_for_year(2027);