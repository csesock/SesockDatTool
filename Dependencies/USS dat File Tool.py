# Current build: Version 0.7.1
# Current build written on 6-26-2020
#
# Author: Chris Sesock on 6-5-2020
#
# python standard libraries
import csv, sys, re, os, time, ctypes
from os import system
from collections import deque
from datetime import datetime
# third-party libraries
from rich.progress import track
from rich.console import Console

# regular expression patterns
record_pattern = re.compile('[a-z][0-9]*\s*')
empty_pattern = re.compile('[^\S\n\t]+')
empty2_pattern = re.compile('[^\S\r\n]{2,}')
lat_long_pattern = re.compile('-?[0-9]{2}\.\d{1,13}$')

# default file information
working_file_name = "download.dat"

# standard wait time
WAIT_TIME = 0.2

# file names with dynamic dates 
missing_meter_filename = 'MissingMeters ' + str(datetime.today().strftime('%Y-%m-%d_%H-%M')) + '.txt'
missing_meter_csv_filename = 'MissingMeters ' + str(datetime.today().strftime('%Y-%m-%d_%H-%M')) + '.csv'
temp_meter_type = ""
meter_type_filename = 'MeterType' + str(temp_meter_type) + " " + str(datetime.today().strftime('%Y-%m-%d_%H-%M')) + '.txt'

# parameterized error handler for the file reader
def throwIOException(errorType):
    if errorType == 1:
        print("[ERROR 01]: File Not Found")
        print()
        main()
    elif errorType == 2:
        print("[ERROR 02]: File Already Exists")
        print()
        main()
    elif errorType == 3:
        print("[ERROR 03]: Unknown Input")
        print()
        main()
    elif errorType == 4:
        print("[ERROR 04]: No Records Found")
        print()
        main()
    else:
        print("[ERROR 00]: Unknown Error")
        print()
        sys.exit(0)
    

# main method -- responsible for IO menu/handling
def main():
    print("Enter operation to perform (0 to quit)")
    print("1) Single record scan")
    print("2) Verbose record scan")
    print("3) Print single record type")
    print("4) Print meter type")
    print("5) Print Office-Region-Zone data")
    print("6) Export missing meters")
    print("7) Export meter type")
    print("8) Check malformed lat/long data")
    try:
        scan_type = int(input(">>"))
    except ValueError:
        throwIOException(3)
    if scan_type == 1:
        print("Enter record type (ex. CUS or RHD)")
        record_type = input(">>").upper()
        scanForRecord(record_type)
    elif scan_type == 2:
        scanAllRecordsVerbose()
    elif scan_type == 3:
        print("Enter the record type (ex. CUS or RHD)")
        record_type = input(">>").upper()
        printSingleRecord(record_type)
    elif scan_type == 4:
        print("Enter the meter code to print (ex. 00 or 01)")
        user_meter_code = int(input(">>"))
        printMeterType(user_meter_code)
    elif scan_type == 5:
        fixOfficeRegionZoneFields()
    elif scan_type == 6:
        exportMissingMeters()
    elif scan_type == 7:
        print("Enter the meter code to export (ex. 00 or 01)")
        user_meter_code = int(input(">>"))
        global temp_meter_type
        temp_meter_type = str(user_meter_code)
        exportMeterType(user_meter_code)
    elif scan_type == 8:
        checkMalformedLatLong()
    elif scan_type == 0:
        sys.exit(0)
    else:
        throwIOException(3)

# scan download file for number of instances of a single record
def scanForRecord(record_type):
    counter = 0
    current_line = 1
    total_lines = getFileLineCount(working_file_name)
    try:
        with open(working_file_name, 'r') as openfile:
            for line in openfile:
                progressBarComplex(current_line, total_lines)
                if line.startswith(record_type):
                    counter+=1
                current_line+=1
    except FileNotFoundError:
        throwIOException(1)
    print()
    print(f"{counter:,d}", "records found")
    print()
    main()

