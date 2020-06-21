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

# argin=8185000
# result={"outputLink": 0, "outputHost": "109.1", "outputMac": "06-00", "outputPort": 0}
# _output_link_map=[ 
#                 [0, 4],
#                 [744, 8],
#                 [1480, 12],
#                 [2234, 16],
#                 [2978, 20],
#                 [3722, 24],
#                 [4466, 28],
#                 [5208, 32],
#                 [5952, 36],
#                 [6696, 40],
#                 [7440, 44],
#                 [8184, 48],
#                 [8928, 52],
#                 [9672, 56],
#                 [10416, 60],
#                 [11160, 64],
#                 [11904, 68],
#                 [12648, 72],
#                 [13392, 76],
#                 [14136, 80]
#             ]
# _vis_destination_address={"outputHost": [[0, "192.168.0.1"], [8184, "192.168.0.2"]],
#             "outputMac": [[0, "06-00-00-00-00-01"]],
#             "outputPort": [[0, 9000, 1], [8184, 9000, 1]]}
# # Get output link by finding the first element[1] that's greater than argin
# link=0
# for element in _output_link_map:
#     if argin>=element[0]:
#         link=element[1]
#     else:
#         break
# result["outputLink"]=link
# # Get 3 addresses by finding the first element[1] that's greater than argin
# host=""
# for element in _vis_destination_address["outputHost"]:
#     if argin>=element[0]:
#         host=element[1]
#     else:
#         break
# result["outputHost"]=host        

# mac=""
# for element in _vis_destination_address["outputMac"]:
#     if argin>=element[0]:
#         mac=element[1]
#     else:
#         break
# result["outputMac"]=mac

# # Port is different. the array is given as [[start_channel, start_value, increment],[start_channel, start_value, increment],.....]
# # value = start_value + (channel - start_channel)*increment
# triple=[] # find the triple with correct start_value
# for element in _vis_destination_address["outputPort"]:
#     if argin>=element[0]:
#         triple=element
#     else:
#         break

# result["outputPort"]= triple[1] + (argin - triple[0])* triple[2]

# print(result)