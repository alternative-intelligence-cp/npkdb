import re
with open("src/network/controllers.npk", "r") as f:
    text = f.read()

replacements = {
    '"{"error":"Expected object"}"': '"{\\"error\\":\\"Expected object\\"}"',
    '"{"error":"Database capacity reached"}"': '"{\\"error\\":\\"Database capacity reached\\"}"',
    '"{"status": "ok", "results": []}"': '"{\\"status\\": \\"ok\\", \\"results\\": []}"',
    '"{"status":"ok"}"': '"{\\"status\\":\\"ok\\"}"',
    '"{"error":"Missing query_vector"}"': '"{\\"error\\":\\"Missing query_vector\\"}"'
}
for k, v in replacements.items():
    text = text.replace(k, v)
with open("src/network/controllers.npk", "w") as f:
    f.write(text)

with open("src/query/evaluator.npk", "r") as f:
    text2 = f.read()
# Let's see if astack requires @
# In the original audit, was it @apush or apush?