def scanAllRecordsVerbose():
    all_records = {}
    with open(working_file_name, 'r') as openfile:
        for line in openfile:
            x = line[0:3]
            if x not in all_records:
                all_records[x] = 1
            else:
                all_records[x]+=1
        print("File scan successful.")
        print("---------------------")
        print("Records found:")
        for record in all_records:
            #print(record, ":", all_records[record])
            print(record, ":\t", f"{all_records[record]:,d}")
        print("---------------------")
        print()
        time.sleep(WAIT_TIME)
        main()


# print all of a single record type
def printSingleRecord(record_type):
    counter = 0
    try:
        with open(working_file_name, 'r') as openfile:
            for line in openfile:
                if record_type in line or record_type.lower() in line:
                    counter+=1
                    print("{0}) {1}".format(counter, line))
        print(counter, "records printed.")
    except FileNotFoundError:
        throwIOException(1)
    print()
    main()

# print all records -- functionally a print() for download.dat
# used for debugging, not a visible option for the user
def printAllRecords():
    try:
        with open(working_file_name, 'r') as openfile:
            counter = 0
            for line in openfile:
                print("{0}) {1}".format(counter, line))
                counter+=1
    except FileNotFoundError:
        throwIOException(1)
    print()
    time.sleep(1)
    main()

# exports a text file with all missing meter records in download file
def exportMissingMeters():
    counter=0
    current_line=1
    total_line = getFileLineCount(working_file_name)
    try:
        with open(working_file_name, 'r') as openfile:
            try:
                with open(missing_meter_filename, 'x') as builtfile:
                    previous_line = ''
                    for line in openfile:
                        progressBarComplex(current_line, total_line)
                        if line.startswith('MTR'):
                            meter_record = line[45:57]
                            if empty_pattern.match(meter_record):
                                builtfile.write(previous_line)
                                counter+=1
                        previous_line=line
                        current_line+=1
                    if counter == 0:
                        builtfile.close()
                        os.remove(missing_meter_filename)
                        print()
                        print("No records found.")
                        print()
                        main()
            except FileExistsError:
                throwIOException(2)
    except FileNotFoundError:
        throwIOException(1)
    print()
    print("The operation was successful.")
    print()
    print("Export missing meters to .csv file (Y or N)")
    answer = input(">>")
    if answer.upper() == 'Y':
        convertMissingMetersToCSV() # create a .csv file with the same data
    elif answer.upper() == 'N':
        main()
    else:
        throwIOException(3)

# post export function which converts list of missing meters to a .csv file
def convertMissingMetersToCSV():
    try: 
        with open(missing_meter_filename, 'r') as openfile:
            try:
                with open(missing_meter_csv_filename, 'x') as builtfile:
                    for line in openfile:
                        line = re.sub('[^\S\r\n]{2,}', ',', line.strip())
                        builtfile.write(line)
                        if line.startswith('CUS'):
                            builtfile.write('\n')
            except FileExistsError:
                throwIOException(2)
    except FileNotFoundError:
        throwIOException(1)
    time.sleep(WAIT_TIME)
    print()
    main()

# exports a text file of a specified meter translation code
#
## There is a theoretical bug wherein the deque exceeds the number of records
## between the current RDG and previous CUS and the previous CUS gets read
## and associated with the wrong RDG record. I am currently working to fix.
def exportMeterType(user_meter_code):
    counter = 0
    current_record = deque(maxlen=getCustomerRecordLength()+1)
    global temp_meter_type
    temp_meter_type = str(user_meter_code)
    try:
        with open(working_file_name, 'r') as openfile:
            try:
                with open(meter_type_filename, 'x') as builtfile:
                    for line in openfile:
                        if line.startswith('RDG'):
                            meter_code = line[76:78] #range 77-78
                            if int(meter_code) == user_meter_code:
                                for record in current_record:
                                    if record.startswith('CUS'):
                                        builtfile.write(record)
                                        counter+=1
                        current_record.append(line)
                    if counter == 0:
                        builtfile.close()
                        os.remove(meter_type_filename)
                        print()
                        print("No records found.")
                        print()
            except FileExistsError:
                throwIOException(2)
    except FileNotFoundError:
        throwIOException(1)
    print("The operation was successful.")
    print(counter, "records exported.")
    print()
    time.sleep(WAIT_TIME)
    main()

