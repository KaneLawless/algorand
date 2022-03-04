import re

print('Hello World!')




regex = re.compile("!!ADDRESS!!")
regex1 = re.compile("!!!RECEVIER!!!")
recevier=["6ZHGHH5Z5CTPCF5WCESXMGRSVK7QJETR63M3NY5FJCUYDHO57VTCMJOBGY","4YSOIT2HUTVYZQYOPS36WCAAMFHTTMKPJIMYNJX7IVKBB5XEAHZLGDAAFA"]

addresses=["4YSOIT2HUTVYZQYOPS36WCAAMFHTTMKPJIMYNJX7IVKBB5XEAHZLGDAAFA","6ZHGHH5Z5CTPCF5WCESXMGRSVK7QJETR63M3NY5FJCUYDHO57VTCMJOBGY"]

for x,y in zip(addresses,recevier):
    with open('full_teal.teal', 'r') as inf:
        report_name=x
        with open('proba_full'+report_name+'.teal', 'w') as outf:
            for z,d in zip(inf,inf):
                outf.write( re.sub(regex, x, z, 0, 0) )
                outf.write( re.sub(regex1, y, d, 0, 0 ))





# DOC HERE : https://docs.python.org/3/library/re.html#re.sub