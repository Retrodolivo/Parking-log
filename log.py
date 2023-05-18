##import serial
##
##ser = serial.Serial(
##    port = 'COM15',
##    baudrate = 115200,
##    bytesize = serial.EIGHTBITS,
##    parity = serial.PARITY_NONE,
##    stopbits = serial.STOPBITS_ONE,
##    timeout = 5
##)
##data = ''
##if ser.is_open:
##    ser.reset_output_buffer()
##    ser.reset_input_buffer()
##    print(ser.is_open)
##    command = 'logs'.encode('utf-8')
##    ser.write(command)
##    print(ser.in_waiting)
###    while ser.in_waiting:
##    data = ser.read(2048)
##    f = open('data.txt', 'w')
##    f.write(str(data))
##    f.close()
##ser.close()
##print(ser.is_open)


import math

def retrieve_log_records_from_page(page):
    offset = 0
    elem_pos = {'start': 0, 'end': 0}
    for record in range(log_records_in_page):
        for elem in data_arrangement_list:
            temp_list = [] #log element parts would be stored there
            elem_pos['start'] = offset + record * bytes_in_record
            elem_pos['end'] = offset + log_record[elem]['size'] + record * bytes_in_record
            temp_list.extend(
                                data_list[elem_pos['start']:elem_pos['end']]
                            )
            offset += log_record[elem]['size']
            for byte in range(log_record[elem]['size']):
                log_record[elem]['val'] |= temp_list[byte] << 8 * byte

#1.Timestamp(32bit);
#2.CardID(32bit);
#3.Index(16bit);
#4.Action(8bit);
#5.Cell_num(8bit).
log_record = {'Timestamp': {'size': 4,
                            'val': 0},
              'CardID':    {'size': 4,
                            'val': 0},
              'Index':     {'size': 2,
                            'val': 0},
              'Action':    {'size': 1,
                            'val': 0},
              'Cell_num':  {'size': 1,
                            'val': 0}
              }
#using by below functions for correct parsing. MUST BE MAINTAINED IN CORRECT ORDER
data_arrangement_list = ['Timestamp', 'CardID', 'Index', 'Action', 'Cell_num']

bytes_in_record = sum(d['size'] for d in log_record.values() if d)
bytes_in_page = 2048
records_in_page = bytes_in_page / bytes_in_record
log_records_in_page = math.floor(bytes_in_page / bytes_in_record)

f = open('flash.bin', 'rb')
#get binary string then convert it to list
dump_data = f.read()
data_list = []
data_list.extend(dump_data)
pages = len(data_list) / bytes_in_page
#if page is not full
if math.floor(pages) == 0:
    print("bin file should be at least 1 page size")
else:
    # for page in pages:
    retrieve_log_records_from_page(1)
    print(log_record)
    f.close()