# prints every record of a specified meter type to the console
def printMeterType(user_meter_code):
    counter = 0
    current_record = deque(maxlen=getCustomerRecordLength()+1)
    try:
        with open(working_file_name, 'r') as openfile:
            for line in openfile:
                if line.startswith('RDG'):
                    meter_code = line[76:78] #range 77-78
                    if int(meter_code) == user_meter_code:
                        for record in current_record:
                            if record.startswith('CUS'):
                                print("{0}) {1}".format(counter, record))
                                counter+=1
                current_record.append(line)
            if counter == 0:
                throwIOException(4)
    except FileNotFoundError:
        throwIOException(1)
    print()
    time.sleep(WAIT_TIME)
    main()

# label and print the office-region-zone fields
def fixOfficeRegionZoneFields():
    try:
        with open(working_file_name, 'r') as openfile:
            for line in openfile:
                if line.startswith('RHD'):
                    office = line[71:73]
                    if office == "  ":
                        office = "BLANK"
                    region = line[73:75]
                    if region == "  ":
                        region = "BLANK"
                    zone = line[75:77]
                    if zone == "  ":
                        zone = "BLANK"
                    print("-------------------------")
                    print("Office: \t", str(office))
                    print("Region: \t", str(region))
                    print("Zone: \t\t", str(zone))
                    print("-------------------------")
                    break
        print()
        time.sleep(WAIT_TIME)
        main()
    except FileNotFoundError:
        throwIOException(1)

# checks that lat/long data matches two digits, period, then trailing digits
def checkMalformedLatLong():
    malformed_data = False
    counter=1 #first line in file
    try:
        with open(working_file_name, 'r') as openfile:
            for line in openfile:
                if line.startswith('MTX'):
                    lat_data = line[23:40].rstrip()
                    long_data = line[40:57].rstrip()
                    if not lat_long_pattern.match(lat_data):
                        malformed_data = True 
                        print("Malformed lat data at line:", counter, "Value:", lat_data)
                    elif not lat_long_pattern.match(long_data):
                        malformed_data = True
                        print("Malformed long data at line:", counter, "Value:", long_data)
                counter+=1
            if malformed_data == True:
                print("The above data is malformed in some way.")
            else:
                if checkLatLongSigns(float(lat_data), float(long_data)) == False:
                    print("The data is not malformed.")
                else:
                    print("The data has malformed sign values.")
        print()
        time.sleep(WAIT_TIME)
        main()
    except FileNotFoundError:
        throwIOException(1)

# an additional level of checking to make sure that lat/long data is correct
# lat data will always be +, long will always be - in our region
def checkLatLongSigns(lat_data, long_data):
    if lat_data < 0 or long_data > 0:
        return True
    else:
        return False

#################################
###### Helper Functions #########
#################################

# counts the number of lines in a file
def getFileLineCount(filename):
    try:
        with open(filename, 'r') as openfile:
            counter = 0
            for line in openfile:
                counter+=1
        return counter
    except FileNotFoundError:
        throwIOException(1)

# returns the number of records associated with each customer
def getCustomerRecordLength():
    try:
        with open(working_file_name, 'r') as openfile:
            counter = start_line = end_line = 0
            for line in openfile:
                counter+=1
                if line.startswith('CUS'):
                    start_line = counter
                if line.startswith('RFF'):
                    end_line = counter
                    length = (end_line-start_line)+1
                    return length
    except FileNotFoundError:
        throwIOException(1)        

def progressBarComplex(current, total, barLength=20):
    percent = float(current)*100/total
    arrow   = '-' * int(percent/100*barLength-1) + '>'
    spaces  = ' ' * (barLength-len(arrow))
    print('Progress: [%s%s] %d %%' % (arrow, spaces, percent), end='\r')

# sets import function calls
if __name__ == "__main__":
    console = Console()
    #ctypes.windll.kernel32.SetConsoleTitleW("USS Dat File Tool v0.7")
    console.print("United Systems dat File Tool [Version 0.7]", style="bold green")
    console.print("(c) 2020 United Systems and Software Inc.", style="bold green")
    console.print()
    main()