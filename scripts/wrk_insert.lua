wrk.method = "PUT"
wrk.headers["Content-Type"] = "application/json"

local file = io.open("scripts/bulk_insert.json", "rb")
if file then
    wrk.body = file:read("*all")
    file:close()
else
    print("Error: Could not find scripts/bulk_insert.json!")
    os.exit(1)
end
