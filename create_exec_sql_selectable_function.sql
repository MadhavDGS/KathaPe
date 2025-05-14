-- Create a function that can execute arbitrary SQL and return table results
CREATE OR REPLACE FUNCTION exec_sql(query text)
RETURNS SETOF json
LANGUAGE plpgsql
SECURITY DEFINER -- This makes it run with the privileges of the function creator (superuser)
AS $$
DECLARE
    result json;
    sql text;
BEGIN
    -- Build a dynamic SQL statement that returns the results as JSON
    sql := 'WITH query_result AS (' || query || ') SELECT row_to_json(query_result) FROM query_result';
    
    -- Execute the query and return results
    FOR result IN EXECUTE sql LOOP
        RETURN NEXT result;
    END LOOP;
    
    -- If no rows were returned, at least return an empty object
    IF NOT FOUND THEN
        RETURN;
    END IF;
    
    RETURN;
EXCEPTION WHEN OTHERS THEN
    -- On error, return error details as JSON
    RETURN NEXT json_build_object(
        'error', SQLERRM,
        'detail', SQLSTATE,
        'query', query
    );
END;
$$;

-- Grant execute permissions to all roles
GRANT EXECUTE ON FUNCTION exec_sql TO authenticated;
GRANT EXECUTE ON FUNCTION exec_sql TO anon;
GRANT EXECUTE ON FUNCTION exec_sql TO service_role;

-- Create a simpler version for non-SELECT queries that don't need to return results
CREATE OR REPLACE FUNCTION exec_sql_noreturn(query text)
RETURNS json
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    EXECUTE query;
    RETURN json_build_object('success', true);
EXCEPTION WHEN OTHERS THEN
    RETURN json_build_object(
        'success', false,
        'error', SQLERRM,
        'detail', SQLSTATE,
        'query', query
    );
END;
$$;

-- Grant execute permissions to all roles
GRANT EXECUTE ON FUNCTION exec_sql_noreturn TO authenticated;
GRANT EXECUTE ON FUNCTION exec_sql_noreturn TO anon;
GRANT EXECUTE ON FUNCTION exec_sql_noreturn TO service_role; 