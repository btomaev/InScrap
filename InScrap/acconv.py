import json
path = input('source>>> ')

with open(path, 'r') as f:
	data = [i.strip().split(':') for i in f.readlines()]
	out = [{"login":i[0], "password":i[1]} for i in data]
	print(json.dumps(out))
input()