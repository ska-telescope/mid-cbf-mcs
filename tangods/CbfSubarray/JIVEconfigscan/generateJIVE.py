# import string

# with open("/home/jerry/Documents/ska/mid-cbf-mcs/tangods/CbfSubarray/JIVEconfigscan/scanconfig.json") as file:
#     data=file.read()
#     # s1=data.translate({ord(c): None for c in string.whitespace})
#     s1="".join(data.split())
#     s2=s1.replace('"','\\"')
#     s3='"'+s2+'"'
#     print(s3)

# import json

# _vis_destination_address={"outputHost":[1], "outputMac": [], "outputPort":[]}
# a=_vis_destination_address
# # s=json.dumps(_vis_destination_address)
# print(type(a))
# print(a["outputHost"])

_output_link_map = [[0,0] for i in range(40)]
print(_output_link_map)