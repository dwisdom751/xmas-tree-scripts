import os.path

import csv


inFile = open('responses.csv')
rawData = csv.reader(inFile)
#skip header
next(rawData)

inAdds = open('latLang.csv')
Adds = csv.reader(inAdds)

latLongD = {}
manuallyCleanAddresses = {}


with open("cancelations.csv", "r") as f:
    # skip header
    f.readline()
    cancels = f.readlines()
    cancels = set([l.strip().upper() for l in cancels])

with open("manuallyGeocoded.csv", "r") as f:
    # skip header
    f.readline()
    manuallyGeocoded = f.readlines()
    manuallyGeocoded = [l.strip().split(",") for l in manuallyGeocoded]

for row in manuallyGeocoded:
    # 0 is clean_address
    # 1 is original_address
    # 9 is latitude
    # 10 is longitude
    latLongD[row[1].upper()] = row[9] + "," + row[10]
    manuallyCleanAddresses[row[1].upper()] = ",".join(row) + "\n"
  


for row in Adds:
    # 9 is LAT column
    # 10 is LON column
    # not using the census lat/lon for now
    
    # "Location" column
    latLongD[row[2].upper()] =  row[9] + "," + row[10]
    # G_street column
    latLongD[row[11] + ' ' + row[12].upper()] =  row[9] + "," + row[10]
    
    
def abbreviate(addr):
    if addr != addr.upper():
        raise ValueError('input must be uppercase')
    addr_parts = addr.split()
    abb = {
      'ROAD': 'RD',
      'LANE': 'LN',
      'AVENUE': 'AVE',
      'CIRCLE': 'CIR',
      'TRAIL': 'TRL',
      'STREET': 'ST',
      'PARKWAY': 'PKWY',
      'HIGHWAY': 'HWY',
      'DRIVE': 'DR',
      'PLACE': 'PL',
      'PARK': 'PK',
      'NORTH': 'N',
      'SOUTH': 'S',
      'EAST': 'E',
      'WEST': 'W',
      'COMMONS': 'CMNS',
      'COURT': 'CT',
      'RIDGE': 'RDG',
      'HOLLOW': 'HOL'
    }
    stopwords = ['USA', 'WESTPORT', '06880', 'CT']
    abb_addr = []
    for addr_part in addr_parts:
        if addr_part in abb:
            abb_addr.append(abb[addr_part])
        # Some people abbreviate "Court" as "Ct" in the input
        # we don't want to drop those
        # so we're assuming that anytime someone put "CT"
        # without also putting "Westport", they were probably
        # trying to put "Ct" as in "Court"
        elif addr_part == 'CT' and 'WESTPORT' not in addr_parts:
            abb_addr.append(addr_part)
        elif addr_part in stopwords:
            continue
        else:
            abb_addr.append(addr_part)
    return ' '.join(abb_addr)
    

def clean_note(note):
    # could either quote it and replace quote characters
    # or replace newlines and commas
    # I'll go with newlines and commas for now
    return note.replace("\n", " ").replace(",", ";")



outHits = open('outHits.csv', "w")
outMiss = open('outMiss.csv', "w")
outWhole = open('outWhole.csv', "w")
outDupes = open('outDupes.csv', "w")

# column headers to match what TrackRoad expects
columns = "street,original_address,city,state,postal_code,boxes,service_time,description,phone,latitude,longitude\n"
outHits.write(columns)
outMiss.write(columns)
outWhole.write(columns)
outDupes.write("address\n")

hits = 0
processed = 0
skipped = 0
dupes = 0
wholeSet = set()
punct = ',./?:;\'"!~`@#$%^&*(){}[]<>'
for row in rawData:
    rezAdd = row[5].upper()
    note = clean_note(row[9])
    
    
    # skip anyone who has canceled
    if rezAdd in cancels:
        skipped += 1
        wholeSet.add(rezAdd, )
        continue
    
    # have to remove commas because the keys in the dict don't have commas
    # because I was lazy and didn't want to use the whole csv parser
    # so I split on commas instead
    if rezAdd.replace(",", "") in manuallyCleanAddresses:
        writeRow = manuallyCleanAddresses[rezAdd.replace(",", "")]
        outHits.write(writeRow)
        outWhole.write(writeRow)
        hits += 1
        processed += 1
        wholeSet.add(rezAdd)
        continue

    for p in punct:
      rezAdd = rezAdd.replace(p, '')

    
    rezAdd = abbreviate(rezAdd)
    if rezAdd in wholeSet:
        dupes += 1
        outDupes.write(row[5].replace(",", "") + "\n");
        continue
        
    ogAdd = row[5].replace(",", "")
    
    if rezAdd in latLongD:
        hits+=1
        processed+=1
        writeRow=rezAdd + "," + ogAdd + "," + "Westport,CT,06880,"+row[8]+",2,"+note+","+row[7]+","+latLongD[rezAdd]+"\n"
        outHits.write(writeRow)
        outWhole.write(writeRow)
    else:
        #TODO: split address into pieces and use them to find candidate addresses
        #try to use bing maps API to check addresses that are not found in latlong 
        processed+=1
        writeRow=rezAdd + "," + ogAdd + "," + "Westport,CT,06880,"+row[8]+",2,"+note+","+row[7]+",0,0\n"
        outMiss.write(writeRow)
        outWhole.write(writeRow)
    wholeSet.add(rezAdd)
outHits.close()
outMiss.close()
outWhole.close()

print(f"\ntotal:    {processed + skipped + dupes:>5}")
print(f"canceled: {skipped:>5}")
print(f"dupes:    {dupes:>5}")
print(f"\ngeocoded {hits} out of {processed} processed ({(hits/processed)*100:.2f}%)")
print(f"need to manually geocode {processed-hits} addresses in outMiss.csv and add them to manuallyGeocoded.csv\n")

