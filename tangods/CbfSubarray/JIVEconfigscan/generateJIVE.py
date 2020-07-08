import string

with open("/home/jerry/Documents/ska/mid-cbf-mcs/tangods/CbfSubarray/JIVEconfigscan/scanconfig.json") as file:
    data=file.read()
    # s1=data.translate({ord(c): None for c in string.whitespace})
    s1="".join(data.split())
    s2=s1.replace('"','\\"')
    s3='"'+s2+'"'
    print(s3)

